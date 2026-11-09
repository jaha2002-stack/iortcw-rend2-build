using DarkWolfPBRStudio.Models;
using DarkWolfPBRStudio.Services;
using System.IO.Compression;
using System.Text.Json;
using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio;

internal static class V206LabRunner
{
    private sealed record FoundTexture(string Pk3Path, TextureAsset Asset);

    public static async Task<int> RunAsync(string[] args)
    {
        var a = Parse(args);
        string pk3Dir = Need(a, "pk3-dir");
        string shader = Need(a, "shader").Replace('\\','/');
        string outDir = Need(a, "out");
        string sdCli = Need(a, "sd-cli");
        string sdModel = Need(a, "sd-model");
        string finishText = Need(a, "finish");
        string extra = a.TryGetValue("sd-extra", out var ev) ? ev : "";
        double strength = a.TryGetValue("strength", out var sv)
            ? double.Parse(sv, System.Globalization.CultureInfo.InvariantCulture) : 0.34;
        var finish = Enum.Parse<SurfaceFinish>(finishText, true);
        long[] seeds = (a.TryGetValue("seeds", out var seedText) ? seedText : "260601,260602,260603")
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(long.Parse).Take(3).ToArray();
        if (seeds.Length != 3) throw new ArgumentException("--seeds must contain exactly 3 values.");

        Directory.CreateDirectory(outDir);
        var found = FindTexture(pk3Dir, shader);
        var pk3 = new Pk3Service();
        byte[] bytes = pk3.ReadEntry(found.Pk3Path, found.Asset.EntryPath);
        BitmapSource source = ImageService.Load(bytes, found.Asset.Extension);
        string input = Path.Combine(outDir, "source.png");
        ImageService.SavePng(source, input);

        MaterialAnalysis analysis = MaterialClassifier.Analyze(found.Asset.EntryPath, source);
        MaterialKind kind = analysis.Kind;
        var profile = MaterialProfile.For(kind);
        string prompt = AiMaterialAuthoringPresets.BuildPrompt(profile, finish);

        var sd = new StableDiffusionService();
        var records = new List<object>();

        for (int i = 0; i < seeds.Length; i++)
        {
            int n = i + 1;
            long seed = seeds[i];
            string candidate = Path.Combine(outDir, $"variant_{n}_basecolor.png");
            await sd.Img2ImgAsync(sdCli, sdModel, input, candidate, prompt, strength, seed, extra, CancellationToken.None);
            var baseColor = ImageService.LoadFile(candidate);

            var settings = PbrSettings.FromProfile(profile);
            settings.GenerationMode = PbrGenerationMode.PhysicalReliefPOM;
            settings.SurfaceFinish = finish;
            settings.NormalStrength = 20;
            settings.HeightContrast = 1.0;
            settings.MacroReliefBoost = 0.75;
            settings.ParallaxEnabled = true;
            settings.ParallaxDepth = kind switch
            {
                MaterialKind.SnowyStone => 0.008,
                MaterialKind.Stone => 0.010,
                MaterialKind.Brick => 0.010,
                _ => Math.Min(0.010, Math.Max(0.004, profile.ParallaxDepth))
            };

            PbrResult result = PbrGenerator.Generate(baseColor, settings);
            string previewDir = Path.Combine(outDir, $"variant_{n}_maps");
            Directory.CreateDirectory(previewDir);
            ImageService.SavePng(result.Height, Path.Combine(previewDir, "height.png"));
            ImageService.SavePng(result.Normal, Path.Combine(previewDir, "normal.png"));
            ImageService.SavePng(result.Orm, Path.Combine(previewDir, "orm.png"));

            MaterialDefinitionInfo? existing = pk3.FindMaterialDefinitionInDirectory(found.Pk3Path, shader);
            var item = new BatchMaterialItem
            {
                Asset = found.Asset,
                BaseColor = baseColor,
                Analysis = analysis,
                Settings = settings,
                Result = result,
                ExistingMaterial = existing,
                IncludeBaseColor = true
            };
            string outputPk3 = Path.Combine(outDir, $"variant_{n}.pk3");
            BatchPbrExportService.Export(outputPk3, new[] { item });

            records.Add(new
            {
                variant = n,
                seed,
                finish = finish.ToString(),
                shader,
                sourcePk3 = Path.GetFileName(found.Pk3Path),
                sourceEntry = found.Asset.EntryPath,
                analysis = analysis.Summary,
                settings.ParallaxDepth,
                report = result.Report.Summary,
                baseColor = Path.GetFileName(candidate),
                pk3 = Path.GetFileName(outputPk3)
            });

            Console.WriteLine($"LAB_VARIANT_READY shader={shader} variant={n} seed={seed} finish={finish} parallaxDepth={settings.ParallaxDepth:0.000}");
        }

        File.WriteAllText(Path.Combine(outDir, "lab_manifest.json"),
            JsonSerializer.Serialize(new { generator="DarkWolf PBR Studio V2.06 AI Material Authoring", shader, finish=finish.ToString(), prompt, variants=records },
                new JsonSerializerOptions { WriteIndented = true }));

        Console.WriteLine($"DARKWOLF_PBR_STUDIO_V206_LAB_PASS shader={shader} finish={finish}");
        return 0;
    }

    private static FoundTexture FindTexture(string dir, string shader)
    {
        if (!Directory.Exists(dir)) throw new DirectoryNotFoundException(dir);
        foreach (string file in Directory.EnumerateFiles(dir, "*.pk3", SearchOption.TopDirectoryOnly)
                     .OrderBy(x => Path.GetFileName(x), StringComparer.OrdinalIgnoreCase))
        {
            using var zip = ZipFile.OpenRead(file);
            foreach (var e in zip.Entries)
            {
                if (e.Length <= 0) continue;
                string path = e.FullName.Replace('\\','/');
                string ext = Path.GetExtension(path).ToLowerInvariant();
                if (ext is not (".jpg" or ".jpeg" or ".png" or ".tga")) continue;
                string stem = path[..^ext.Length];
                if (!stem.Equals(shader, StringComparison.OrdinalIgnoreCase)) continue;
                return new FoundTexture(file, new TextureAsset
                {
                    EntryPath = path,
                    DisplayName = Path.GetFileName(path),
                    Extension = ext,
                    ShaderName = shader,
                    Size = e.Length
                });
            }
        }
        throw new FileNotFoundException($"Texture for shader '{shader}' was not found in {dir}");
    }

    private static Dictionary<string,string> Parse(string[] args)
    {
        var d = new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < args.Length; i++)
        {
            string k = args[i];
            if (!k.StartsWith("--")) continue;
            if (k.Equals("--lab-author", StringComparison.OrdinalIgnoreCase)) { d["lab-author"]="1"; continue; }
            if (i + 1 >= args.Length) throw new ArgumentException($"Missing value after {k}");
            d[k[2..]] = args[++i];
        }
        return d;
    }

    private static string Need(Dictionary<string,string> a, string key)
        => a.TryGetValue(key, out var v) && !string.IsNullOrWhiteSpace(v)
            ? v : throw new ArgumentException($"Missing --{key}");
}
