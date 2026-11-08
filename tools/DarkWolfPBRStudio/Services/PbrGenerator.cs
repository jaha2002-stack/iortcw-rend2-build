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
        var lumLinear = new double[count];
        var lumSrgb = new double[count];
        var saturation = new double[count];

        for (int i = 0, p = 0; i < count; i++, p += 4)
        {
            double bS = px[p] / 255.0, gS = px[p + 1] / 255.0, rS = px[p + 2] / 255.0;
            double b = SrgbToLinear(bS), g = SrgbToLinear(gS), r = SrgbToLinear(rS);
            lumLinear[i] = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            // Geometry intentionally follows perceptual/sRGB structure. This is what
            // made the original Escape1 reference preserve broad stone blocks instead
            // of amplifying tiny dark JPEG variations after linearization.
            lumSrgb[i] = 0.2126 * rS + 0.7152 * gS + 0.0722 * bS;

            double mx = Math.Max(rS, Math.Max(gS, bS));
            double mn = Math.Min(rS, Math.Min(gS, bS));
            saturation[i] = mx <= 1e-6 ? 0.0 : (mx - mn) / mx;
        }

        int minDim = Math.Min(w, h);

        // V2.02: edge-preserving denoise + absolute multi-scale structure.
        // Do not high-pass and percentile-normalize the texture: that was the V2.01
        // failure mode which converted JPEG/color micro-variation into embossed noise.
        int bilateralRadius = Math.Clamp(minDim / 256, 2, 3);
        var edgePreserved = BilateralFilterWrap(lumSrgb, w, h, bilateralRadius, 0.075);
        var fine = GaussianBlurWrap(edgePreserved, w, h, Math.Max(0.70, minDim / 320.0));
        var mid = GaussianBlurWrap(edgePreserved, w, h, Math.Max(1.8, minDim / 110.0));
        var coarse = GaussianBlurWrap(edgePreserved, w, h, Math.Max(2.8, minDim / 72.0));

        double grooveStrength = settings.MaterialKind switch
        {
            MaterialKind.Stone => 0.34,
            MaterialKind.SnowyStone => 0.30,
            MaterialKind.Brick => 0.38,
            MaterialKind.Soil => 0.22,
            MaterialKind.Wood => 0.10,
            _ => 0.08
        };

        var height = new double[count];
        double heightContrast = Math.Clamp(settings.HeightContrast, 0.30, 1.60);
        for (int i = 0; i < count; i++)
        {
            // Same successful principle as the first hand-generated material:
            // broad absolute luminance carries the stone shape. FineWeight/CoarseWeight
            // now blend denoised structural scales, not high-pass residuals.
            double structure = settings.FineWeight * fine[i] + settings.CoarseWeight * coarse[i];

            // Dark local valleys relative to their neighborhood are likely mortar/cracks.
            // Deepen them gently, while chroma suppresses colored paint/stains.
            double valley = Math.Max(0.0, mid[i] - fine[i]);
            double pigmentGuard = Math.Clamp(1.0 - settings.ChromaSuppression * saturation[i], 0.30, 1.0);
            double h0 = structure - grooveStrength * valley * pigmentGuard;

            height[i] = Math.Clamp(0.5 + (h0 - 0.5) * heightContrast, 0.02, 0.98);
        }
        var heightForAo = GaussianBlurWrap(height, w, h, Math.Max(1.6, minDim / 100.0));

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

                // Ignore sub-pixel gradient chatter left by JPEG ringing. Large stone
                // boundaries and mortar survive because they remain well above this floor.
                const double gradientNoiseFloor = 0.00055;
                if (Math.Abs(gx) < gradientNoiseFloor) gx = 0.0;
                if (Math.Abs(gy) < gradientNoiseFloor) gy = 0.0;

                double nx = -gx * settings.NormalStrength;
                double ny =  gy * settings.NormalStrength;

                // The successful hand reference had P95 around 45 degrees. A 50-degree
                // cap preserves readable relief without the V2.01 near-horizontal spikes.
                const double maxNormalAngleDeg = 50.0;
                double maxSlope = Math.Tan(maxNormalAngleDeg * Math.PI / 180.0);
                double slope = Math.Sqrt(nx * nx + ny * ny);
                if (slope > maxSlope)
                {
                    double k = maxSlope / slope;
                    nx *= k;
                    ny *= k;
                }

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

                // AO V2.02 intentionally follows the successful first material:
                // broad local valleys darken, but flat dark albedo is not forced to zero.
                double local = Math.Clamp(fine[i] - heightForAo[i], -0.30, 0.30);
                double ao = Math.Clamp(
                    0.72 + 0.25 * lumSrgb[i] + 0.30 * settings.AoStrength * local,
                    settings.AoFloor, 1.0);

                // Roughness follows material brightness plus structural edge energy,
                // not high-frequency noise. Exposed darker stone can catch a readable
                // grazing response while snow/bright mineral remains rougher.
                double structureEnergy = Math.Clamp(Math.Abs(fine[i] - coarse[i]) * 5.0, 0.0, 1.0);
                double rough = settings.RoughnessBase
                             + settings.MicroRoughness * structureEnergy
                             + settings.BrightnessRoughness * lumSrgb[i];
                rough = Math.Clamp(rough, settings.RoughnessMin, settings.RoughnessMax);

                double metallic = Math.Clamp(settings.Metallic, 0.0, 1.0);
                if (settings.MaterialKind == MaterialKind.RustedMetal)
                {
                    // Rust oxide is dielectric. Saturated/rough regions reduce the
                    // effective metallic response while intact darker metal retains it.
                    double oxide = Math.Clamp(saturation[i] * 1.35 + structureEnergy * 0.25, 0.0, 1.0);
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

    private static double[] GaussianBlurWrap(double[] src, int w, int h, double sigma)
    {
        sigma = Math.Clamp(sigma, 0.55, 18.0);
        int radius = Math.Clamp((int)Math.Ceiling(sigma * 2.5), 1, 48);
        var kernel = new double[radius * 2 + 1];
        double sumK = 0.0;
        for (int i = -radius; i <= radius; i++)
        {
            double v = Math.Exp(-(i * i) / (2.0 * sigma * sigma));
            kernel[i + radius] = v;
            sumK += v;
        }
        for (int i = 0; i < kernel.Length; i++) kernel[i] /= sumK;

        var tmp = new double[src.Length];
        var dst = new double[src.Length];
        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                double s = 0.0;
                for (int k = -radius; k <= radius; k++)
                    s += src[y * w + Wrap(x + k, w)] * kernel[k + radius];
                tmp[y * w + x] = s;
            }
        }
        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                double s = 0.0;
                for (int k = -radius; k <= radius; k++)
                    s += tmp[Wrap(y + k, h) * w + x] * kernel[k + radius];
                dst[y * w + x] = s;
            }
        }
        return dst;
    }

    private static double[] BilateralFilterWrap(double[] src, int w, int h, int radius, double sigmaRange)
    {
        radius = Math.Clamp(radius, 1, 4);
        sigmaRange = Math.Clamp(sigmaRange, 0.02, 0.25);
        double sigmaSpatial = Math.Max(0.8, radius * 0.85);
        var dst = new double[src.Length];

        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                double center = src[y * w + x];
                double weighted = 0.0, weightSum = 0.0;
                for (int oy = -radius; oy <= radius; oy++)
                {
                    int yy = Wrap(y + oy, h);
                    for (int ox = -radius; ox <= radius; ox++)
                    {
                        int xx = Wrap(x + ox, w);
                        double v = src[yy * w + xx];
                        double spatial = Math.Exp(-(ox * ox + oy * oy) / (2.0 * sigmaSpatial * sigmaSpatial));
                        double d = v - center;
                        double range = Math.Exp(-(d * d) / (2.0 * sigmaRange * sigmaRange));
                        double wt = spatial * range;
                        weighted += v * wt;
                        weightSum += wt;
                    }
                }
                dst[y * w + x] = weightSum > 1e-12 ? weighted / weightSum : center;
            }
        }
        return dst;
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
