using System.IO;
using DarkWolfPBRStudio.Models;
using DarkWolfPBRStudio.Services;
using System.IO.Compression;
using System.Text.Json;

namespace DarkWolfPBRStudio.Cli;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            var opt = Parse(args);
            string input = Required(opt, "input");
            string outDir = Required(opt, "outdir");
            string shader = opt.TryGetValue("shader", out var s) ? s : "textures/snow/s_cathedrale_c06";
            string entry = opt.TryGetValue("entry", out var e) ? e : shader + Path.GetExtension(input).ToLowerInvariant();

            Directory.CreateDirectory(outDir);

            var image = ImageService.LoadFile(input);
            var analysis = MaterialClassifier.Analyze(entry, image);
            MaterialKind kind = analysis.Kind;
            if (opt.TryGetValue("profile", out var profileName) &&
                Enum.TryParse<MaterialKind>(profileName, true, out var parsed) &&
                parsed != MaterialKind.Auto)
                kind = parsed;

            var profile = MaterialProfile.For(kind);
            var settings = PbrSettings.FromProfile(profile);
            if (opt.TryGetValue("mode", out var modeName) &&
                Enum.TryParse<PbrGenerationMode>(modeName, true, out var mode))
                settings.GenerationMode = mode;
            ApplyOverrides(opt, settings);

            if (opt.TryGetValue("parallax", out var p))
                settings.ParallaxEnabled = p != "0" && !p.Equals("false", StringComparison.OrdinalIgnoreCase);

            var result = PbrGenerator.Generate(image, settings);

            string baseName = Path.GetFileName(shader);
            ImageService.SavePng(result.Height, Path.Combine(outDir, baseName + "_h_preview.png"));
            ImageService.SavePng(result.Normal, Path.Combine(outDir, baseName + "_n_preview.png"));
            ImageService.SavePng(result.Orm, Path.Combine(outDir, baseName + "_orm_preview.png"));

            var asset = new TextureAsset
            {
                EntryPath = entry.Replace('\\', '/'),
                DisplayName = Path.GetFileName(entry),
                Extension = Path.GetExtension(entry).ToLowerInvariant(),
                ShaderName = shader.Replace('\\', '/'),
                Size = new FileInfo(input).Length
            };

            string fullPk3 = Path.Combine(outDir, "zzz_dw_escape1_outdoor_pbrstudio_v2.pk3");
            PbrExportService.Export(
                fullPk3, asset, image, false, result, true, settings, analysis, "PBR Studio V2.02 structure-preserving");

            string baselinePk3 = Path.Combine(outDir, "zzz_dw_escape1_outdoor_original.pk3");
            WriteBaselinePk3(baselinePk3, shader, entry);

            var proof = new
            {
                generator = "DarkWolf PBR Studio V2.02 CLI",
                source = entry,
                shader,
                imageSize = new[] { image.PixelWidth, image.PixelHeight },
                material = new
                {
                    detected = analysis.Kind.ToString(),
                    used = kind.ToString(),
                    analysis.Confidence,
                    analysis.Reason,
                    analysis.MeanLuminance,
                    analysis.MeanSaturation,
                    analysis.LuminanceStdDev,
                    analysis.EdgeDensity
                },
                settings,
                validation = result.Report,
                outputs = new
                {
                    baselinePk3 = Path.GetFileName(baselinePk3),
                    fullPk3 = Path.GetFileName(fullPk3),
                    normal = shader + "_n.tga",
                    normalHeight = settings.ParallaxEnabled ? shader + "_nh.tga" : null,
                    height = settings.ParallaxEnabled ? shader + "_h.tga" : null,
                    orm = shader + "_orm.tga"
                }
            };
            File.WriteAllText(Path.Combine(outDir, "pbr_studio_v2_proof.json"),
                JsonSerializer.Serialize(proof, new JsonSerializerOptions { WriteIndented = true }));

            Console.WriteLine(JsonSerializer.Serialize(proof, new JsonSerializerOptions { WriteIndented = true }));
            Console.WriteLine("DARKWOLF_PBR_STUDIO_V2_CLI_PASS");
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 1;
        }
    }

    private static void ApplyOverrides(Dictionary<string,string> opt, PbrSettings s)
    {
        SetDouble(opt, "normal-strength", v => s.NormalStrength = v);
        SetDouble(opt, "height-contrast", v => s.HeightContrast = v);
        SetDouble(opt, "fine-weight", v => s.FineWeight = v);
        SetDouble(opt, "coarse-weight", v => s.CoarseWeight = v);
        SetDouble(opt, "chroma-suppression", v => s.ChromaSuppression = v);
        SetDouble(opt, "ao-strength", v => s.AoStrength = v);
        SetDouble(opt, "ao-floor", v => s.AoFloor = v);
        SetDouble(opt, "roughness-base", v => s.RoughnessBase = v);
        SetDouble(opt, "roughness-min", v => s.RoughnessMin = v);
        SetDouble(opt, "roughness-max", v => s.RoughnessMax = v);
        SetDouble(opt, "micro-roughness", v => s.MicroRoughness = v);
        SetDouble(opt, "brightness-roughness", v => s.BrightnessRoughness = v);
        SetDouble(opt, "metallic", v => s.Metallic = v);
        SetDouble(opt, "macro-relief-boost", v => s.MacroReliefBoost = v);
    }

    private static void SetDouble(Dictionary<string,string> opt, string key, Action<double> setter)
    {
        if (!opt.TryGetValue(key, out var raw)) return;
        if (!double.TryParse(raw, System.Globalization.NumberStyles.Float,
            System.Globalization.CultureInfo.InvariantCulture, out var value))
            throw new ArgumentException($"Invalid --{key} value '{raw}'");
        setter(value);
    }

    private static void WriteBaselinePk3(string path, string shader, string entry)
    {
        if (File.Exists(path)) File.Delete(path);
        using var zip = ZipFile.Open(path, ZipArchiveMode.Create);
        string mtr = $@"{shader}
{{
    qer_editorimage {entry}
    {{
        stage diffuseMap
        map {shader}
        rgbGen identity
    }}
    {{
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
    }}
}}
";
        var ze = zip.CreateEntry("scripts/dw_pbrstudio_v2_escape1_original.mtr", CompressionLevel.Optimal);
        using var sw = new StreamWriter(ze.Open());
        sw.Write(mtr);
    }

    private static Dictionary<string,string> Parse(string[] args)
    {
        var d = new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        for (int i=0;i<args.Length;i++)
        {
            if (!args[i].StartsWith("--")) continue;
            string key=args[i][2..];
            string value=(i+1<args.Length && !args[i+1].StartsWith("--")) ? args[++i] : "1";
            d[key]=value;
        }
        return d;
    }

    private static string Required(Dictionary<string,string> d, string key)
        => d.TryGetValue(key, out var v) && !string.IsNullOrWhiteSpace(v)
            ? v : throw new ArgumentException($"Missing --{key}");
}
