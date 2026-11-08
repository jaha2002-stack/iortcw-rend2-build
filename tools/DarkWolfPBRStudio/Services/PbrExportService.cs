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
        PbrResult pbr,
        bool writeExplicitMtr,
        PbrSettings settings,
        MaterialAnalysis? analysis,
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
        string normalHeightPath = asset.ShaderName + "_nh.tga";
        string heightPath = asset.ShaderName + "_h.tga";
        string ormPath = asset.ShaderName + "_orm.tga";

        string tmpN = Path.GetTempFileName();
        string tmpNh = Path.GetTempFileName();
        string tmpH = Path.GetTempFileName();
        string tmpO = Path.GetTempFileName();
        try
        {
            TgaCodec.Save(pbr.Normal, tmpN);
            TgaCodec.Save(pbr.NormalHeight, tmpNh);
            TgaCodec.Save(pbr.Height, tmpH);
            TgaCodec.Save(pbr.Orm, tmpO);

            Write(zip, normalPath, File.ReadAllBytes(tmpN));
            Write(zip, ormPath, File.ReadAllBytes(tmpO));

            // _nh is the native Rend2 normal+height convention. Its RGB is tangent-space
            // normal and alpha is height. The standalone _h is authoring/debug data.
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

        if (writeExplicitMtr)
        {
            string normalStage = settings.ParallaxEnabled
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

            string mtr = $@"{asset.ShaderName}
{{
    qer_editorimage {asset.EntryPath}
    {{
        stage diffuseMap
        map {asset.ShaderName}
        rgbGen identity
    }}
{normalStage}
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
            string key = Convert.ToHexString(
                System.Security.Cryptography.SHA1.HashData(
                    System.Text.Encoding.UTF8.GetBytes(asset.ShaderName)))
                .ToLowerInvariant()[..10];

            Write(zip, $"scripts/dw_pbrstudio_v203_{key}.mtr", System.Text.Encoding.UTF8.GetBytes(mtr));
        }

        var manifest = new
        {
            generator = "DarkWolf PBR Studio V2.03",
            target = "ioRTCW Rend2 DarkWolf r_pbr 3 / BSP Relight V4.2",
            source = asset.EntryPath,
            shader = asset.ShaderName,
            variant = variantName,
            material = analysis is null ? null : new
            {
                kind = analysis.Kind.ToString(),
                confidence = analysis.Confidence,
                reason = analysis.Reason,
                analysis.MeanLuminance,
                analysis.MeanSaturation,
                analysis.LuminanceStdDev,
                analysis.EdgeDensity
            },
            maps = new
            {
                normal = normalPath,
                normalHeight = settings.ParallaxEnabled ? normalHeightPath : null,
                height = settings.ParallaxEnabled ? heightPath : null,
                orm = ormPath,
                ormChannels = "R=AO, G=Roughness, B=Metallic",
                normalHeightChannels = settings.ParallaxEnabled ? "RGB=Normal XYZ, A=Height" : null
            },
            generationMode = settings.GenerationMode.ToString(),
            macroReliefBoost = settings.MacroReliefBoost,
            pbr = settings,
            validation = pbr.Report,
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
