using System.IO;
using DarkWolfPBRStudio.Models;
using DarkWolfPBRStudio.Services;
using System.IO.Compression;
using System.Windows.Media;
using System.Windows.Media.Imaging;

static void Require(bool ok, string message)
{
    if (!ok) throw new Exception("SELFTEST FAIL: " + message);
    Console.WriteLine("PASS: " + message);
}

static BitmapSource MakeWavyStone(int w, int h)
{
    var baseStone = ImageService.ToBgra(MakeTileableStone(w, h), out _, out _);
    var px = (byte[])baseStone.Clone();

    for (int y = 0; y < h; y++)
    {
        for (int x = 0; x < w; x++)
        {
            int p = (y * w + x) * 4;
            double wave = 18.0 * Math.Sin(2.0 * Math.PI * y / 5.0)
                        + 9.0 * Math.Sin(2.0 * Math.PI * (x + y) / 7.0);
            for (int c = 0; c < 3; c++)
                px[p + c] = (byte)Math.Clamp((int)Math.Round(px[p + c] + wave), 0, 255);
        }
    }

    var bmp = BitmapSource.Create(w, h, 96, 96, PixelFormats.Bgra32, null, px, w * 4);
    bmp.Freeze();
    return bmp;
}

static double HighFrequencyEnergy(BitmapSource image)
{
    var px = ImageService.ToBgra(image, out int w, out int h);
    double sum = 0.0;
    int n = 0;

    for (int y = 1; y < h - 1; y++)
    {
        for (int x = 1; x < w - 1; x++)
        {
            int p = (y * w + x) * 4;
            double c0 = px[p] / 255.0;
            double local = (
                px[((y - 1) * w + x) * 4] +
                px[((y + 1) * w + x) * 4] +
                px[(y * w + x - 1) * 4] +
                px[(y * w + x + 1) * 4]) / (4.0 * 255.0);
            double d = c0 - local;
            sum += d * d;
            n++;
        }
    }

    return n == 0 ? 0.0 : Math.Sqrt(sum / n);
}

static (double Seam, double Face) KnownStoneHeights(BitmapSource height)
{
    var px = ImageService.ToBgra(height, out int w, out int h);
    double seam = 0.0, face = 0.0;
    int ns = 0, nf = 0;

    for (int y = 0; y < h; y++)
    {
        for (int x = 0; x < w; x++)
        {
            double sx = Math.Abs(Math.Sin(2.0 * Math.PI * x / 32.0));
            double sy = Math.Abs(Math.Sin(2.0 * Math.PI * y / 24.0));
            double v = px[(y * w + x) * 4] / 255.0;

            if (Math.Min(sx, sy) < 0.10)
            {
                seam += v;
                ns++;
            }
            else if (sx > 0.75 && sy > 0.75)
            {
                face += v;
                nf++;
            }
        }
    }

    return (ns == 0 ? 0 : seam / ns, nf == 0 ? 0 : face / nf);
}

static BitmapSource MakeTileableStone(int w, int h)
{
    var px = new byte[w * h * 4];
    for (int y = 0; y < h; y++)
    {
        for (int x = 0; x < w; x++)
        {
            double sx = Math.Sin(2.0 * Math.PI * x / 32.0);
            double sy = Math.Sin(2.0 * Math.PI * y / 24.0);
            double mortar = Math.Min(Math.Abs(sx), Math.Abs(sy));
            double stone = 0.52 + 0.18 * Math.Sin(2.0 * Math.PI * x / 64.0) * Math.Cos(2.0 * Math.PI * y / 48.0);
            double snow = 0.12 * Math.Max(0, Math.Cos(2.0 * Math.PI * y / 64.0));
            double v = Math.Clamp(stone + snow - (mortar < 0.12 ? 0.22 : 0.0), 0.08, 0.92);

            int p = (y * w + x) * 4;
            px[p] = (byte)Math.Round(v * 220);
            px[p + 1] = (byte)Math.Round(v * 235);
            px[p + 2] = (byte)Math.Round(v * 245);
            px[p + 3] = 255;
        }
    }
    var bmp = BitmapSource.Create(w, h, 96, 96, PixelFormats.Bgra32, null, px, w * 4);
    bmp.Freeze();
    return bmp;
}

var source = MakeTileableStone(128, 128);

var analysis = MaterialClassifier.Analyze("textures/snow/s_cathedrale_c06.jpg", source);
Require(analysis.Kind == MaterialKind.SnowyStone, "snow cathedral path classifies as SnowyStone");
Require(analysis.Confidence >= 0.60, "material classification has useful confidence");

var settings = PbrSettings.FromProfile(MaterialProfile.For(analysis.Kind));
settings.GenerationMode = PbrGenerationMode.ReferenceHandGenerated;
settings.NormalStrength = 20;
settings.HeightContrast = 1.0;
var pbr = PbrGenerator.Generate(source, settings);
Console.WriteLine("REFERENCE REPORT: " + pbr.Report.Summary);

var macroSettings = PbrSettings.FromProfile(MaterialProfile.For(analysis.Kind));
macroSettings.GenerationMode = PbrGenerationMode.MacroReliefEnhanced;
macroSettings.NormalStrength = 20;
macroSettings.HeightContrast = 1.0;
macroSettings.MacroReliefBoost = 0.75;
var macroPbr = PbrGenerator.Generate(source, macroSettings);
Console.WriteLine("MACRO REPORT: " + macroPbr.Report.Summary);

var physicalSettings = PbrSettings.FromProfile(MaterialProfile.For(analysis.Kind));
physicalSettings.GenerationMode = PbrGenerationMode.PhysicalReliefPOM;
physicalSettings.NormalStrength = 20;
physicalSettings.HeightContrast = 1.0;
physicalSettings.MacroReliefBoost = 0.75;
physicalSettings.PhysicalNormalCoupling = 1.25;
physicalSettings.ParallaxEnabled = true;
physicalSettings.ParallaxDepth = 0.010;
var physicalPbr = PbrGenerator.Generate(source, physicalSettings);
Console.WriteLine("PHYSICAL RELIEF REPORT: " + physicalPbr.Report.Summary);

Require(pbr.Height.PixelWidth == 128 && pbr.Height.PixelHeight == 128, "Height dimensions preserved");
Require(pbr.Normal.PixelWidth == 128 && pbr.Orm.PixelHeight == 128, "Normal/ORM dimensions preserved");
Require(pbr.Report.MeanNormalAngleDeg > 3.0, "Normal contains real relief");
Require(pbr.Report.P90NormalAngleDeg < 58.5, "Normal slopes stay within safety range");
Require(pbr.Report.MeanMetallic < 0.02, "Snowy stone remains dielectric");
Require(pbr.Report.MeanRoughness > 0.45 && pbr.Report.MeanRoughness < 0.98, "Roughness is physically plausible");
Require(pbr.Report.MeanAo > 0.50 && pbr.Report.MeanAo <= 1.0, "AO is physically bounded");
Require(macroPbr.Report.P90NormalAngleDeg > pbr.Report.P90NormalAngleDeg + 2.0,
    "macro mode increases broad structural relief over hand reference");
Require(Math.Abs(macroPbr.Report.MeanAo - pbr.Report.MeanAo) < 0.002,
    "macro mode preserves hand-reference AO response");
Require(Math.Abs(macroPbr.Report.MeanRoughness - pbr.Report.MeanRoughness) < 0.002,
    "macro mode preserves hand-reference roughness response");
var refHeightBytes = ImageService.ToBgra(pbr.Height, out _, out _);
var macroHeightBytes = ImageService.ToBgra(macroPbr.Height, out _, out _);
Require(refHeightBytes.SequenceEqual(macroHeightBytes),
    "macro mode keeps exact hand-reference height field (no new pits/holes)");

var macroNormalBytes = ImageService.ToBgra(macroPbr.Normal, out _, out _);
var physicalNormalBytes = ImageService.ToBgra(physicalPbr.Normal, out _, out _);
var macroOrmBytes = ImageService.ToBgra(macroPbr.Orm, out _, out _);
var physicalOrmBytes = ImageService.ToBgra(physicalPbr.Orm, out _, out _);
Require(!macroNormalBytes.SequenceEqual(physicalNormalBytes),
    "V2.06.1 PhysicalReliefPOM couples the physical Height field into Normal RGB");
Require(macroOrmBytes.SequenceEqual(physicalOrmBytes),
    "PhysicalReliefPOM preserves validated V2.03 ORM exactly");

// Coupling must affect only tangent-space Normal. Height/POM geometry itself remains
// byte-identical so the control cannot silently reshape the displacement field.
var uncoupledSettings = PbrSettings.FromProfile(MaterialProfile.For(analysis.Kind));
uncoupledSettings.GenerationMode = PbrGenerationMode.PhysicalReliefPOM;
uncoupledSettings.NormalStrength = 20;
uncoupledSettings.HeightContrast = 1.0;
uncoupledSettings.MacroReliefBoost = 0.75;
uncoupledSettings.PhysicalNormalCoupling = 0.0;
uncoupledSettings.ParallaxEnabled = true;
uncoupledSettings.ParallaxDepth = 0.010;
var uncoupledPbr = PbrGenerator.Generate(source, uncoupledSettings);
Require(ImageService.ToBgra(uncoupledPbr.Height, out _, out _)
        .SequenceEqual(ImageService.ToBgra(physicalPbr.Height, out _, out _)),
    "V2.06.1 normal coupling does not change Physical Height/POM geometry");
Require(!ImageService.ToBgra(uncoupledPbr.Normal, out _, out _)
        .SequenceEqual(ImageService.ToBgra(physicalPbr.Normal, out _, out _)),
    "V2.06.1 normal coupling has an observable effect on Normal RGB");

// V2.06 invariant: Dry stays byte-identical to V2.05.2 while authored finishes
// change only the physical response maps, never metallic classification or Height/POM.
var dryV206 = PbrSettings.FromProfile(MaterialProfile.For(MaterialKind.Stone));
dryV206.GenerationMode = PbrGenerationMode.PhysicalReliefPOM;
dryV206.ParallaxEnabled = true;
dryV206.ParallaxDepth = 0.010;
dryV206.SurfaceFinish = SurfaceFinish.Dry;
var dryV206Pbr = PbrGenerator.Generate(source, dryV206);

var wetV206 = PbrSettings.FromProfile(MaterialProfile.For(MaterialKind.Stone));
wetV206.GenerationMode = PbrGenerationMode.PhysicalReliefPOM;
wetV206.ParallaxEnabled = true;
wetV206.ParallaxDepth = 0.010;
wetV206.SurfaceFinish = SurfaceFinish.Wet;
var wetV206Pbr = PbrGenerator.Generate(source, wetV206);

var snowV206 = PbrSettings.FromProfile(MaterialProfile.For(MaterialKind.Stone));
snowV206.GenerationMode = PbrGenerationMode.PhysicalReliefPOM;
snowV206.ParallaxEnabled = true;
snowV206.ParallaxDepth = 0.010;
snowV206.SurfaceFinish = SurfaceFinish.Snowy;
var snowV206Pbr = PbrGenerator.Generate(source, snowV206);

Require(dryV206Pbr.Report.MeanMetallic < 0.02 &&
        wetV206Pbr.Report.MeanMetallic < 0.02 &&
        snowV206Pbr.Report.MeanMetallic < 0.02,
    "Dry/Wet/Snowy stone remain dielectric");
Require(wetV206Pbr.Report.MeanRoughness < dryV206Pbr.Report.MeanRoughness - 0.03,
    "Wet finish lowers roughness enough for visible GGX highlights");
Require(snowV206Pbr.Report.MeanRoughness > dryV206Pbr.Report.MeanRoughness,
    "Snow finish remains rougher than dry stone");
Require(ImageService.ToBgra(dryV206Pbr.Height, out _, out _)
        .SequenceEqual(ImageService.ToBgra(wetV206Pbr.Height, out _, out _)),
    "Wet finish does not alter validated POM Height");
Require(ImageService.ToBgra(dryV206Pbr.Normal, out _, out _)
        .SequenceEqual(ImageService.ToBgra(wetV206Pbr.Normal, out _, out _)),
    "Wet finish does not alter validated tangent-space Normal");

string wetPrompt = AiMaterialAuthoringPresets.BuildPrompt(
    MaterialProfile.For(MaterialKind.Stone), SurfaceFinish.Wet);
Require(wetPrompt.Contains("no baked specular highlights", StringComparison.OrdinalIgnoreCase),
    "AI authoring prompt forbids painted highlights");
Require(wetPrompt.Contains("preserve exact original UV layout", StringComparison.OrdinalIgnoreCase),
    "AI authoring prompt preserves RTCW UV composition");

// V2.05.2 regression: the rejected game result showed many small wave ridges in
// Height/POM. Feed an intentionally wavy stone diffuse and verify that the new
// stone reconstruction moves those frequencies out of Height while preserving
// a meaningful mortar-to-face depth separation.
var wavySource = MakeWavyStone(128, 128);
var wavySettings = PbrSettings.FromProfile(MaterialProfile.For(MaterialKind.Stone));
wavySettings.GenerationMode = PbrGenerationMode.PhysicalReliefPOM;
wavySettings.NormalStrength = 20;
wavySettings.HeightContrast = 1.0;
wavySettings.MacroReliefBoost = 0.75;
wavySettings.ParallaxEnabled = true;
wavySettings.ParallaxDepth = 0.012;
var wavyPhysical = PbrGenerator.Generate(wavySource, wavySettings);

var wavyReferenceSettings = PbrSettings.FromProfile(MaterialProfile.For(MaterialKind.Stone));
wavyReferenceSettings.GenerationMode = PbrGenerationMode.ReferenceHandGenerated;
wavyReferenceSettings.NormalStrength = 20;
wavyReferenceSettings.HeightContrast = 1.0;
var wavyReference = PbrGenerator.Generate(wavySource, wavyReferenceSettings);

double refHf = HighFrequencyEnergy(wavyReference.Height);
double physicalHf = HighFrequencyEnergy(wavyPhysical.Height);
Console.WriteLine($"STONE WAVE HF: reference={refHf:0.000000} reconstructed={physicalHf:0.000000}");
Require(physicalHf < refHf * 0.58,
    "V2.05.2 stone Height strongly suppresses high-frequency wave embossing");

var knownDepth = KnownStoneHeights(wavyPhysical.Height);
Console.WriteLine($"STONE DEPTH: seam={knownDepth.Seam:0.000} face={knownDepth.Face:0.000}");
Require(knownDepth.Face - knownDepth.Seam > 0.055,
    "V2.05.2 stone Height keeps coherent mortar seams below stone faces");

var wavyMacroSettings = PbrSettings.FromProfile(MaterialProfile.For(MaterialKind.Stone));
wavyMacroSettings.GenerationMode = PbrGenerationMode.MacroReliefEnhanced;
wavyMacroSettings.NormalStrength = 20;
wavyMacroSettings.HeightContrast = 1.0;
wavyMacroSettings.MacroReliefBoost = 0.75;
var wavyMacro = PbrGenerator.Generate(wavySource, wavyMacroSettings);
var wavyMacroNormal = ImageService.ToBgra(wavyMacro.Normal, out _, out _);
var wavyPhysicalNormal = ImageService.ToBgra(wavyPhysical.Normal, out _, out _);
Require(!wavyMacroNormal.SequenceEqual(wavyPhysicalNormal),
    "V2.06.1 couples rebuilt stone Height into Normal while preserving macro/micro detail");

var physicalHeightBytes = ImageService.ToBgra(physicalPbr.Height, out _, out _);
var physicalHeightSamples = new List<byte>();
for (int i = 0; i < physicalHeightBytes.Length; i += 4)
    physicalHeightSamples.Add(physicalHeightBytes[i]);
physicalHeightSamples.Sort();
byte phP05 = physicalHeightSamples[(int)(physicalHeightSamples.Count * 0.05)];
byte phP95 = physicalHeightSamples[(int)(physicalHeightSamples.Count * 0.95)];
Require(phP95 - phP05 >= 28,
    "PhysicalReliefPOM keeps a useful but non-aggressive robust Height range");
Require(physicalHeightSamples[0] >= 24 && physicalHeightSamples[^1] <= 230,
    "PhysicalReliefPOM keeps broad safety headroom away from hard 0/255 plateaus");

var nh = ImageService.ToBgra(physicalPbr.NormalHeight, out var nw, out var nhh);
var coupledNormal = ImageService.ToBgra(physicalPbr.Normal, out _, out _);
var coupledHeight = ImageService.ToBgra(physicalPbr.Height, out _, out _);
byte minAlpha = 255, maxAlpha = 0;
int rgbMismatch = 0, alphaMismatch = 0;
for (int i = 0; i < nh.Length; i += 4)
{
    minAlpha = Math.Min(minAlpha, nh[i + 3]);
    maxAlpha = Math.Max(maxAlpha, nh[i + 3]);
    if (nh[i] != coupledNormal[i] || nh[i + 1] != coupledNormal[i + 1] || nh[i + 2] != coupledNormal[i + 2])
        rgbMismatch++;
    if (nh[i + 3] != coupledHeight[i])
        alphaMismatch++;
}
Require(maxAlpha - minAlpha >= 28, "V2.06.1 _nh alpha contains meaningful Physical Height range");
Require(rgbMismatch == 0, "V2.06.1 _nh RGB is exactly the coupled tangent-space Normal");
Require(alphaMismatch == 0, "V2.06.1 _nh Alpha is exactly the Physical Height used by POM");

var orm = ImageService.ToBgra(pbr.Orm, out _, out _);
double meanMetal = 0, meanRough = 0, meanAo = 0;
int pixels = orm.Length / 4;
for (int p = 0; p < orm.Length; p += 4)
{
    meanMetal += orm[p] / 255.0;
    meanRough += orm[p + 1] / 255.0;
    meanAo += orm[p + 2] / 255.0;
}
meanMetal /= pixels; meanRough /= pixels; meanAo /= pixels;
Require(meanMetal < 0.02, "ORM B=Metallic for stone is zero");
Require(meanRough > 0.45, "ORM G=Roughness is populated");
Require(meanAo > 0.50, "ORM R=AO is populated");

var metalAnalysis = MaterialClassifier.Analyze("textures/metal/steel_plate.jpg", source);
Require(metalAnalysis.Kind == MaterialKind.BareMetal, "metal path classifies as BareMetal");
var metalPbr = PbrGenerator.Generate(source, PbrSettings.FromProfile(MaterialProfile.For(MaterialKind.BareMetal)));
Require(metalPbr.Report.MeanMetallic > 0.95, "bare metal profile produces metallic=1");

string temp = Path.Combine(Path.GetTempPath(), "dw_pbrstudio_v2_selftest_" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(temp);
try
{
    var asset = new TextureAsset
    {
        EntryPath = "textures/snow/s_cathedrale_c06.jpg",
        DisplayName = "s_cathedrale_c06.jpg",
        Extension = ".jpg",
        ShaderName = "textures/snow/s_cathedrale_c06",
        Size = 0
    };

    // Standard V2.02 materials keep parallax off by default; enable it here only
    // to verify the optional _nh/_h export contract.
    settings.ParallaxEnabled = true;
    string pk3 = Path.Combine(temp, "test.pk3");
    PbrExportService.Export(pk3, asset, source, false, pbr, true, settings, analysis, "SelfTest");

    using var zip = ZipFile.OpenRead(pk3);
    var names = zip.Entries.Select(e => e.FullName).ToHashSet(StringComparer.OrdinalIgnoreCase);
    Require(names.Contains("textures/snow/s_cathedrale_c06_n.tga"), "export contains _n");
    Require(names.Contains("textures/snow/s_cathedrale_c06_nh.tga"), "export contains _nh");
    Require(names.Contains("textures/snow/s_cathedrale_c06_h.tga"), "export contains authoring height");
    Require(names.Contains("textures/snow/s_cathedrale_c06_orm.tga"), "export contains _orm");

    byte TgaBpp(string name)
    {
        var e = zip.Entries.Single(x => x.FullName.Equals(name, StringComparison.OrdinalIgnoreCase));
        using var s = e.Open();
        Span<byte> header = stackalloc byte[18];
        int read = s.Read(header);
        if (read != 18) throw new Exception("SELFTEST FAIL: truncated TGA " + name);
        return header[16];
    }
    Require(TgaBpp("textures/snow/s_cathedrale_c06_n.tga") == 24,
        "ordinary Normal exports as reference-compatible 24-bit TGA");
    Require(TgaBpp("textures/snow/s_cathedrale_c06_orm.tga") == 24,
        "ORM exports as reference-compatible 24-bit TGA");
    Require(TgaBpp("textures/snow/s_cathedrale_c06_nh.tga") == 32,
        "_nh remains 32-bit because alpha carries Height");

    var singleShader = zip.Entries.Single(e => e.FullName.StartsWith("scripts/dw_pbrstudio_v2051_", StringComparison.OrdinalIgnoreCase) &&
                                               e.FullName.EndsWith(".shader", StringComparison.OrdinalIgnoreCase));
    var singleMtr = zip.Entries.Single(e => e.FullName.StartsWith("scripts/dw_pbrstudio_v2051_", StringComparison.OrdinalIgnoreCase) &&
                                            e.FullName.EndsWith(".mtr", StringComparison.OrdinalIgnoreCase));
    Require(Path.GetFileNameWithoutExtension(singleShader.FullName) == Path.GetFileNameWithoutExtension(singleMtr.FullName),
        "single export writes same-basename .shader + .mtr registration pair");
    using var shaderSr = new StreamReader(singleShader.Open());
    string fallbackShader = shaderSr.ReadToEnd();
    Require(!fallbackShader.Contains("stage ormMap", StringComparison.OrdinalIgnoreCase),
        "single-export fallback .shader stays legacy-safe and contains no ormMap extension");
    Require(!fallbackShader.Contains("normalParallaxMap", StringComparison.OrdinalIgnoreCase),
        "single-export fallback .shader stays legacy-safe and contains no normalParallaxMap extension");
    Require(fallbackShader.Contains("map textures/snow/s_cathedrale_c06.jpg"),
        "single-export fallback .shader still renders the original diffuse texture");

    using var sr = new StreamReader(singleMtr.Open());
    string mtr = sr.ReadToEnd();
    Require(mtr.Contains("map textures/snow/s_cathedrale_c06.jpg"), "explicit material diffuse stage references the image filename, not the shader token");
    Require(mtr.Contains("stage normalParallaxMap"), "explicit MTR uses normalParallaxMap");
    Require(mtr.Contains("parallaxDepth"), "explicit MTR writes parallaxDepth");
    Require(mtr.Contains("stage ormMap"), "explicit MTR uses ormMap");

    var asset2 = new TextureAsset
    {
        EntryPath = "textures/stone/floor_a.jpg",
        DisplayName = "floor_a.jpg",
        Extension = ".jpg",
        ShaderName = "textures/stone/floor_a",
        Size = 0
    };
    string scriptedFallback = @"textures/stone/floor_a
{
    qer_editorimage textures/stone/floor_a.jpg
    surfaceParm slick
    cull none
    {
        map textures/stone/floor_a
        rgbGen identity
    }
    {
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
    }
    {
        map textures/effects/glow
        blendFunc add
    }
}

textures/stone/untouched_neighbor
{
    qer_editorimage textures/stone/untouched_neighbor.jpg
    {
        map textures/stone/untouched_neighbor.jpg
        rgbGen identity
    }
    {
        map $lightmap
        blendFunc GL_DST_COLOR GL_ZERO
    }
}";
    string scriptedBlock = Pk3Service.ExtractExactMaterialBlock(scriptedFallback, asset2.ShaderName)
        ?? throw new Exception("SELFTEST FAIL: scripted block fixture extraction");

    var scripted = new MaterialDefinitionInfo(
        asset2.ShaderName,
        "pak_custom.pk3",
        "scripts/custom.shader",
        scriptedBlock)
    {
        DiscoveryShaderPath = "scripts/custom.shader",
        FallbackShaderText = scriptedFallback,
        EffectiveScriptText = scriptedFallback
    };

    var batchItems = new[]
    {
        new BatchMaterialItem
        {
            Asset = asset,
            BaseColor = source,
            Analysis = analysis,
            Settings = physicalSettings,
            Result = physicalPbr,
            ExistingMaterial = null,
            IncludeBaseColor = false
        },
        new BatchMaterialItem
        {
            Asset = asset2,
            BaseColor = source,
            Analysis = MaterialClassifier.Analyze(asset2.EntryPath, source),
            Settings = macroSettings,
            Result = macroPbr,
            ExistingMaterial = scripted,
            IncludeBaseColor = false
        }
    };

    string batchPk3 = Path.Combine(temp, "batch_test.pk3");
    BatchPbrExportService.Export(batchPk3, batchItems);

    using var batchZip = ZipFile.OpenRead(batchPk3);
    var batchNames = batchZip.Entries.Select(e => e.FullName).ToHashSet(StringComparer.OrdinalIgnoreCase);
    var implicitShaderEntries = batchZip.Entries.Where(e => e.FullName.StartsWith("scripts/dw_pbrstudio_v2051_", StringComparison.OrdinalIgnoreCase) &&
                                                                      e.FullName.EndsWith(".shader", StringComparison.OrdinalIgnoreCase)).ToList();
    var implicitMtrEntries = batchZip.Entries.Where(e => e.FullName.StartsWith("scripts/dw_pbrstudio_v2051_", StringComparison.OrdinalIgnoreCase) &&
                                                                   e.FullName.EndsWith(".mtr", StringComparison.OrdinalIgnoreCase)).ToList();
    Require(implicitShaderEntries.Count == 1 && implicitMtrEntries.Count == 1,
        "implicit batch materials share one owned same-basename fallback/PBR pair");
    Require(Path.GetFileNameWithoutExtension(implicitShaderEntries[0].FullName) == Path.GetFileNameWithoutExtension(implicitMtrEntries[0].FullName),
        "implicit batch shader/mtr registration pair shares exact basename");
    Require(batchNames.Contains("scripts/custom.shader") && batchNames.Contains("scripts/custom.mtr"),
        "scripted material exports under its original discovery basename");
    Require(batchNames.Contains("textures/snow/s_cathedrale_c06_n.tga"), "batch contains first Normal");
    Require(batchNames.Contains("textures/snow/s_cathedrale_c06_orm.tga"), "batch contains first ORM");
    Require(batchNames.Contains("textures/stone/floor_a_n.tga"), "batch contains second Normal");
    Require(batchNames.Contains("textures/stone/floor_a_orm.tga"), "batch contains second ORM");
    Require(batchNames.Count(x => x.StartsWith("scripts/", StringComparison.OrdinalIgnoreCase)) == 4,
        "mixed batch contains one implicit pair plus one complete scripted-source pair");
    Require(batchNames.Contains("darkwolf_pbrstudio/batch_manifest_v2051.json"),
        "batch contains one inspectable V2.05.1 safe-export manifest");

    using var implicitShaderSr = new StreamReader(implicitShaderEntries[0].Open());
    string implicitFallback = implicitShaderSr.ReadToEnd();
    using var implicitMtrSr = new StreamReader(implicitMtrEntries[0].Open());
    string implicitMtr = implicitMtrSr.ReadToEnd();
    Require(!implicitFallback.Contains("stage ormMap", StringComparison.OrdinalIgnoreCase),
        "implicit batch fallback .shader has no Rend2 PBR-only stage");
    Require(implicitMtr.Contains("stage normalParallaxMap") && implicitMtr.Contains("stage ormMap"),
        "implicit batch .mtr contains the complete PBR/POM response");

    var scriptedShaderEntry = batchZip.Entries.Single(e => e.FullName.Equals("scripts/custom.shader", StringComparison.OrdinalIgnoreCase));
    var scriptedMtrEntry = batchZip.Entries.Single(e => e.FullName.Equals("scripts/custom.mtr", StringComparison.OrdinalIgnoreCase));
    using var scriptedShaderSr = new StreamReader(scriptedShaderEntry.Open());
    string exportedFallback = scriptedShaderSr.ReadToEnd();
    using var scriptedMtrSr = new StreamReader(scriptedMtrEntry.Open());
    string exportedMtr = scriptedMtrSr.ReadToEnd();

    Require(exportedFallback == scriptedFallback,
        "scripted fallback .shader is byte-for-text identical to the complete original shader source");
    Require(exportedMtr.Contains("textures/stone/untouched_neighbor"),
        "scripted .mtr preserves unrelated neighbor material definitions from the original source file");
    Require(exportedMtr.Contains("surfaceParm slick"), "scripted merge preserves surfaceParm");
    Require(exportedMtr.Contains("cull none"), "scripted merge preserves cull state");
    Require(exportedMtr.Contains("textures/effects/glow"), "scripted merge preserves unrelated original stages");
    Require(exportedMtr.Contains("textures/stone/floor_a_n"), "scripted merge inserts generated Normal");
    Require(exportedMtr.Contains("textures/stone/floor_a_orm"), "scripted merge inserts generated ORM");

    string upgradedBlock = Pk3Service.ExtractExactMaterialBlock(exportedMtr, "textures/stone/floor_a")
        ?? throw new Exception("SELFTEST FAIL: upgraded scripted block missing");
    int diffuseIndex = upgradedBlock.IndexOf("map textures/stone/floor_a", StringComparison.OrdinalIgnoreCase);
    int normalIndex = upgradedBlock.IndexOf("stage normalMap", StringComparison.OrdinalIgnoreCase);
    int ormIndex = upgradedBlock.IndexOf("stage ormMap", StringComparison.OrdinalIgnoreCase);
    int lightmapIndex = upgradedBlock.IndexOf("map $lightmap", StringComparison.OrdinalIgnoreCase);
    Require(diffuseIndex >= 0 && normalIndex > diffuseIndex && ormIndex > normalIndex && lightmapIndex > ormIndex,
        "scripted PBR stages are placed canonically after primary diffuse and before lightmap");
}
finally
{
    try { Directory.Delete(temp, true); } catch { }
}

// V2.06.1 AI path hotfix regression: portable model discovery must find
// .safetensors automatically in Tools/StableDiffusionCpp/models-style folders.
string aiPathTemp = Path.Combine(Path.GetTempPath(), "dw_pbrstudio_ai_path_" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(aiPathTemp);
try
{
    string model = Path.Combine(aiPathTemp, "dreamshaper_8.safetensors");
    File.WriteAllBytes(model, new byte[] { 1, 2, 3, 4 });
    Require(StableDiffusionService.IsSupportedModel(model), "AI path hotfix recognizes .safetensors");
    string? discovered = StableDiffusionService.FindModelInDirectory(aiPathTemp, "dreamshaper_8.safetensors");
    Require(string.Equals(discovered, model, StringComparison.OrdinalIgnoreCase),
        "AI path hotfix auto-discovers preferred .safetensors model");
}
finally
{
    try { Directory.Delete(aiPathTemp, true); } catch { }
}

Console.WriteLine("DARKWOLF_PBR_STUDIO_V2061_SELFTEST_PASS");
