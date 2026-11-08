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
        var gray601 = new double[count];
        var saturation = new double[count];

        for (int i = 0, p = 0; i < count; i++, p += 4)
        {
            double bS = px[p] / 255.0, gS = px[p + 1] / 255.0, rS = px[p + 2] / 255.0;
            double b = SrgbToLinear(bS), g = SrgbToLinear(gS), r = SrgbToLinear(rS);
            lumLinear[i] = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            lumSrgb[i] = 0.2126 * rS + 0.7152 * gS + 0.0722 * bS;

            // Match the successful first hand-generated material. PIL convert("L")
            // is effectively Rec.601 perceptual luminance, not linear-light luminance.
            gray601[i] = Math.Clamp(0.299 * rS + 0.587 * gS + 0.114 * bS, 0.0, 1.0);

            double mx = Math.Max(rS, Math.Max(gS, bS));
            double mn = Math.Min(rS, Math.Min(gS, bS));
            saturation[i] = mx <= 1e-6 ? 0.0 : (mx - mn) / mx;
        }

        int minDim = Math.Min(w, h);
        double[] fine;
        double[] mid;
        double[] coarse;
        double[] height;
        double[] normalHeightSource;
        double[] aoBlur;

        if (settings.GenerationMode == PbrGenerationMode.ReferenceHandGenerated)
        {
            // Exact design of the first visually successful Escape1 material:
            // absolute smoothed luminance, 74% fine + 26% coarse, no high-pass,
            // no percentile normalization and no artificial groove detector.
            fine = GaussianBlurWrap(gray601, w, h, Math.Max(0.65, minDim / 320.0));
            coarse = GaussianBlurWrap(gray601, w, h, Math.Max(2.2, minDim / 72.0));
            mid = GaussianBlurWrap(gray601, w, h, Math.Max(1.0, minDim / 100.0));
            height = new double[count];
            for (int i = 0; i < count; i++)
            {
                double v = 0.74 * fine[i] + 0.26 * coarse[i];
                height[i] = Math.Clamp(0.5 + (v - 0.5) * settings.HeightContrast, 0.02, 0.98);
            }
            normalHeightSource = height;
            aoBlur = mid;
        }
        else if (settings.GenerationMode == PbrGenerationMode.MacroReliefEnhanced)
        {
            // V2.03 macro mode starts from the successful hand-generated solution and
            // adds ONLY a low-frequency band. There is no local-valley/groove term, so
            // isolated JPEG dark specks cannot become pits or holes.
            fine = GaussianBlurWrap(gray601, w, h, Math.Max(0.82, minDim / 300.0));
            mid = GaussianBlurWrap(gray601, w, h, Math.Max(1.8, minDim / 112.0));
            coarse = GaussianBlurWrap(gray601, w, h, Math.Max(2.8, minDim / 70.0));
            var macro = GaussianBlurWrap(gray601, w, h, Math.Max(5.2, minDim / 34.0));

            height = new double[count];
            double boost = Math.Clamp(settings.MacroReliefBoost, 0.0, 1.0);
            for (int i = 0; i < count; i++)
            {
                double referenceBase = 0.70 * fine[i] + 0.30 * coarse[i];

                // Broad local shape only. Soft limiting prevents large illumination
                // transitions from exploding while keeping stone-block relief readable.
                double macroBand = coarse[i] - macro[i];
                double macroSoft = Math.Tanh(macroBand / 0.11) * 0.11;

                double v = referenceBase + boost * macroSoft;
                height[i] = Math.Clamp(0.5 + (v - 0.5) * settings.HeightContrast, 0.02, 0.98);
            }

            // A final sub-pixel smooth is applied ONLY to the normal source. This keeps
            // the broad height shape while removing pinprick normal dents.
            normalHeightSource = GaussianBlurWrap(height, w, h, 0.58);
            aoBlur = GaussianBlurWrap(gray601, w, h, Math.Max(1.0, minDim / 100.0));
        }
        else
        {
            // Retain the V2.02 structure-preserving mode as a compatibility option.
            int bilateralRadius = Math.Clamp(minDim / 256, 2, 3);
            var edgePreserved = BilateralFilterWrap(lumSrgb, w, h, bilateralRadius, 0.075);
            fine = GaussianBlurWrap(edgePreserved, w, h, Math.Max(0.70, minDim / 320.0));
            mid = GaussianBlurWrap(edgePreserved, w, h, Math.Max(1.8, minDim / 110.0));
            coarse = GaussianBlurWrap(edgePreserved, w, h, Math.Max(2.8, minDim / 72.0));

            double grooveStrength = settings.MaterialKind switch
            {
                MaterialKind.Stone => 0.34,
                MaterialKind.SnowyStone => 0.30,
                MaterialKind.Brick => 0.38,
                MaterialKind.Soil => 0.22,
                MaterialKind.Wood => 0.10,
                _ => 0.08
            };

            height = new double[count];
            for (int i = 0; i < count; i++)
            {
                double structure = settings.FineWeight * fine[i] + settings.CoarseWeight * coarse[i];
                double valley = Math.Max(0.0, mid[i] - fine[i]);
                double pigmentGuard = Math.Clamp(1.0 - settings.ChromaSuppression * saturation[i], 0.30, 1.0);
                double h0 = structure - grooveStrength * valley * pigmentGuard;
                height[i] = Math.Clamp(0.5 + (h0 - 0.5) * settings.HeightContrast, 0.02, 0.98);
            }
            normalHeightSource = height;
            aoBlur = GaussianBlurWrap(height, w, h, Math.Max(1.6, minDim / 100.0));
        }

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
            int ym = settings.GenerationMode == PbrGenerationMode.ReferenceHandGenerated ? Math.Max(0, y - 1) : Wrap(y - 1, h);
            int yp = settings.GenerationMode == PbrGenerationMode.ReferenceHandGenerated ? Math.Min(h - 1, y + 1) : Wrap(y + 1, h);

            for (int x = 0; x < w; x++)
            {
                int xm = settings.GenerationMode == PbrGenerationMode.ReferenceHandGenerated ? Math.Max(0, x - 1) : Wrap(x - 1, w);
                int xp = settings.GenerationMode == PbrGenerationMode.ReferenceHandGenerated ? Math.Min(w - 1, x + 1) : Wrap(x + 1, w);
                double H(int xx, int yy) => normalHeightSource[yy * w + xx];

                double gx = (H(xp, ym) + 2 * H(xp, y) + H(xp, yp)
                           - H(xm, ym) - 2 * H(xm, y) - H(xm, yp)) / 8.0;
                double gy = (H(xm, yp) + 2 * H(x, yp) + H(xp, yp)
                           - H(xm, ym) - 2 * H(x, ym) - H(xp, ym)) / 8.0;

                if (settings.GenerationMode != PbrGenerationMode.ReferenceHandGenerated)
                {
                    const double gradientNoiseFloor = 0.00038;
                    if (Math.Abs(gx) < gradientNoiseFloor) gx = 0.0;
                    if (Math.Abs(gy) < gradientNoiseFloor) gy = 0.0;
                }

                double nx = -gx * settings.NormalStrength;
                double ny = gy * settings.NormalStrength;

                if (settings.GenerationMode != PbrGenerationMode.ReferenceHandGenerated)
                {
                    const double maxNormalAngleDeg = 52.0;
                    double maxSlope = Math.Tan(maxNormalAngleDeg * Math.PI / 180.0);
                    double slope = Math.Sqrt(nx * nx + ny * ny);
                    if (slope > maxSlope)
                    {
                        double k = maxSlope / slope;
                        nx *= k;
                        ny *= k;
                    }
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

                double ao;
                double rough;
                double structureEnergy = Math.Clamp(Math.Abs(fine[i] - coarse[i]) * 5.0, 0.0, 1.0);

                if (settings.GenerationMode is PbrGenerationMode.ReferenceHandGenerated or PbrGenerationMode.MacroReliefEnhanced)
                {
                    // Match the first hand-generated ORM response. This material looked
                    // more convincingly PBR because exposed dark stone could catch light
                    // while bright snowy/mineral areas remained rough.
                    double g = gray601[i];
                    double b = aoBlur[i];
                    double local = Math.Clamp(g - b, -0.30, 0.30);
                    double edge = LaplacianEdge(gray601, w, h, x, y);

                    ao = Math.Clamp(0.72 + 0.25 * g + 0.30 * local, settings.AoFloor, 1.0);
                    rough = Math.Clamp(0.60 + 0.22 * g + 0.10 * edge,
                        settings.RoughnessMin, settings.RoughnessMax);
                }
                else
                {
                    double local = Math.Clamp(fine[i] - aoBlur[i], -0.30, 0.30);
                    ao = Math.Clamp(
                        0.72 + 0.25 * lumSrgb[i] + 0.30 * settings.AoStrength * local,
                        settings.AoFloor, 1.0);

                    rough = settings.RoughnessBase
                          + settings.MicroRoughness * structureEnergy
                          + settings.BrightnessRoughness * lumSrgb[i];
                    rough = Math.Clamp(rough, settings.RoughnessMin, settings.RoughnessMax);
                }

                double metallic = Math.Clamp(settings.Metallic, 0.0, 1.0);
                if (settings.MaterialKind == MaterialKind.RustedMetal)
                {
                    double oxide = Math.Clamp(saturation[i] * 1.35 + structureEnergy * 0.25, 0.0, 1.0);
                    metallic *= 1.0 - oxide * 0.75;
                }

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

    private static double LaplacianEdge(double[] src, int w, int h, int x, int y)
    {
        double c = src[y * w + x];
        double sum = 0.0;
        for (int oy = -1; oy <= 1; oy++)
        {
            int yy = Wrap(y + oy, h);
            for (int ox = -1; ox <= 1; ox++)
            {
                if (ox == 0 && oy == 0) continue;
                int xx = Wrap(x + ox, w);
                sum += src[yy * w + xx];
            }
        }
        return Math.Clamp(Math.Abs(8.0 * c - sum), 0.0, 1.0);
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
