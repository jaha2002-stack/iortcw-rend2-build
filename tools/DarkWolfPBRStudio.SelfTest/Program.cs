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

var nh = ImageService.ToBgra(pbr.NormalHeight, out var nw, out var nhh);
byte minAlpha = 255, maxAlpha = 0;
for (int i = 3; i < nh.Length; i += 4)
{
    minAlpha = Math.Min(minAlpha, nh[i]);
    maxAlpha = Math.Max(maxAlpha, nh[i]);
}
Require(maxAlpha - minAlpha > 40, "_nh alpha contains meaningful height range");

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

    var mtrEntry = zip.Entries.Single(e => e.FullName.StartsWith("scripts/dw_pbrstudio_v203_", StringComparison.OrdinalIgnoreCase));
    using var sr = new StreamReader(mtrEntry.Open());
    string mtr = sr.ReadToEnd();
    Require(mtr.Contains("stage normalParallaxMap"), "explicit MTR uses normalParallaxMap");
    Require(mtr.Contains("parallaxDepth"), "explicit MTR writes parallaxDepth");
    Require(mtr.Contains("stage ormMap"), "explicit MTR uses ormMap");
}
finally
{
    try { Directory.Delete(temp, true); } catch { }
}

Console.WriteLine("DARKWOLF_PBR_STUDIO_V203_SELFTEST_PASS");
