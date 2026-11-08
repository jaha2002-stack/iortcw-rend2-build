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
        var gray601Byte = new byte[count];
        var saturation = new double[count];

        for (int i = 0, p = 0; i < count; i++, p += 4)
        {
            double bS = px[p] / 255.0, gS = px[p + 1] / 255.0, rS = px[p + 2] / 255.0;
            double b = SrgbToLinear(bS), g = SrgbToLinear(gS), r = SrgbToLinear(rS);
            lumLinear[i] = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            lumSrgb[i] = 0.2126 * rS + 0.7152 * gS + 0.0722 * bS;

            // Byte-exact Pillow RGB -> L conversion used by the first hand generator.
            int r8 = px[p + 2], g8 = px[p + 1], b8 = px[p];
            byte l8 = (byte)Math.Clamp((r8 * 19595 + g8 * 38470 + b8 * 7471 + 32768) >> 16, 0, 255);
            gray601Byte[i] = l8;
            gray601[i] = l8 / 255.0;

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
        double[] macroNormalSource;
        double[] aoBlur;
        byte[]? referenceHeightByte = null;
        byte[]? referenceAoByte = null;
        byte[]? referenceRoughByte = null;

        if (settings.GenerationMode == PbrGenerationMode.ReferenceHandGenerated)
        {
            BuildReferenceFields(gray601Byte, w, h, minDim,
                out fine, out mid, out coarse, out height,
                out referenceHeightByte, out referenceAoByte, out referenceRoughByte);
            normalHeightSource = height;
            macroNormalSource = height;
            aoBlur = mid;
        }
        else if (settings.GenerationMode == PbrGenerationMode.MacroReliefEnhanced)
        {
            // Height and ORM are byte-identical to the successful hand-generated mode.
            // Macro enhancement is allowed to affect normals only.
            BuildReferenceFields(gray601Byte, w, h, minDim,
                out fine, out mid, out coarse, out height,
                out referenceHeightByte, out referenceAoByte, out referenceRoughByte);
            normalHeightSource = height;
            byte[] macro8 = PillowGaussianBlur(referenceHeightByte, w, h, 2.8);
            macroNormalSource = new double[count];
            for (int i = 0; i < count; i++) macroNormalSource[i] = macro8[i] / 255.0;
            aoBlur = mid;
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
            macroNormalSource = height;
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

                if (settings.GenerationMode == PbrGenerationMode.MacroReliefEnhanced)
                {
                    double C(int xx, int yy) => macroNormalSource[yy * w + xx];
                    double cgx = (C(xp, ym) + 2 * C(xp, y) + C(xp, yp)
                                - C(xm, ym) - 2 * C(xm, y) - C(xm, yp)) / 8.0;
                    double cgy = (C(xm, yp) + 2 * C(x, yp) + C(xp, yp)
                                - C(xm, ym) - 2 * C(x, ym) - C(xp, ym)) / 8.0;

                    double bmag = Math.Sqrt(gx * gx + gy * gy);
                    double cmag = Math.Sqrt(cgx * cgx + cgy * cgy);
                    double align = bmag > 1e-8 && cmag > 1e-8
                        ? Math.Max(0.0, (gx * cgx + gy * cgy) / (bmag * cmag))
                        : 0.0;

                    // Broad gradients around 0.006..0.026 on the 512px reference
                    // correspond to stone-block boundaries; smoothstep avoids halos.
                    double t = Math.Clamp((cmag - 0.006) / 0.020, 0.0, 1.0);
                    t = t * t * (3.0 - 2.0 * t);
                    double structural = align * t;
                    double gain = 1.0 + Math.Clamp(settings.MacroReliefBoost, 0.0, 1.25) * structural;
                    gx *= gain;
                    gy *= gain;
                }

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
                byte bh = referenceHeightByte is null ? ToByte(height[i]) : referenceHeightByte[i];

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
                    ao = referenceAoByte![i] / 255.0;
                    rough = referenceRoughByte![i] / 255.0;
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
                orm[p + 1] = referenceRoughByte is null ? ToByte(rough) : referenceRoughByte[i];
                orm[p + 2] = referenceAoByte is null ? ToByte(ao) : referenceAoByte[i];
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

    private static void BuildReferenceFields(
        byte[] gray, int w, int h, int minDim,
        out double[] fine, out double[] mid, out double[] coarse, out double[] height,
        out byte[] heightByte, out byte[] aoByte, out byte[] roughByte)
    {
        byte[] fine8 = PillowGaussianBlur(gray, w, h, Math.Max(0.65, minDim / 320.0));
        byte[] coarse8 = PillowGaussianBlur(gray, w, h, Math.Max(2.2, minDim / 72.0));
        byte[] mid8 = PillowGaussianBlur(gray, w, h, Math.Max(1.0, minDim / 100.0));
        byte[] edge8 = PillowFindEdges(gray, w, h);

        int count = w * h;
        fine = new double[count];
        mid = new double[count];
        coarse = new double[count];
        height = new double[count];
        heightByte = new byte[count];
        aoByte = new byte[count];
        roughByte = new byte[count];

        for (int i = 0; i < count; i++)
        {
            fine[i] = fine8[i] / 255.0;
            mid[i] = mid8[i] / 255.0;
            coarse[i] = coarse8[i] / 255.0;

            // Pillow Image.blend(fine, coarse, 0.26): positive 8-bit result truncates.
            byte hb = (byte)Math.Clamp((int)Math.Floor(fine8[i] * 0.74 + coarse8[i] * 0.26), 0, 255);
            heightByte[i] = hb;
            height[i] = hb / 255.0;

            double g = gray[i] / 255.0;
            double b = mid8[i] / 255.0;
            double e = edge8[i] / 255.0;
            double local = Math.Clamp(g - b, -0.30, 0.30);
            double ao = Math.Clamp(0.72 + 0.25 * g + 0.30 * local, 0.46, 1.0);
            double rough = Math.Clamp(0.60 + 0.22 * g + 0.10 * e, 0.46, 0.92);
            aoByte[i] = ToByte(ao);
            roughByte[i] = ToByte(rough);
        }
    }

    private static byte[] PillowGaussianBlur(byte[] src, int w, int h, double requestedSigma)
    {
        const int passes = 3;
        float sigma = (float)requestedSigma;
        float sigma2 = sigma * sigma / passes;
        float L = MathF.Sqrt(12.0f * sigma2 + 1.0f);
        float l = MathF.Floor((L - 1.0f) / 2.0f);
        float a = (2.0f * l + 1.0f) * (l * (l + 1.0f) - 3.0f * sigma2);
        a /= 6.0f * (sigma2 - (l + 1.0f) * (l + 1.0f));
        float radius = l + a;

        byte[] cur = (byte[])src.Clone();
        for (int p = 0; p < passes; p++) cur = PillowBoxBlurHorizontal(cur, w, h, radius);
        for (int p = 0; p < passes; p++) cur = PillowBoxBlurVertical(cur, w, h, radius);
        return cur;
    }

    private static byte[] PillowBoxBlurHorizontal(byte[] src, int w, int h, float floatRadius)
    {
        int radius = (int)floatRadius;
        uint ww = (uint)((1u << 24) / (floatRadius * 2.0f + 1.0f));
        uint fw = ((1u << 24) - (uint)(radius * 2 + 1) * ww) / 2u;
        var dst = new byte[src.Length];

        for (int y = 0; y < h; y++)
        {
            int row = y * w;
            for (int x = 0; x < w; x++)
            {
                uint acc = 0;
                for (int k = -radius; k <= radius; k++)
                    acc += src[row + Math.Clamp(x + k, 0, w - 1)];

                int left = Math.Clamp(x - radius - 1, 0, w - 1);
                int right = Math.Clamp(x + radius + 1, 0, w - 1);
                ulong bulk = (ulong)acc * ww + (ulong)(src[row + left] + src[row + right]) * fw;
                dst[row + x] = (byte)((bulk + (1u << 23)) >> 24);
            }
        }
        return dst;
    }

    private static byte[] PillowBoxBlurVertical(byte[] src, int w, int h, float floatRadius)
    {
        int radius = (int)floatRadius;
        uint ww = (uint)((1u << 24) / (floatRadius * 2.0f + 1.0f));
        uint fw = ((1u << 24) - (uint)(radius * 2 + 1) * ww) / 2u;
        var dst = new byte[src.Length];

        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                uint acc = 0;
                for (int k = -radius; k <= radius; k++)
                    acc += src[Math.Clamp(y + k, 0, h - 1) * w + x];

                int top = Math.Clamp(y - radius - 1, 0, h - 1);
                int bottom = Math.Clamp(y + radius + 1, 0, h - 1);
                ulong bulk = (ulong)acc * ww + (ulong)(src[top * w + x] + src[bottom * w + x]) * fw;
                dst[y * w + x] = (byte)((bulk + (1u << 23)) >> 24);
            }
        }
        return dst;
    }

    private static byte[] PillowFindEdges(byte[] src, int w, int h)
    {
        var dst = (byte[])src.Clone();
        for (int y = 1; y < h - 1; y++)
        {
            for (int x = 1; x < w - 1; x++)
            {
                int i = y * w + x;
                int sum =
                    src[(y - 1) * w + x - 1] + src[(y - 1) * w + x] + src[(y - 1) * w + x + 1] +
                    src[y * w + x - 1] + src[y * w + x + 1] +
                    src[(y + 1) * w + x - 1] + src[(y + 1) * w + x] + src[(y + 1) * w + x + 1];
                dst[i] = (byte)Math.Clamp(8 * src[i] - sum, 0, 255);
            }
        }
        return dst;
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
        // Pillow FIND_EDGES uses a signed 8-neighbor Laplacian and clips negative
        // values to zero; it is not absolute-value edge magnitude.
        return Math.Clamp(8.0 * c - sum, 0.0, 1.0);
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

    private static double[] GaussianBlurClamp(double[] src, int w, int h, double sigma)
    {
        sigma = Math.Clamp(sigma, 0.55, 18.0);
        int radius = Math.Clamp((int)Math.Ceiling(sigma * 3.0), 1, 54);
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
                {
                    int xx = Math.Clamp(x + k, 0, w - 1);
                    s += src[y * w + xx] * kernel[k + radius];
                }
                tmp[y * w + x] = s;
            }
        }
        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                double s = 0.0;
                for (int k = -radius; k <= radius; k++)
                {
                    int yy = Math.Clamp(y + k, 0, h - 1);
                    s += tmp[yy * w + x] * kernel[k + radius];
                }
                dst[y * w + x] = s;
            }
        }
        return dst;
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
