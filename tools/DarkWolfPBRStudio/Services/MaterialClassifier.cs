using DarkWolfPBRStudio.Models;
using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio.Services;

public static class MaterialClassifier
{
    public static MaterialAnalysis Analyze(string assetPath, BitmapSource image)
    {
        string path = assetPath.Replace('\\', '/').ToLowerInvariant();
        var px = ImageService.ToBgra(image, out int w, out int h);
        int step = Math.Max(1, Math.Min(w, h) / 192);
        var lumas = new List<double>();
        double satSum = 0.0;
        double edgeSum = 0.0;
        int count = 0;

        double LumaAt(int x, int y)
        {
            int p = (y * w + x) * 4;
            double b = SrgbToLinear(px[p] / 255.0);
            double g = SrgbToLinear(px[p + 1] / 255.0);
            double r = SrgbToLinear(px[p + 2] / 255.0);
            return 0.2126 * r + 0.7152 * g + 0.0722 * b;
        }

        for (int y = 0; y < h; y += step)
        {
            for (int x = 0; x < w; x += step)
            {
                int p = (y * w + x) * 4;
                double b = px[p] / 255.0, g = px[p + 1] / 255.0, r = px[p + 2] / 255.0;
                double mx = Math.Max(r, Math.Max(g, b)), mn = Math.Min(r, Math.Min(g, b));
                double sat = mx <= 1e-5 ? 0 : (mx - mn) / mx;
                double l = LumaAt(x, y);
                double lx = LumaAt((x + step) % w, y);
                double ly = LumaAt(x, (y + step) % h);
                lumas.Add(l);
                satSum += sat;
                edgeSum += Math.Min(1.0, (Math.Abs(lx - l) + Math.Abs(ly - l)) * 4.0);
                count++;
            }
        }

        double mean = lumas.Count == 0 ? 0 : lumas.Average();
        double std = lumas.Count == 0 ? 0 : Math.Sqrt(lumas.Sum(x => (x - mean) * (x - mean)) / lumas.Count);
        double satMean = count == 0 ? 0 : satSum / count;
        double edge = count == 0 ? 0 : edgeSum / count;

        var scores = Enum.GetValues<MaterialKind>().Where(k => k is not MaterialKind.Auto).ToDictionary(k => k, _ => 0.0);
        var reasons = new List<string>();

        void Hit(MaterialKind kind, double score, string reason)
        {
            scores[kind] += score;
            if (score >= 2.0) reasons.Add(reason);
        }

        bool Has(params string[] words) => words.Any(path.Contains);

        if (Has("cathedrale", "castle", "stone", "rock", "masonry")) Hit(MaterialKind.Stone, 5, "stone/masonry path");
        if (Has("snow") && Has("cathedrale", "castle", "stone", "rock", "wall")) Hit(MaterialKind.SnowyStone, 8, "snow-covered masonry path");
        else if (Has("snow", "ice", "frost")) Hit(MaterialKind.SnowIce, 6, "snow/ice path");
        if (Has("brick")) Hit(MaterialKind.Brick, 8, "brick path");
        if (Has("concrete", "cement")) Hit(MaterialKind.Concrete, 8, "concrete path");
        if (Has("plaster", "stucco")) Hit(MaterialKind.Plaster, 8, "plaster path");
        if (Has("wood", "timber", "plank", "beam", "board")) Hit(MaterialKind.Wood, 8, "wood path");
        if (Has("fabric", "cloth", "carpet", "curtain", "flag", "banner")) Hit(MaterialKind.Fabric, 8, "fabric path");
        if (Has("leather")) Hit(MaterialKind.Leather, 8, "leather path");
        if (Has("ceramic", "tile", "porcelain")) Hit(MaterialKind.Ceramic, 7, "ceramic/tile path");
        if (Has("soil", "dirt", "mud", "ground", "earth")) Hit(MaterialKind.Soil, 7, "soil/ground path");

        bool metalWord = Has("metal", "steel", "iron", "chrome", "aluminum", "aluminium", "grate", "pipe", "duct");
        if (metalWord && Has("rust", "corrod")) Hit(MaterialKind.RustedMetal, 9, "rusted metal path");
        else if (metalWord && Has("paint", "painted", "door", "panel")) Hit(MaterialKind.PaintedMetal, 8, "painted metal path");
        else if (metalWord) Hit(MaterialKind.BareMetal, 7, "metal path");
        if (Has("rust")) Hit(MaterialKind.RustedMetal, 7, "rust path");

        if (scores.Values.Max() < 2.0)
        {
            if (satMean < 0.10 && edge < 0.11 && mean > 0.48) Hit(MaterialKind.Plaster, 2.5, "low-saturation smooth surface statistics");
            else if (satMean < 0.12 && edge > 0.18) Hit(MaterialKind.Concrete, 2.2, "low-saturation granular statistics");
            else Hit(MaterialKind.GenericDielectric, 2.0, "no strong semantic path signal");
        }

        var best = scores.OrderByDescending(kv => kv.Value).First();
        var second = scores.OrderByDescending(kv => kv.Value).Skip(1).First();
        double confidence = best.Value <= 0 ? .35 : Math.Clamp(.50 + (best.Value - second.Value) / 12.0, .40, .98);
        string reasonText = reasons.Count == 0 ? "Image statistics fallback." : string.Join("; ", reasons.Distinct());

        return new MaterialAnalysis(best.Key, confidence, reasonText, mean, satMean, std, edge);
    }

    private static double SrgbToLinear(double c)
        => c <= 0.04045 ? c / 12.92 : Math.Pow((c + 0.055) / 1.055, 2.4);
}
