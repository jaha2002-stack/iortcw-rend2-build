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
        byte[]? physicalHeightByte = null;
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
        else if (settings.GenerationMode == PbrGenerationMode.PhysicalReliefPOM)
        {
            // Start from the validated V2.03 hand-reference material, but build a
            // dedicated displacement field for POM. Normal/ORM stay on the proven
            // macro-relief path; only Height alpha receives the wider, low-frequency
            // physical range. This avoids turning small dark JPEG specks into craters.
            BuildReferenceFields(gray601Byte, w, h, minDim,
                out fine, out mid, out coarse, out height,
                out referenceHeightByte, out referenceAoByte, out referenceRoughByte);

            physicalHeightByte = BuildPhysicalReliefHeight(
                referenceHeightByte, w, h, minDim, settings.MaterialKind,
                Math.Clamp(settings.PhysicalReliefStrength * settings.HeightContrast, 0.35, 1.60));

            height = new double[count];
            for (int i = 0; i < count; i++)
                height[i] = physicalHeightByte[i] / 255.0;

            // Preserve the accepted V2.03 macro normal instead of deriving a noisy
            // normal map from the more aggressive POM displacement field.
            normalHeightSource = new double[count];
            for (int i = 0; i < count; i++)
                normalHeightSource[i] = referenceHeightByte[i] / 255.0;

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

        bool handGeometry = settings.GenerationMode is PbrGenerationMode.ReferenceHandGenerated
            or PbrGenerationMode.MacroReliefEnhanced
            or PbrGenerationMode.PhysicalReliefPOM;
        for (int y = 0; y < h; y++)
        {
            int ym = handGeometry ? Math.Max(0, y - 1) : Wrap(y - 1, h);
            int yp = handGeometry ? Math.Min(h - 1, y + 1) : Wrap(y + 1, h);

            for (int x = 0; x < w; x++)
            {
                int xm = handGeometry ? Math.Max(0, x - 1) : Wrap(x - 1, w);
                int xp = handGeometry ? Math.Min(w - 1, x + 1) : Wrap(x + 1, w);

                double gx, gy;
                if (referenceHeightByte is not null)
                {
                    // Preserve the Python reference's integer Sobel numerator before
                    // division. Doing the weighted sums in normalized doubles leaves
                    // tiny negative cancellation errors that encode flat 0 as 127
                    // instead of the reference value 128.
                    int G(int xx, int yy) => referenceHeightByte[yy * w + xx];
                    int gxNum = G(xp, ym) + 2 * G(xp, y) + G(xp, yp)
                              - G(xm, ym) - 2 * G(xm, y) - G(xm, yp);
                    int gyNum = G(xm, yp) + 2 * G(x, yp) + G(xp, yp)
                              - G(xm, ym) - 2 * G(x, ym) - G(xp, ym);
                    gx = gxNum / (8.0 * 255.0);
                    gy = gyNum / (8.0 * 255.0);
                }
                else
                {
                    double H(int xx, int yy) => normalHeightSource[yy * w + xx];
                    gx = (H(xp, ym) + 2 * H(xp, y) + H(xp, yp)
                        - H(xm, ym) - 2 * H(xm, y) - H(xm, yp)) / 8.0;
                    gy = (H(xm, yp) + 2 * H(x, yp) + H(xp, yp)
                        - H(xm, ym) - 2 * H(x, ym) - H(xp, ym)) / 8.0;
                }

                if (settings.GenerationMode is PbrGenerationMode.MacroReliefEnhanced or PbrGenerationMode.PhysicalReliefPOM)
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
                byte bh = physicalHeightByte is not null
                    ? physicalHeightByte[i]
                    : (referenceHeightByte is null ? ToByte(height[i]) : referenceHeightByte[i]);

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

                if (settings.GenerationMode is PbrGenerationMode.ReferenceHandGenerated
                    or PbrGenerationMode.MacroReliefEnhanced
                    or PbrGenerationMode.PhysicalReliefPOM)
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

                // V2.06 authored surface finish: keep dielectric/metal classification intact,
                // but shape roughness/AO so PBR V3.2 GGX has physically meaningful wet/snow/moss response.
                // These masks are deliberately broad and restrained; they do not alter Height/POM geometry.
                double hPhys = height[i];
                double darkMask = SmoothStep(0.72, 0.30, lumSrgb[i]);
                double brightMask = SmoothStep(0.58, 0.88, lumSrgb[i]);
                double recessMask = SmoothStep(0.58, 0.28, hPhys);

                switch (settings.SurfaceFinish)
                {
                    case SurfaceFinish.Wet:
                    {
                        double wetMask = Math.Clamp(0.62 * darkMask + 0.38 * recessMask, 0.0, 1.0);
                        rough = Math.Clamp(rough * (1.0 - 0.68 * wetMask), 0.10, 0.96);
                        ao = Math.Clamp(ao - 0.08 * recessMask, settings.AoFloor * 0.88, 1.0);
                        break;
                    }
                    case SurfaceFinish.Snowy:
                    {
                        double snowMask = Math.Clamp(0.72 * brightMask + 0.28 * SmoothStep(0.52, 0.76, hPhys), 0.0, 1.0);
                        rough = Math.Clamp(rough + (0.88 - rough) * 0.82 * snowMask, 0.28, 0.98);
                        ao = Math.Clamp(ao + 0.05 * snowMask, settings.AoFloor, 1.0);
                        break;
                    }
                    case SurfaceFinish.WetSnow:
                    {
                        double snowMask = Math.Clamp(0.68 * brightMask + 0.32 * SmoothStep(0.54, 0.78, hPhys), 0.0, 1.0);
                        double wetMask = Math.Clamp((1.0 - snowMask) * (0.58 * darkMask + 0.42 * recessMask), 0.0, 1.0);
                        double wetRough = Math.Clamp(rough * (1.0 - 0.70 * wetMask), 0.09, 0.96);
                        rough = Math.Clamp(wetRough + (0.90 - wetRough) * 0.86 * snowMask, 0.09, 0.98);
                        ao = Math.Clamp(ao - 0.06 * wetMask + 0.04 * snowMask, settings.AoFloor * 0.88, 1.0);
                        break;
                    }
                    case SurfaceFinish.Mossy:
                    {
                        double mossMask = Math.Clamp(0.50 * recessMask + 0.30 * darkMask + 0.20 * saturation[i], 0.0, 1.0);
                        rough = Math.Clamp(rough + (0.92 - rough) * 0.60 * mossMask, 0.38, 0.98);
                        ao = Math.Clamp(ao - 0.10 * mossMask, settings.AoFloor * 0.84, 1.0);
                        break;
                    }
                }

                double metallic = Math.Clamp(settings.Metallic, 0.0, 1.0);
                if (settings.MaterialKind == MaterialKind.RustedMetal)
                {
                    double oxide = Math.Clamp(saturation[i] * 1.35 + structureEnergy * 0.25, 0.0, 1.0);
                    metallic *= 1.0 - oxide * 0.75;
                }

                orm[p] = ToByte(metallic);
                bool preserveReferenceOrm = settings.SurfaceFinish == SurfaceFinish.Dry;
                orm[p + 1] = preserveReferenceOrm && referenceRoughByte is not null
                    ? referenceRoughByte[i] : ToByte(rough);
                orm[p + 2] = preserveReferenceOrm && referenceAoByte is not null
                    ? referenceAoByte[i] : ToByte(ao);
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

    private static byte[] BuildPhysicalReliefHeight(
        byte[] referenceHeight, int w, int h, int minDim,
        MaterialKind materialKind, double strength)
    {
        if (materialKind is MaterialKind.Stone or MaterialKind.SnowyStone or MaterialKind.Brick)
            return BuildStonePhysicalReliefHeight(referenceHeight, w, h, minDim, materialKind, strength);

        return BuildGenericPhysicalReliefHeight(referenceHeight, w, h, minDim, strength);
    }

    private static byte[] BuildStonePhysicalReliefHeight(
        byte[] referenceHeight, int w, int h, int minDim,
        MaterialKind materialKind, double strength)
    {
        int count = w * h;
        var src = new double[count];
        for (int i = 0; i < count; i++)
            src[i] = referenceHeight[i] / 255.0;

        // V2.05.2 Stone Height Reconstruction:
        // 1) suppress micro-grooves before any displacement classification;
        // 2) detect only coherent dark seams/mortar as recesses;
        // 3) keep stone faces on broad plateaus with only very low-frequency shape.
        //
        // Fine surface grain remains exclusively in the Normal map.
        double faceSigma = Math.Clamp(minDim / 150.0, 1.60, 4.50);
        double neighborhoodSigma = Math.Clamp(minDim / 42.0, 3.50, 13.0);
        double lightingSigma = Math.Clamp(minDim / 16.0, 7.0, 18.0);

        var face = GaussianBlurWrap(src, w, h, faceSigma);
        var neighborhood = GaussianBlurWrap(face, w, h, neighborhoodSigma);
        var lighting = GaussianBlurWrap(face, w, h, lightingSigma);

        // A dark narrow line relative to its local neighborhood is a seam candidate.
        // Using a local maximum reference is intentionally asymmetric: bright stone
        // scratches do not become raised displacement ridges.
        int ridgeRadius = Math.Clamp((int)Math.Round(minDim / 80.0), 2, 8);
        var localMax = LocalMaxFilterWrap(face, w, h, ridgeRadius);
        var groove = new double[count];
        for (int i = 0; i < count; i++)
            groove[i] = Math.Max(0.0, localMax[i] - face[i]);

        double g50 = Percentile(groove, 0.50);
        double g88 = Percentile(groove, 0.88);
        double g97 = Percentile(groove, 0.97);
        double seamLow = Math.Max(0.012, g50 + 0.22 * Math.Max(g88 - g50, 0.0));
        double seamHigh = Math.Max(seamLow + 0.014, g97);

        var seamMask = new double[count];
        for (int i = 0; i < count; i++)
        {
            double t = SmoothStep(seamLow, seamHigh, groove[i]);
            seamMask[i] = t;
        }

        // Broad dark stains can look like geometry if we only threshold darkness.
        // Suppress regions whose seam response fills a large neighborhood; true mortar
        // and cracks remain thin/linear and survive this occupancy guard.
        var seamOccupancy = GaussianBlurWrap(
            seamMask, w, h, Math.Clamp(minDim / 95.0, 1.5, 5.0));
        for (int i = 0; i < count; i++)
        {
            double broadPatch = SmoothStep(0.52, 0.82, seamOccupancy[i]);
            seamMask[i] *= 1.0 - 0.82 * broadPatch;
        }

        // Bevel the seam edge for stable POM traversal instead of a binary trench.
        seamMask = GaussianBlurWrap(seamMask, w, h, 0.85);

        // Stone faces get only low-frequency block-to-block variation. This term is
        // deliberately small so illumination painted into the diffuse cannot create
        // the wavy/embossed failure seen in V2.05.1.
        var macroResidual = new double[count];
        for (int i = 0; i < count; i++)
            macroResidual[i] = neighborhood[i] - lighting[i];

        double mr10 = Percentile(macroResidual, 0.10);
        double mr90 = Percentile(macroResidual, 0.90);
        double mrCenter = 0.5 * (mr10 + mr90);
        double mrSpan = Math.Max(mr90 - mr10, 0.035);

        double seamDepth = materialKind switch
        {
            MaterialKind.Brick => 0.33,
            MaterialKind.SnowyStone => 0.29,
            _ => 0.30
        };
        double faceVariation = materialKind == MaterialKind.Brick ? 0.050 : 0.042;
        double plateau = materialKind == MaterialKind.SnowyStone ? 0.64 : 0.62;

        var outHeight = new byte[count];
        for (int i = 0; i < count; i++)
        {
            double macroShape = Math.Clamp((macroResidual[i] - mrCenter) / mrSpan, -1.0, 1.0);
            double v = plateau
                     + strength * faceVariation * macroShape
                     - strength * seamDepth * Math.Clamp(seamMask[i], 0.0, 1.0);

            // Keep a generous safe range for POM refinement and bilinear filtering.
            v = Math.Clamp(v, 0.12, 0.86);
            outHeight[i] = ToByte(v);
        }

        // Tiny final smoothing removes isolated one-pixel ledges but does not restore
        // the suppressed surface-frequency grain.
        return PillowGaussianBlur(outHeight, w, h, 0.55);
    }

    private static byte[] BuildGenericPhysicalReliefHeight(
        byte[] referenceHeight, int w, int h, int minDim, double strength)
    {
        // V2.05.1 generic PhysicalRelief path retained unchanged for non-masonry
        // materials to avoid cross-material regressions.
        double detailSigma = Math.Clamp(minDim / 900.0, 1.15, 2.40);
        double macroSigma = Math.Clamp(minDim / 180.0, 4.0, 12.0);

        byte[] surface = PillowGaussianBlur(referenceHeight, w, h, detailSigma);
        byte[] macro = PillowGaussianBlur(referenceHeight, w, h, macroSigma);

        int count = w * h;
        var local = new double[count];
        for (int i = 0; i < count; i++)
            local[i] = (surface[i] - macro[i]) / 255.0;

        double p10 = Percentile(local, 0.10);
        double p90 = Percentile(local, 0.90);
        double span = Math.Max(p90 - p10, 0.018);
        double center = 0.5 * (p10 + p90);

        double macroMedian = Percentile(macro.Select(v => v / 255.0).ToArray(), 0.50);
        var outHeight = new byte[count];

        for (int i = 0; i < count; i++)
        {
            double structural = (local[i] - center) / span;
            structural *= structural < 0.0 ? 0.38 : 0.30;

            double macroShape = Math.Clamp((macro[i] / 255.0 - macroMedian) * 0.22, -0.07, 0.07);
            double v = 0.50 + strength * (structural + macroShape);
            v = Math.Clamp(v, 0.08, 0.92);
            outHeight[i] = ToByte(v);
        }

        return PillowGaussianBlur(outHeight, w, h, 0.65);
    }

    private static double[] LocalMaxFilterWrap(double[] src, int w, int h, int radius)
    {
        radius = Math.Clamp(radius, 1, 12);
        var tmp = new double[src.Length];
        var dst = new double[src.Length];

        for (int y = 0; y < h; y++)
        {
            int row = y * w;
            for (int x = 0; x < w; x++)
            {
                double m = double.NegativeInfinity;
                for (int k = -radius; k <= radius; k++)
                    m = Math.Max(m, src[row + Wrap(x + k, w)]);
                tmp[row + x] = m;
            }
        }

        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                double m = double.NegativeInfinity;
                for (int k = -radius; k <= radius; k++)
                    m = Math.Max(m, tmp[Wrap(y + k, h) * w + x]);
                dst[y * w + x] = m;
            }
        }

        return dst;
    }

    private static double SmoothStep(double edge0, double edge1, double x)
    {
        if (edge1 <= edge0)
            return x >= edge1 ? 1.0 : 0.0;
        double t = Math.Clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
        return t * t * (3.0 - 2.0 * t);
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
        double minUsefulHeightRange =
            settings.GenerationMode == PbrGenerationMode.PhysicalReliefPOM &&
            settings.MaterialKind is MaterialKind.Stone or MaterialKind.SnowyStone or MaterialKind.Brick
                ? 0.12
                : 0.18;
        if (h95 - h05 < minUsefulHeightRange)
            warnings.Add("Height dynamic range is weak.");
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
