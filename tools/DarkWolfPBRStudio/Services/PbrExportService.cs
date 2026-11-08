using DarkWolfPBRStudio.Models;
using System.IO.Compression;
using System.Text.Json;
using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio.Services;

public static class PbrExportService
{
    public static void Export(
        string outputPk3,
        TextureAsset asset,
        BitmapSource currentBaseColor,
        bool includeBaseColor,
        BitmapSource normal,
        BitmapSource orm,
        bool writeExplicitMtr,
        PbrSettings settings,
        string variantName)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(outputPk3) ?? ".");
        if (File.Exists(outputPk3)) File.Delete(outputPk3);

        using var zip = ZipFile.Open(outputPk3, ZipArchiveMode.Create);

        if (includeBaseColor)
        {
            var bytes = ImageService.EncodePreservingExtension(currentBaseColor, asset.Extension);
            Write(zip, asset.EntryPath, bytes);
        }

        string normalPath = asset.ShaderName + "_n.tga";
        string ormPath = asset.ShaderName + "_orm.tga";

        string tmpN = Path.GetTempFileName();
        string tmpO = Path.GetTempFileName();
        try
        {
            TgaCodec.Save(normal, tmpN);
            TgaCodec.Save(orm, tmpO);
            Write(zip, normalPath, File.ReadAllBytes(tmpN));
            Write(zip, ormPath, File.ReadAllBytes(tmpO));
        }
        finally
        {
            try { File.Delete(tmpN); } catch { }
            try { File.Delete(tmpO); } catch { }
        }

        if (writeExplicitMtr)
        {
            string mtr = $@"{asset.ShaderName}
{{
    qer_editorimage {asset.EntryPath}
    {{
        stage diffuseMap
        map {asset.ShaderName}
        rgbGen identity
    }}
    {{
        stage normalMap
        map {asset.ShaderName}_n
        normalScale 1 1
    }}
    {{
        stage ormMap
        map {asset.ShaderName}_orm
    }}
    {{
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
    }}
}}
";
            string key = Convert.ToHexString(System.Security.Cryptography.SHA1.HashData(System.Text.Encoding.UTF8.GetBytes(asset.ShaderName))).ToLowerInvariant()[..10];
            Write(zip, $"scripts/dw_pbrstudio_{key}.mtr", System.Text.Encoding.UTF8.GetBytes(mtr));
        }

        var manifest = new
        {
            generator = "DarkWolf PBR Studio V1",
            target = "ioRTCW Rend2 DarkWolf r_pbr 3",
            source = asset.EntryPath,
            shader = asset.ShaderName,
            variant = variantName,
            maps = new { normal = normalPath, orm = ormPath, ormChannels = "R=AO, G=Roughness, B=Metallic" },
            pbr = settings,
            explicitMtr = writeExplicitMtr,
            generatedUtc = DateTime.UtcNow
        };
        Write(zip, $"darkwolf_pbrstudio/{Sanitize(asset.ShaderName)}.json",
            JsonSerializer.SerializeToUtf8Bytes(manifest, new JsonSerializerOptions { WriteIndented = true }));
    }

    private static void Write(ZipArchive zip, string path, byte[] bytes)
    {
        var e = zip.CreateEntry(path.Replace('\\', '/'), CompressionLevel.Optimal);
        using var s = e.Open();
        s.Write(bytes);
    }

    private static string Sanitize(string s)
        => string.Concat(s.Select(ch => char.IsLetterOrDigit(ch) ? ch : '_'));
}
