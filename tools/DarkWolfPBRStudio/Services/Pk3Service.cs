using DarkWolfPBRStudio.Models;
using System.IO.Compression;
using System.Text.RegularExpressions;
using System.Text;

namespace DarkWolfPBRStudio.Services;

public sealed class Pk3Service
{
    private static readonly HashSet<string> Extensions = new(StringComparer.OrdinalIgnoreCase)
    { ".jpg", ".jpeg", ".png", ".tga" };

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
        var entry = zip.GetEntry(entryPath) ?? zip.Entries.FirstOrDefault(e => e.FullName.Equals(entryPath, StringComparison.OrdinalIgnoreCase));
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

        var candidates = new List<MaterialDefinitionInfo>();
        foreach (var file in Directory.EnumerateFiles(dir, "*.pk3", SearchOption.TopDirectoryOnly)
                     .OrderBy(x => Path.GetFileName(x), StringComparer.OrdinalIgnoreCase))
        {
            try
            {
                using var zip = ZipFile.OpenRead(file);
                foreach (var e in zip.Entries.OrderBy(x => x.FullName, StringComparer.OrdinalIgnoreCase))
                {
                    var low = e.FullName.ToLowerInvariant();
                    if (!low.StartsWith("scripts/") || !(low.EndsWith(".shader") || low.EndsWith(".mtr"))) continue;

                    using var ms = new MemoryStream();
                    using (var src = e.Open()) src.CopyTo(ms);
                    string text = Encoding.Latin1.GetString(ms.ToArray());

                    string? block = ExtractExactMaterialBlock(text, shaderName);
                    if (block is null) continue;

                    candidates.Add(new MaterialDefinitionInfo(
                        shaderName,
                        Path.GetFileName(file),
                        e.FullName.Replace('\\','/'),
                        block));
                }
            }
            catch
            {
                // A corrupt/unreadable neighboring PK3 must not make the whole texture
                // browser unusable. The batch review will still classify the material
                // as implicit if no readable definition survives.
            }
        }

        // Later PK3/script names are treated as the effective override candidate.
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

        int depth = 0;
        bool lineComment = false;
        bool blockComment = false;
        bool quoted = false;

        for (int i = brace; i < text.Length; i++)
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
                if (depth == 0)
                    return text[match.Index..(i + 1)].Trim();
            }
        }
        return null;
    }
}
