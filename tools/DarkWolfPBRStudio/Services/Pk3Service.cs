using DarkWolfPBRStudio.Models;
using System.IO.Compression;
using System.Text.RegularExpressions;

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
    {
        string? dir = Path.GetDirectoryName(pk3Path);
        if (string.IsNullOrEmpty(dir) || !Directory.Exists(dir)) return false;
        foreach (var file in Directory.EnumerateFiles(dir, "*.pk3", SearchOption.TopDirectoryOnly))
        {
            try
            {
                using var zip = ZipFile.OpenRead(file);
                foreach (var e in zip.Entries)
                {
                    var low = e.FullName.ToLowerInvariant();
                    if (!low.StartsWith("scripts/") || !(low.EndsWith(".shader") || low.EndsWith(".mtr"))) continue;
                    using var sr = new StreamReader(e.Open());
                    var text = sr.ReadToEnd();
                    if (Regex.IsMatch(text, $@"(?im)^\s*{Regex.Escape(shaderName)}\s*\{{"))
                        return true;
                }
            }
            catch { }
        }
        return false;
    }
}
