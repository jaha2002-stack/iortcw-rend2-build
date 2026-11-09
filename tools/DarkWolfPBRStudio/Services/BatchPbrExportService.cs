using DarkWolfPBRStudio.Models;
using System.IO.Compression;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Security.Cryptography;

namespace DarkWolfPBRStudio.Services;

public static class BatchPbrExportService
{
    public static void Export(string outputPk3, IReadOnlyList<BatchMaterialItem> items)
    {
        if (items.Count == 0) throw new InvalidOperationException("Batch is empty.");

        Directory.CreateDirectory(Path.GetDirectoryName(outputPk3) ?? ".");
        if (File.Exists(outputPk3)) File.Delete(outputPk3);

        using var zip = ZipFile.Open(outputPk3, ZipArchiveMode.Create);
        var materialBlocks = new List<string>();
        var manifestItems = new List<object>();

        foreach (var item in items.OrderBy(x => x.Asset.ShaderName, StringComparer.OrdinalIgnoreCase))
        {
            var asset = item.Asset;
            var settings = item.Settings;
            var pbr = item.Result;

            if (item.IncludeBaseColor)
            {
                var bytes = ImageService.EncodePreservingExtension(item.BaseColor, asset.Extension);
                Write(zip, asset.EntryPath, bytes);
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

                Write(zip, normalPath, File.ReadAllBytes(tmpN));
                Write(zip, ormPath, File.ReadAllBytes(tmpO));
                if (settings.ParallaxEnabled)
                {
                    Write(zip, normalHeightPath, File.ReadAllBytes(tmpNh));
                    Write(zip, heightPath, File.ReadAllBytes(tmpH));
                }
            }
            finally
            {
                foreach (string p in new[] { tmpN, tmpNh, tmpH, tmpO })
                    try { File.Delete(p); } catch { }
            }

            string normalStage = BuildNormalStage(asset, settings);
            string ormStage = $@"    {{
        stage ormMap
        map {asset.ShaderName}_orm
    }}";

            string block = item.ExistingMaterial is null
                ? BuildImplicitMaterial(asset, normalStage, ormStage)
                : MergePbrStages(item.ExistingMaterial.Block, normalStage, ormStage);

            materialBlocks.Add(block.Trim());

            manifestItems.Add(new
            {
                source = asset.EntryPath,
                shader = asset.ShaderName,
                materialMode = item.ExistingMaterial is null ? "implicit-auto-mtr" : "scripted-merged-mtr",
                scriptedSource = item.ExistingMaterial is null ? null : new
                {
                    item.ExistingMaterial.SourcePk3,
                    item.ExistingMaterial.ScriptPath
                },
                maps = new
                {
                    normal = normalPath,
                    normalHeight = settings.ParallaxEnabled ? normalHeightPath : null,
                    height = settings.ParallaxEnabled ? heightPath : null,
                    orm = ormPath,
                    ormChannels = "R=AO, G=Roughness, B=Metallic"
                },
                generationMode = settings.GenerationMode.ToString(),
                macroReliefBoost = settings.MacroReliefBoost,
                pbr = settings,
                validation = pbr.Report
            });
        }

        string combined = string.Join(Environment.NewLine + Environment.NewLine, materialBlocks) + Environment.NewLine;

        // Unique deterministic basename prevents multiple exported PK3s from
        // shadowing each other's script file in RTCW's scripts namespace.
        string materialKey = string.Join("\n",
            items.Select(x => x.Asset.ShaderName)
                 .OrderBy(x => x, StringComparer.OrdinalIgnoreCase));
        string key = Convert.ToHexString(SHA1.HashData(Encoding.UTF8.GetBytes(materialKey)))
            .ToLowerInvariant()[..10];
        string scriptBase = $"scripts/dw_pbrstudio_v205_{key}";
        byte[] scriptBytes = Encoding.UTF8.GetBytes(combined);

        // Rend2 lists *.shader files, then loads a same-basename *.mtr in preference.
        // Both files are intentional and must stay paired.
        Write(zip, scriptBase + ".shader", scriptBytes);
        Write(zip, scriptBase + ".mtr", scriptBytes);

        var manifest = new
        {
            generator = "DarkWolf PBR Studio V2.05 Physical Relief Batch Material Set",
            target = "ioRTCW Rend2 DarkWolf PBR V3.2 Physical Relief / POM",
            textureCount = items.Count,
            combinedShader = scriptBase + ".shader",
            combinedMtr = scriptBase + ".mtr",
            generatedUtc = DateTime.UtcNow,
            items = manifestItems
        };
        Write(zip, "darkwolf_pbrstudio/batch_manifest_v205.json",
            JsonSerializer.SerializeToUtf8Bytes(manifest, new JsonSerializerOptions { WriteIndented = true }));
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

    private static string BuildImplicitMaterial(TextureAsset asset, string normalStage, string ormStage)
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

    internal static string MergePbrStages(string originalBlock, string normalStage, string ormStage)
    {
        string merged = ReplaceStageIfPresent(originalBlock, new[] { "normalMap", "normalParallaxMap" }, normalStage);
        if (ReferenceEquals(merged, originalBlock) || merged == originalBlock)
            merged = InsertBeforeMaterialClose(merged, normalStage);

        string afterOrm = ReplaceStageIfPresent(merged, new[] { "ormMap" }, ormStage);
        if (afterOrm == merged)
            afterOrm = InsertBeforeMaterialClose(afterOrm, ormStage);

        return afterOrm;
    }

    private static string ReplaceStageIfPresent(string block, IReadOnlyCollection<string> stageNames, string replacement)
    {
        foreach (string stageName in stageNames)
        {
            var m = Regex.Match(block, $@"(?ims)\{{\s*stage\s+{Regex.Escape(stageName)}\b");
            if (!m.Success) continue;

            int open = block.IndexOf('{', m.Index);
            int close = FindMatchingBrace(block, open);
            if (open >= 0 && close > open)
                return block[..open] + replacement + block[(close + 1)..];
        }
        return block;
    }

    private static string InsertBeforeMaterialClose(string block, string stage)
    {
        int open = block.IndexOf('{');
        if (open < 0) throw new InvalidDataException("Material block has no opening brace.");
        int close = FindMatchingBrace(block, open);
        if (close < 0) throw new InvalidDataException("Material block has unbalanced braces.");

        string before = block[..close].TrimEnd();
        string after = block[close..];
        return before + Environment.NewLine + stage + Environment.NewLine + after;
    }

    private static int FindMatchingBrace(string text, int open)
    {
        int depth = 0;
        bool lineComment = false, blockComment = false, quoted = false;

        for (int i = open; i < text.Length; i++)
        {
            char ch = text[i];
            char next = i + 1 < text.Length ? text[i + 1] : '\0';

            if (lineComment)
            {
                if (ch == '\n') lineComment = false;
                continue;
            }
            if (blockComment)
            {
                if (ch == '*' && next == '/') { blockComment = false; i++; }
                continue;
            }
            if (!quoted && ch == '/' && next == '/') { lineComment = true; i++; continue; }
            if (!quoted && ch == '/' && next == '*') { blockComment = true; i++; continue; }
            if (ch == '"') { quoted = !quoted; continue; }
            if (quoted) continue;

            if (ch == '{') depth++;
            else if (ch == '}')
            {
                depth--;
                if (depth == 0) return i;
            }
        }
        return -1;
    }

    private static void Write(ZipArchive zip, string path, byte[] bytes)
    {
        var e = zip.CreateEntry(path.Replace('\\', '/'), CompressionLevel.Optimal);
        using var s = e.Open();
        s.Write(bytes);
    }
}
