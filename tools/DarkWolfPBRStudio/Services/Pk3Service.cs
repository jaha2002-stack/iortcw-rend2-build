using DarkWolfPBRStudio.Models;
using System.IO.Compression;
using System.Text.RegularExpressions;
using System.Text;

namespace DarkWolfPBRStudio.Services;

public sealed class Pk3Service
{
    private static readonly HashSet<string> Extensions = new(StringComparer.OrdinalIgnoreCase)
    { ".jpg", ".jpeg", ".png", ".tga" };

    private sealed record VirtualScript(string Path, string SourcePk3, string Text);

    public IReadOnlyList<TextureAsset> ListTextures(string pk3Path)
    {
        using var zip = ZipFile.OpenRead(pk3Path);
        return zip.Entries
            .Where(e => e.Length > 0 && Extensions.Contains(Path.GetExtension(e.FullName)))
            .Select(e => new TextureAsset
            {
                EntryPath = e.FullName.Replace('\\', '/'),
                DisplayName = Path.GetFileName(e.FullName),
                Extension = Path.GetExtension(e.FullName).ToLowerInvariant(),
                ShaderName = e.FullName[..^Path.GetExtension(e.FullName).Length].Replace('\\', '/'),
                Size = e.Length
            })
            .OrderBy(e => e.EntryPath, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    public byte[] ReadEntry(string pk3Path, string entryPath)
    {
        using var zip = ZipFile.OpenRead(pk3Path);
        var entry = zip.GetEntry(entryPath) ??
                    zip.Entries.FirstOrDefault(e =>
                        e.FullName.Equals(entryPath, StringComparison.OrdinalIgnoreCase));
        if (entry is null) throw new FileNotFoundException("PK3 entry not found", entryPath);

        using var src = entry.Open();
        using var ms = new MemoryStream();
        src.CopyTo(ms);
        return ms.ToArray();
    }

    public bool HasMaterialDefinitionInDirectory(string pk3Path, string shaderName)
        => FindMaterialDefinitionInDirectory(pk3Path, shaderName) is not null;

    public MaterialDefinitionInfo? FindMaterialDefinitionInDirectory(string pk3Path, string shaderName)
    {
        string? dir = Path.GetDirectoryName(pk3Path);
        if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir)) return null;

        // Mirror Rend2's discovery rule instead of independently scanning .mtr files:
        // only scripts/*.shader paths are discovery points. For each discovered
        // basename Rend2 prefers a same-basename .mtr if the virtual filesystem has one.
        //
        // Later archive names replace earlier entries at the same virtual path, matching
        // the override intent of z/zz/zzz PK3 packages closely enough for authoring.
        var virtualScripts = new Dictionary<string, VirtualScript>(StringComparer.OrdinalIgnoreCase);

        foreach (var file in Directory.EnumerateFiles(dir, "*.pk3", SearchOption.TopDirectoryOnly)
                     .OrderBy(x => Path.GetFileName(x), StringComparer.OrdinalIgnoreCase))
        {
            try
            {
                using var zip = ZipFile.OpenRead(file);
                foreach (var e in zip.Entries.OrderBy(x => x.FullName, StringComparer.OrdinalIgnoreCase))
                {
                    string path = e.FullName.Replace('\\', '/');
                    string low = path.ToLowerInvariant();
                    if (!low.StartsWith("scripts/") ||
                        !(low.EndsWith(".shader") || low.EndsWith(".mtr")) ||
                        e.Length <= 0)
                        continue;

                    using var ms = new MemoryStream();
                    using (var src = e.Open()) src.CopyTo(ms);
                    string text = Encoding.Latin1.GetString(ms.ToArray());

                    virtualScripts[path] = new VirtualScript(path, Path.GetFileName(file), text);
                }
            }
            catch
            {
                // A malformed neighboring archive must not make texture browsing unusable.
            }
        }

        var candidates = new List<MaterialDefinitionInfo>();

        foreach (var discovery in virtualScripts.Values
                     .Where(x => x.Path.EndsWith(".shader", StringComparison.OrdinalIgnoreCase))
                     .OrderBy(x => x.Path, StringComparer.OrdinalIgnoreCase))
        {
            string mtrPath = discovery.Path[..^7] + ".mtr";
            VirtualScript effective = virtualScripts.TryGetValue(mtrPath, out var mtr)
                ? mtr
                : discovery;

            string? block = ExtractExactMaterialBlock(effective.Text, shaderName);
            if (block is null) continue;

            candidates.Add(new MaterialDefinitionInfo(
                shaderName,
                effective.SourcePk3,
                effective.Path,
                block)
            {
                DiscoveryShaderPath = discovery.Path,
                FallbackShaderText = discovery.Text,
                EffectiveScriptText = effective.Text
            });
        }

        // Multiple different script files may define the same material. Rend2's historical
        // concatenation order is not an override API; keep the latest deterministic
        // candidate for authoring and export the whole owning script pair in V2.05.1.
        return candidates.LastOrDefault();
    }

    internal static string? ExtractExactMaterialBlock(string text, string shaderName)
    {
        var match = Regex.Match(
            text,
            $@"(?im)^\s*{Regex.Escape(shaderName)}\s*\{{");
        if (!match.Success) return null;

        int brace = text.IndexOf('{', match.Index);
        if (brace < 0) return null;

        int close = FindMatchingBrace(text, brace);
        return close < 0 ? null : text[match.Index..(close + 1)].Trim();
    }

    internal static int FindMatchingBrace(string text, int open)
    {
        int depth = 0;
        bool lineComment = false;
        bool blockComment = false;
        bool quoted = false;

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
}
