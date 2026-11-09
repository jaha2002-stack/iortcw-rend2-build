using DarkWolfPBRStudio.Models;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace DarkWolfPBRStudio.Services;

public static class BatchPbrExportService
{
    private readonly record struct TextRange(int Start, int End, string Text);

    public static void Export(string outputPk3, IReadOnlyList<BatchMaterialItem> items)
    {
        if (items.Count == 0) throw new InvalidOperationException("Batch is empty.");

        Directory.CreateDirectory(Path.GetDirectoryName(outputPk3) ?? ".");
        if (File.Exists(outputPk3)) File.Delete(outputPk3);

        using var zip = ZipFile.Open(outputPk3, ZipArchiveMode.Create);
        var writtenPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var manifestItems = new List<object>();
        var scriptPairs = new List<object>();

        foreach (var item in items.OrderBy(x => x.Asset.ShaderName, StringComparer.OrdinalIgnoreCase))
        {
            WriteMaterialMaps(zip, writtenPaths, item);

            var asset = item.Asset;
            var settings = item.Settings;
            manifestItems.Add(new
            {
                source = asset.EntryPath,
                shader = asset.ShaderName,
                materialMode = item.ExistingMaterial is null
                    ? "implicit-safe-fallback"
                    : "scripted-full-source-pair",
                scriptedSource = item.ExistingMaterial is null ? null : new
                {
                    item.ExistingMaterial.SourcePk3,
                    item.ExistingMaterial.DiscoveryShaderPath,
                    effective = item.ExistingMaterial.ScriptPath,
                    item.ExistingMaterial.UsesMtr
                },
                maps = new
                {
                    normal = asset.ShaderName + "_n.tga",
                    normalHeight = settings.ParallaxEnabled ? asset.ShaderName + "_nh.tga" : null,
                    height = settings.ParallaxEnabled ? asset.ShaderName + "_h.tga" : null,
                    orm = asset.ShaderName + "_orm.tga",
                    ormChannels = "R=AO, G=Roughness, B=Metallic"
                },
                generationMode = settings.GenerationMode.ToString(),
                macroReliefBoost = settings.MacroReliefBoost,
                pbr = settings,
                validation = item.Result.Report
            });
        }

        // Implicit materials have no competing original definition. Keep one own namespace
        // pair: a real legacy .shader fallback and a PBR .mtr replacement.
        var implicitItems = items
            .Where(x => x.ExistingMaterial is null)
            .OrderBy(x => x.Asset.ShaderName, StringComparer.OrdinalIgnoreCase)
            .ToList();

        if (implicitItems.Count > 0)
        {
            string materialKey = string.Join("\n",
                implicitItems.Select(x => x.Asset.ShaderName));
            string key = Convert.ToHexString(SHA1.HashData(Encoding.UTF8.GetBytes(materialKey)))
                .ToLowerInvariant()[..10];
            string scriptBase = $"scripts/dw_pbrstudio_v2051_{key}";

            string fallbackText = string.Join(
                Environment.NewLine + Environment.NewLine,
                implicitItems.Select(x => BuildImplicitFallbackMaterial(x.Asset))) +
                Environment.NewLine;

            string pbrText = string.Join(
                Environment.NewLine + Environment.NewLine,
                implicitItems.Select(x =>
                {
                    string normalStage = BuildNormalStage(x.Asset, x.Settings);
                    string ormStage = BuildOrmStage(x.Asset);
                    return BuildImplicitPbrMaterial(x.Asset, normalStage, ormStage);
                })) + Environment.NewLine;

            WriteUnique(zip, writtenPaths, scriptBase + ".shader", Encoding.UTF8.GetBytes(fallbackText));
            WriteUnique(zip, writtenPaths, scriptBase + ".mtr", Encoding.UTF8.GetBytes(pbrText));

            scriptPairs.Add(new
            {
                mode = "implicit-owned-pair",
                shader = scriptBase + ".shader",
                mtr = scriptBase + ".mtr",
                materialCount = implicitItems.Count,
                selectedMaterials = implicitItems.Select(x => x.Asset.ShaderName).ToArray()
            });
        }

        // Existing scripted materials must keep their original discovery basename.
        // A same-basename .mtr replaces the ENTIRE .shader text in Rend2, so export the
        // complete original fallback shader plus a complete upgraded effective script.
        var scriptedGroups = items
            .Where(x => x.ExistingMaterial is not null)
            .GroupBy(x => x.ExistingMaterial!.DiscoveryShaderPath, StringComparer.OrdinalIgnoreCase)
            .OrderBy(g => g.Key, StringComparer.OrdinalIgnoreCase);

        foreach (var group in scriptedGroups)
        {
            var first = group.First().ExistingMaterial!;
            string fallbackText = first.FallbackShaderText;
            string pbrText = first.EffectiveScriptText;

            foreach (var item in group.OrderBy(x => x.Asset.ShaderName, StringComparer.OrdinalIgnoreCase))
            {
                var existing = item.ExistingMaterial!;
                if (!existing.FallbackShaderText.Equals(fallbackText, StringComparison.Ordinal) ||
                    !existing.EffectiveScriptText.Equals(first.EffectiveScriptText, StringComparison.Ordinal))
                {
                    throw new InvalidDataException(
                        $"Conflicting source texts for discovery script {first.DiscoveryShaderPath}.");
                }

                string normalStage = BuildNormalStage(item.Asset, item.Settings);
                string ormStage = BuildOrmStage(item.Asset);
                string mergedBlock = MergePbrStages(existing.Block, item.Asset, normalStage, ormStage);
                pbrText = ReplaceMaterialBlock(pbrText, item.Asset.ShaderName, mergedBlock);
            }

            string scriptBase = first.ScriptBasePath.Replace('\\', '/');
            WriteUnique(zip, writtenPaths, scriptBase + ".shader", EncodeScript(fallbackText));
            WriteUnique(zip, writtenPaths, scriptBase + ".mtr", EncodeScript(pbrText));

            scriptPairs.Add(new
            {
                mode = "scripted-full-file-safe-replacement",
                shader = scriptBase + ".shader",
                mtr = scriptBase + ".mtr",
                originalEffectiveSource = first.ScriptPath,
                originalPk3 = first.SourcePk3,
                materialCount = group.Count(),
                selectedMaterials = group.Select(x => x.Asset.ShaderName)
                    .OrderBy(x => x, StringComparer.OrdinalIgnoreCase)
                    .ToArray()
            });
        }

        var manifest = new
        {
            generator = "DarkWolf PBR Studio V2.05.1 Safe Material Export",
            target = "ioRTCW Rend2 DarkWolf PBR V3.2 Physical Relief / POM",
            textureCount = items.Count,
            scriptPairCount = scriptPairs.Count,
            discoveryRule = "Rend2 discovers scripts/*.shader and prefers same-basename .mtr",
            scriptedRule = "A same-basename .mtr replaces the complete .shader source; therefore scripted exports contain full source pairs",
            generatedUtc = DateTime.UtcNow,
            scriptPairs,
            items = manifestItems
        };

        WriteUnique(zip, writtenPaths, "darkwolf_pbrstudio/batch_manifest_v2051.json",
            JsonSerializer.SerializeToUtf8Bytes(manifest, new JsonSerializerOptions { WriteIndented = true }));
    }

    private static void WriteMaterialMaps(
        ZipArchive zip,
        HashSet<string> writtenPaths,
        BatchMaterialItem item)
    {
        var asset = item.Asset;
        var settings = item.Settings;
        var pbr = item.Result;

        if (item.IncludeBaseColor)
        {
            var bytes = ImageService.EncodePreservingExtension(item.BaseColor, asset.Extension);
            WriteUnique(zip, writtenPaths, asset.EntryPath, bytes);
        }

        string normalPath = asset.ShaderName + "_n.tga";
        string normalHeightPath = asset.ShaderName + "_nh.tga";
        string heightPath = asset.ShaderName + "_h.tga";
        string ormPath = asset.ShaderName + "_orm.tga";

        string tmpN = Path.GetTempFileName();
        string tmpNh = Path.GetTempFileName();
        string tmpH = Path.GetTempFileName();
        string tmpO = Path.GetTempFileName();

        try
        {
            TgaCodec.SaveRgb24PillowCompatible(pbr.Normal, tmpN);
            TgaCodec.Save(pbr.NormalHeight, tmpNh);
            TgaCodec.SaveRgb24PillowCompatible(pbr.Height, tmpH);
            TgaCodec.SaveRgb24PillowCompatible(pbr.Orm, tmpO);

            WriteUnique(zip, writtenPaths, normalPath, File.ReadAllBytes(tmpN));
            WriteUnique(zip, writtenPaths, ormPath, File.ReadAllBytes(tmpO));

            if (settings.ParallaxEnabled)
            {
                WriteUnique(zip, writtenPaths, normalHeightPath, File.ReadAllBytes(tmpNh));
                WriteUnique(zip, writtenPaths, heightPath, File.ReadAllBytes(tmpH));
            }
        }
        finally
        {
            foreach (string p in new[] { tmpN, tmpNh, tmpH, tmpO })
                try { File.Delete(p); } catch { }
        }
    }

    private static string BuildNormalStage(TextureAsset asset, PbrSettings settings)
        => settings.ParallaxEnabled
            ? $@"    {{
        stage normalParallaxMap
        map {asset.ShaderName}_nh
        normalScale 1 1
        parallaxDepth {settings.ParallaxDepth.ToString("0.000", System.Globalization.CultureInfo.InvariantCulture)}
    }}"
            : $@"    {{
        stage normalMap
        map {asset.ShaderName}_n
        normalScale 1 1
    }}";

    private static string BuildOrmStage(TextureAsset asset)
        => $@"    {{
        stage ormMap
        map {asset.ShaderName}_orm
    }}";

    private static string BuildImplicitFallbackMaterial(TextureAsset asset)
        => $@"{asset.ShaderName}
{{
    qer_editorimage {asset.EntryPath}
    {{
        map {asset.EntryPath}
        rgbGen identity
    }}
    {{
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
    }}
}}";

    private static string BuildImplicitPbrMaterial(
        TextureAsset asset,
        string normalStage,
        string ormStage)
        => $@"{asset.ShaderName}
{{
    qer_editorimage {asset.EntryPath}
    {{
        stage diffuseMap
        map {asset.EntryPath}
        rgbGen identity
    }}
{normalStage}
{ormStage}
    {{
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
    }}
}}";

    internal static string MergePbrStages(
        string originalBlock,
        TextureAsset asset,
        string normalStage,
        string ormStage)
    {
        string cleaned = RemoveExistingPbrResponseStages(originalBlock);
        var blocks = FindTopLevelStageBlocks(cleaned);

        TextRange? diffuse = blocks.FirstOrDefault(b =>
            Regex.IsMatch(b.Text, @"(?im)^\s*stage\s+diffuseMap\b"));

        if (diffuse is null || diffuse.Value.Text is null)
        {
            string imagePattern = $@"(?im)^\s*map\s+({Regex.Escape(asset.EntryPath)}|{Regex.Escape(asset.ShaderName)})\s*$";
            diffuse = blocks.FirstOrDefault(b => Regex.IsMatch(b.Text, imagePattern));
        }

        int insertAt;
        if (diffuse is not null && diffuse.Value.Text is not null)
        {
            insertAt = diffuse.Value.End;
        }
        else
        {
            var lightmap = blocks.FirstOrDefault(b =>
                Regex.IsMatch(b.Text, @"(?im)^\s*map\s+\$lightmap\b"));
            insertAt = lightmap.Text is not null
                ? lightmap.Start
                : FindOuterClose(cleaned);
        }

        string insertion =
            Environment.NewLine + normalStage +
            Environment.NewLine + ormStage +
            Environment.NewLine;

        return cleaned.Insert(insertAt, insertion);
    }

    private static string RemoveExistingPbrResponseStages(string materialBlock)
    {
        var ranges = FindTopLevelStageBlocks(materialBlock)
            .Where(b =>
                Regex.IsMatch(b.Text,
                    @"(?im)^\s*stage\s+(normalMap|normalParallaxMap|bumpMap|bumpParallaxMap|ormMap|specularMap)\b"))
            .OrderByDescending(b => b.Start)
            .ToList();

        string result = materialBlock;
        foreach (var range in ranges)
        {
            int start = range.Start;
            int end = range.End;
            while (start > 0 && (result[start - 1] == ' ' || result[start - 1] == '\t'))
                start--;
            if (start > 0 && result[start - 1] == '\n') start--;
            result = result.Remove(start, end - start);
        }

        return result;
    }

    private static List<TextRange> FindTopLevelStageBlocks(string materialBlock)
    {
        var result = new List<TextRange>();
        int outerOpen = materialBlock.IndexOf('{');
        if (outerOpen < 0) return result;
        int outerClose = Pk3Service.FindMatchingBrace(materialBlock, outerOpen);
        if (outerClose < 0) return result;

        bool lineComment = false;
        bool blockComment = false;
        bool quoted = false;

        for (int i = outerOpen + 1; i < outerClose; i++)
        {
            char ch = materialBlock[i];
            char next = i + 1 < outerClose ? materialBlock[i + 1] : '\0';

            if (lineComment)
            {
                if (ch == '\n') lineComment = false;
                continue;
            }

            if (blockComment)
            {
                if (ch == '*' && next == '/')
                {
                    blockComment = false;
                    i++;
                }
                continue;
            }

            if (!quoted && ch == '/' && next == '/')
            {
                lineComment = true;
                i++;
                continue;
            }

            if (!quoted && ch == '/' && next == '*')
            {
                blockComment = true;
                i++;
                continue;
            }

            if (ch == '"')
            {
                quoted = !quoted;
                continue;
            }

            if (quoted || ch != '{') continue;

            int close = Pk3Service.FindMatchingBrace(materialBlock, i);
            if (close < 0 || close > outerClose)
                throw new InvalidDataException("Unbalanced stage block.");

            result.Add(new TextRange(i, close + 1, materialBlock[i..(close + 1)]));
            i = close;
        }

        return result;
    }

    private static int FindOuterClose(string materialBlock)
    {
        int open = materialBlock.IndexOf('{');
        if (open < 0) throw new InvalidDataException("Material block has no opening brace.");
        int close = Pk3Service.FindMatchingBrace(materialBlock, open);
        if (close < 0) throw new InvalidDataException("Material block has unbalanced braces.");
        return close;
    }

    internal static string ReplaceMaterialBlock(
        string fullScriptText,
        string shaderName,
        string replacementBlock)
    {
        var match = Regex.Match(
            fullScriptText,
            $@"(?im)^\s*{Regex.Escape(shaderName)}\s*\{{");
        if (!match.Success)
            throw new InvalidDataException(
                $"Material '{shaderName}' was not found in its effective source script.");

        int open = fullScriptText.IndexOf('{', match.Index);
        int close = Pk3Service.FindMatchingBrace(fullScriptText, open);
        if (open < 0 || close < 0)
            throw new InvalidDataException(
                $"Material '{shaderName}' has unbalanced braces in its source script.");

        return fullScriptText[..match.Index] +
               replacementBlock.Trim() +
               fullScriptText[(close + 1)..];
    }

    private static byte[] EncodeScript(string text)
        => Encoding.Latin1.GetBytes(text);

    private static void WriteUnique(
        ZipArchive zip,
        HashSet<string> writtenPaths,
        string path,
        byte[] bytes)
    {
        path = path.Replace('\\', '/');
        if (!writtenPaths.Add(path))
            throw new InvalidDataException($"Duplicate PK3 output path: {path}");

        var e = zip.CreateEntry(path, CompressionLevel.Optimal);
        using var s = e.Open();
        s.Write(bytes);
    }
}
