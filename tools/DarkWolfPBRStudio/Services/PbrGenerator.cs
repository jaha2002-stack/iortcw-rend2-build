using DarkWolfPBRStudio.Models;
using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio.Services;

public sealed record PbrResult(BitmapSource Normal, BitmapSource Orm);

public static class PbrGenerator
{
    public static PbrResult Generate(BitmapSource input, PbrSettings settings)
    {
        var px = ImageService.ToBgra(input, out int w, out int h);
        var lum = new double[w * h];

        for (int i = 0, p = 0; i < lum.Length; i++, p += 4)
        {
            double b = px[p] / 255.0, g = px[p + 1] / 255.0, r = px[p + 2] / 255.0;
            lum[i] = 0.2126 * r + 0.7152 * g + 0.0722 * b;
        }

        var fine = BoxBlur(lum, w, h, Math.Max(1, Math.Min(w, h) / 320));
        var coarse = BoxBlur(lum, w, h, Math.Max(2, Math.Min(w, h) / 72));
        var height = new double[lum.Length];
        for (int i = 0; i < height.Length; i++) height[i] = fine[i] * 0.74 + coarse[i] * 0.26;

        var normal = new byte[w * h * 4];
        var orm = new byte[w * h * 4];
        var blur = BoxBlur(lum, w, h, Math.Max(1, Math.Min(w, h) / 100));

        for (int y = 0; y < h; y++)
        {
            int ym = Math.Max(0, y - 1), yp = Math.Min(h - 1, y + 1);
            for (int x = 0; x < w; x++)
            {
                int xm = Math.Max(0, x - 1), xp = Math.Min(w - 1, x + 1);
                double H(int xx, int yy) => height[yy * w + xx];

                double gx = (H(xp, ym) + 2 * H(xp, y) + H(xp, yp) - H(xm, ym) - 2 * H(xm, y) - H(xm, yp)) / 8.0;
                double gy = (H(xm, yp) + 2 * H(x, yp) + H(xp, yp) - H(xm, ym) - 2 * H(x, ym) - H(xp, ym)) / 8.0;

                double nx = -gx * settings.NormalStrength;
                double ny = gy * settings.NormalStrength;
                double nz = 1.0;
                double len = Math.Sqrt(nx * nx + ny * ny + nz * nz);
                nx /= len; ny /= len; nz /= len;

                int p = (y * w + x) * 4;
                normal[p] = ToByte(nz * 0.5 + 0.5);      // B = Z
                normal[p + 1] = ToByte(ny * 0.5 + 0.5);  // G = Y
                normal[p + 2] = ToByte(nx * 0.5 + 0.5);  // R = X
                normal[p + 3] = 255;

                double g0 = lum[y * w + x];
                double b0 = blur[y * w + x];
                double local = Math.Clamp(g0 - b0, -0.30, 0.30);
                double edge = Math.Clamp(Math.Sqrt(gx * gx + gy * gy) * 7.0, 0.0, 1.0);

                double ao = Math.Clamp(0.72 + 0.25 * g0 + 0.30 * local, settings.AoFloor, 1.0);
                double rough = Math.Clamp(settings.RoughnessBase + 0.22 * g0 + 0.10 * edge, settings.RoughnessMin, settings.RoughnessMax);

                orm[p] = 0;             // B = Metallic
                orm[p + 1] = ToByte(rough); // G = Roughness
                orm[p + 2] = ToByte(ao);    // R = AO
                orm[p + 3] = 255;
            }
        }

        return new PbrResult(ImageService.FromBgra(normal, w, h), ImageService.FromBgra(orm, w, h));
    }

    private static byte ToByte(double v) => (byte)Math.Clamp((int)Math.Round(v * 255.0), 0, 255);

    private static double[] BoxBlur(double[] src, int w, int h, int radius)
    {
        radius = Math.Clamp(radius, 1, 32);
        var tmp = new double[src.Length];
        var dst = new double[src.Length];

        for (int y = 0; y < h; y++)
        {
            double sum = 0;
            int count = 0;
            for (int x = -radius; x <= radius; x++)
            {
                int xx = Math.Clamp(x, 0, w - 1);
                sum += src[y * w + xx]; count++;
            }
            for (int x = 0; x < w; x++)
            {
                tmp[y * w + x] = sum / count;
                int remove = Math.Clamp(x - radius, 0, w - 1);
                int add = Math.Clamp(x + radius + 1, 0, w - 1);
                sum += src[y * w + add] - src[y * w + remove];
            }
        }

        for (int x = 0; x < w; x++)
        {
            double sum = 0;
            int count = 0;
            for (int y = -radius; y <= radius; y++)
            {
                int yy = Math.Clamp(y, 0, h - 1);
                sum += tmp[yy * w + x]; count++;
            }
            for (int y = 0; y < h; y++)
            {
                dst[y * w + x] = sum / count;
                int remove = Math.Clamp(y - radius, 0, h - 1);
                int add = Math.Clamp(y + radius + 1, 0, h - 1);
                sum += tmp[add * w + x] - tmp[remove * w + x];
            }
        }
        return dst;
    }
}
