using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio.Services;

public static class ImageService
{
    public static BitmapSource Load(byte[] bytes, string extension)
    {
        extension = extension.ToLowerInvariant();
        if (extension == ".tga") return TgaCodec.Decode(bytes);

        using var ms = new MemoryStream(bytes, false);
        var bmp = new BitmapImage();
        bmp.BeginInit();
        bmp.CacheOption = BitmapCacheOption.OnLoad;
        bmp.StreamSource = ms;
        bmp.EndInit();
        bmp.Freeze();
        return bmp;
    }

    public static BitmapSource LoadFile(string path)
        => Load(File.ReadAllBytes(path), Path.GetExtension(path));

    public static void SavePng(BitmapSource source, string path)
    {
        using var fs = File.Create(path);
        var enc = new PngBitmapEncoder();
        enc.Frames.Add(BitmapFrame.Create(source));
        enc.Save(fs);
    }

    public static void SaveJpeg(BitmapSource source, string path, int quality = 96)
    {
        using var fs = File.Create(path);
        var enc = new JpegBitmapEncoder { QualityLevel = quality };
        enc.Frames.Add(BitmapFrame.Create(source));
        enc.Save(fs);
    }

    public static void SavePreservingExtension(BitmapSource source, string path)
    {
        switch (Path.GetExtension(path).ToLowerInvariant())
        {
            case ".jpg":
            case ".jpeg": SaveJpeg(source, path); break;
            case ".tga": TgaCodec.Save(source, path); break;
            default: SavePng(source, path); break;
        }
    }

    public static byte[] EncodePreservingExtension(BitmapSource source, string extension)
    {
        string temp = Path.Combine(Path.GetTempPath(), $"dw_pbr_{Guid.NewGuid():N}{extension}");
        try
        {
            SavePreservingExtension(source, temp);
            return File.ReadAllBytes(temp);
        }
        finally
        {
            try { File.Delete(temp); } catch { }
        }
    }

    public static byte[] ToBgra(BitmapSource source, out int width, out int height)
    {
        var bgra = new FormatConvertedBitmap(source, PixelFormats.Bgra32, null, 0);
        width = bgra.PixelWidth;
        height = bgra.PixelHeight;
        var pixels = new byte[width * height * 4];
        bgra.CopyPixels(pixels, width * 4, 0);
        return pixels;
    }

    public static BitmapSource FromBgra(byte[] bytes, int width, int height)
    {
        var bmp = BitmapSource.Create(width, height, 96, 96, PixelFormats.Bgra32, null, bytes, width * 4);
        bmp.Freeze();
        return bmp;
    }
}
