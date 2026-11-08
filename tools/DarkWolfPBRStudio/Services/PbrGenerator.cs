using DarkWolfPBRStudio.Models;
using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio.Services;

public sealed record PbrResult(
    BitmapSource Height,
    BitmapSource Normal,
    BitmapSource NormalHeight,
    BitmapSource Orm,
    PbrValidationReport Report);

public static class PbrGenerator
{
    public static PbrResult Generate(BitmapSource input, PbrSettings settings)
    {
        var px = ImageService.ToBgra(input, out int w, out int h);
        int count = w * h;
        var lum = new double[count];
        var saturation = new double[count];

        for (int i = 0, p = 0; i < count; i++, p += 4)
        {
            double bS = px[p] / 255.0, gS = px[p + 1] / 255.0, rS = px[p + 2] / 255.0;
            double b = SrgbToLinear(bS), g = SrgbToLinear(gS), r = SrgbToLinear(rS);
            lum[i] = 0.2126 * r + 0.7152 * g + 0.0722 * b;

            double mx = Math.Max(rS, Math.Max(gS, bS));
            double mn = Math.Min(rS, Math.Min(gS, bS));
            saturation[i] = mx <= 1e-6 ? 0.0 : (mx - mn) / mx;
        }

        int minDim = Math.Min(w, h);
        int denoiseRadius = Math.Max(1, minDim / 512);
        int midRadius = Math.Max(2, minDim / 110);
        int macroRadius = Math.Max(4, minDim / 34);

        // Tile-safe multi-scale intrinsic decomposition. The large-scale component
        // absorbs baked/painted illumination so it is not blindly converted into relief.
        var denoise = BoxBlurWrap(lum, w, h, denoiseRadius);
        var mid = BoxBlurWrap(denoise, w, h, midRadius);
        var macro = BoxBlurWrap(mid, w, h, macroRadius);

        var heightRaw = new double[count];
        for (int i = 0; i < count; i++)
        {
            double fine = denoise[i] - mid[i];
            double coarse = mid[i] - macro[i];

            // Highly saturated color changes are more likely pigment/paint than geometry.
            double pigmentGuard = Math.Clamp(1.0 - settings.ChromaSuppression * saturation[i], 0.18, 1.0);
            double detail = settings.FineWeight * fine * 2.15 + settings.CoarseWeight * coarse * 1.70;
            heightRaw[i] = detail * pigmentGuard * settings.HeightContrast;
        }

        var height = RobustNormalizeSigned(heightRaw, 0.06, 0.94);
        var heightForAo = BoxBlurWrap(height, w, h, Math.Max(2, minDim / 70));

        var normal = new byte[count * 4];
        var normalHeight = new byte[count * 4];
        var orm = new byte[count * 4];
        var heightPixels = new byte[count * 4];

        var normalAngles = new double[count];
        var aoValues = new double[count];
        var roughValues = new double[count];
        var metallicValues = new double[count];

        for (int y = 0; y < h; y++)
        {
            int ym = Wrap(y - 1, h), yp = Wrap(y + 1, h);
            for (int x = 0; x < w; x++)
            {
                int xm = Wrap(x - 1, w), xp = Wrap(x + 1, w);
                double H(int xx, int yy) => height[yy * w + xx];

                double gx = (H(xp, ym) + 2 * H(xp, y) + H(xp, yp)
                           - H(xm, ym) - 2 * H(xm, y) - H(xm, yp)) / 8.0;
                double gy = (H(xm, yp) + 2 * H(x, yp) + H(xp, yp)
                           - H(xm, ym) - 2 * H(x, ym) - H(xp, ym)) / 8.0;

                double nx = -gx * settings.NormalStrength;
                double ny =  gy * settings.NormalStrength;
                double nz = 1.0;
                double len = Math.Sqrt(nx * nx + ny * ny + nz * nz);
                nx /= len; ny /= len; nz /= len;

                int i = y * w + x;
                int p = i * 4;
                byte bx = ToByte(nx * 0.5 + 0.5);
                byte by = ToByte(ny * 0.5 + 0.5);
                byte bz = ToByte(nz * 0.5 + 0.5);
                byte bh = ToByte(height[i]);

                // BGRA memory: B=Z, G=Y, R=X.
                normal[p] = bz;
                normal[p + 1] = by;
                normal[p + 2] = bx;
                normal[p + 3] = 255;

                normalHeight[p] = bz;
                normalHeight[p + 1] = by;
                normalHeight[p + 2] = bx;
                normalHeight[p + 3] = bh;

                heightPixels[p] = heightPixels[p + 1] = heightPixels[p + 2] = bh;
                heightPixels[p + 3] = 255;

                // AO is derived from local concavity of the reconstructed surface,
                // not directly from darkness in BaseColor.
                double concavity = Math.Max(0.0, heightForAo[i] - height[i]);
                double ao = Math.Clamp(1.0 - settings.AoStrength * concavity * 3.4, settings.AoFloor, 1.0);

                // Micro-roughness follows high-frequency surface energy. Brightness
                // influence is profile-specific and intentionally small.
                double micro = Math.Clamp(Math.Abs(denoise[i] - mid[i]) * 8.0, 0.0, 1.0);
                double rough = settings.RoughnessBase
                             + settings.MicroRoughness * micro
                             + settings.BrightnessRoughness * (lum[i] - 0.5);
                rough = Math.Clamp(rough, settings.RoughnessMin, settings.RoughnessMax);

                double metallic = Math.Clamp(settings.Metallic, 0.0, 1.0);
                if (settings.MaterialKind == MaterialKind.RustedMetal)
                {
                    // Rust oxide is dielectric. Saturated/rough regions reduce the
                    // effective metallic response while intact darker metal retains it.
                    double oxide = Math.Clamp(saturation[i] * 1.35 + micro * 0.25, 0.0, 1.0);
                    metallic *= 1.0 - oxide * 0.75;
                }

                // BGRA memory for ORM: B=Metallic, G=Roughness, R=AO.
                orm[p] = ToByte(metallic);
                orm[p + 1] = ToByte(rough);
                orm[p + 2] = ToByte(ao);
                orm[p + 3] = 255;

                normalAngles[i] = Math.Acos(Math.Clamp(nz, -1.0, 1.0)) * 180.0 / Math.PI;
                aoValues[i] = ao;
                roughValues[i] = rough;
                metallicValues[i] = metallic;
            }
        }

        var report = Validate(
            height, normalAngles, aoValues, roughValues, metallicValues,
            settings, w, h);

        return new PbrResult(
            ImageService.FromBgra(heightPixels, w, h),
            ImageService.FromBgra(normal, w, h),
            ImageService.FromBgra(normalHeight, w, h),
            ImageService.FromBgra(orm, w, h),
            report);
    }

    private static PbrValidationReport Validate(
        double[] height, double[] angles, double[] ao, double[] rough, double[] metal,
        PbrSettings settings, int w, int h)
    {
        var warnings = new List<string>();
        double meanAngle = angles.Average();
        double p90Angle = Percentile(angles, .90);
        double meanAo = ao.Average();
        double meanRough = rough.Average();
        double meanMetal = metal.Average();
        double h05 = Percentile(height, .05);
        double h95 = Percentile(height, .95);

        if (meanAngle < 3.0) warnings.Add("Normal is very flat.");
        if (p90Angle > 58.0) warnings.Add("Normal has unusually steep slopes.");
        if (h95 - h05 < .18) warnings.Add("Height dynamic range is weak.");
        if (meanRough < .12) warnings.Add("Material is extremely glossy.");
        if (meanRough > .96) warnings.Add("Material is almost fully rough.");
        if (settings.MaterialKind is not (MaterialKind.BareMetal or MaterialKind.RustedMetal) && meanMetal > .08)
            warnings.Add("Dielectric profile has non-zero metallic.");

        double seam = SeamError(height, w, h);
        if (seam > .18) warnings.Add($"Source may not tile seamlessly (height seam {seam:0.00}).");

        return new PbrValidationReport(
            meanAngle, p90Angle,
            meanAo, ao.Min(),
            meanRough, rough.Min(), rough.Max(),
            meanMetal, h05, h95,
            warnings);
    }

    private static double SeamError(double[] a, int w, int h)
    {
        double sum = 0.0;
        int n = 0;
        for (int y = 0; y < h; y++)
        {
            sum += Math.Abs(a[y * w] - a[y * w + (w - 1)]);
            n++;
        }
        for (int x = 0; x < w; x++)
        {
            sum += Math.Abs(a[x] - a[(h - 1) * w + x]);
            n++;
        }
        return n == 0 ? 0 : sum / n;
    }

    private static double[] RobustNormalizeSigned(double[] src, double loOut, double hiOut)
    {
        double lo = Percentile(src, .02);
        double hi = Percentile(src, .98);
        if (hi - lo < 1e-7)
            return Enumerable.Repeat(0.5, src.Length).ToArray();

        var dst = new double[src.Length];
        double scale = (hiOut - loOut) / (hi - lo);
        for (int i = 0; i < src.Length; i++)
            dst[i] = Math.Clamp(loOut + (src[i] - lo) * scale, loOut, hiOut);
        return dst;
    }

    private static double Percentile(double[] values, double p)
    {
        if (values.Length == 0) return 0;
        var copy = (double[])values.Clone();
        Array.Sort(copy);
        double pos = Math.Clamp(p, 0, 1) * (copy.Length - 1);
        int a = (int)Math.Floor(pos), b = (int)Math.Ceiling(pos);
        if (a == b) return copy[a];
        double t = pos - a;
        return copy[a] * (1.0 - t) + copy[b] * t;
    }

    private static double[] BoxBlurWrap(double[] src, int w, int h, int radius)
    {
        radius = Math.Clamp(radius, 1, 48);
        int kernel = radius * 2 + 1;
        var tmp = new double[src.Length];
        var dst = new double[src.Length];

        for (int y = 0; y < h; y++)
        {
            double sum = 0;
            for (int k = -radius; k <= radius; k++) sum += src[y * w + Wrap(k, w)];
            for (int x = 0; x < w; x++)
            {
                tmp[y * w + x] = sum / kernel;
                sum -= src[y * w + Wrap(x - radius, w)];
                sum += src[y * w + Wrap(x + radius + 1, w)];
            }
        }

        for (int x = 0; x < w; x++)
        {
            double sum = 0;
            for (int k = -radius; k <= radius; k++) sum += tmp[Wrap(k, h) * w + x];
            for (int y = 0; y < h; y++)
            {
                dst[y * w + x] = sum / kernel;
                sum -= tmp[Wrap(y - radius, h) * w + x];
                sum += tmp[Wrap(y + radius + 1, h) * w + x];
            }
        }

        return dst;
    }

    private static int Wrap(int v, int size)
    {
        int r = v % size;
        return r < 0 ? r + size : r;
    }

    private static byte ToByte(double v)
        => (byte)Math.Clamp((int)Math.Round(Math.Clamp(v, 0.0, 1.0) * 255.0), 0, 255);

    private static double SrgbToLinear(double c)
        => c <= 0.04045 ? c / 12.92 : Math.Pow((c + 0.055) / 1.055, 2.4);
}
