using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio.Services;

public static class TgaCodec
{
    public static BitmapSource Decode(byte[] data)
    {
        if (data.Length < 18) throw new InvalidDataException("TGA header is truncated.");
        int idLength = data[0];
        int imageType = data[2];
        int width = data[12] | (data[13] << 8);
        int height = data[14] | (data[15] << 8);
        int bpp = data[16];
        int descriptor = data[17];

        if (width <= 0 || height <= 0) throw new InvalidDataException("Invalid TGA dimensions.");
        bool rle = imageType is 10 or 11;
        bool gray = imageType is 3 or 11;
        if (!gray && bpp is not (24 or 32)) throw new NotSupportedException($"TGA {bpp} bpp is not supported.");
        if (gray && bpp != 8) throw new NotSupportedException("Only 8-bit grayscale TGA is supported.");
        if (imageType is not (2 or 3 or 10 or 11)) throw new NotSupportedException($"TGA type {imageType} is not supported.");

        int srcBpp = gray ? 1 : bpp / 8;
        int pos = 18 + idLength;
        var pixels = new byte[width * height * 4];

        void WritePixel(int pixelIndex, ReadOnlySpan<byte> px)
        {
            int x = pixelIndex % width;
            int y = pixelIndex / width;
            bool topOrigin = (descriptor & 0x20) != 0;
            int dy = topOrigin ? y : (height - 1 - y);
            int dst = (dy * width + x) * 4;
            if (gray)
            {
                pixels[dst] = pixels[dst + 1] = pixels[dst + 2] = px[0];
                pixels[dst + 3] = 255;
            }
            else
            {
                pixels[dst] = px[0];
                pixels[dst + 1] = px[1];
                pixels[dst + 2] = px[2];
                pixels[dst + 3] = srcBpp == 4 ? px[3] : (byte)255;
            }
        }

        int total = width * height;
        int outIndex = 0;
        if (!rle)
        {
            for (; outIndex < total; outIndex++)
            {
                if (pos + srcBpp > data.Length) throw new InvalidDataException("TGA pixel data is truncated.");
                WritePixel(outIndex, data.AsSpan(pos, srcBpp));
                pos += srcBpp;
            }
        }
        else
        {
            while (outIndex < total)
            {
                if (pos >= data.Length) throw new InvalidDataException("TGA RLE data is truncated.");
                byte packet = data[pos++];
                int count = (packet & 0x7F) + 1;
                if ((packet & 0x80) != 0)
                {
                    if (pos + srcBpp > data.Length) throw new InvalidDataException("TGA RLE packet is truncated.");
                    var px = data.AsSpan(pos, srcBpp);
                    pos += srcBpp;
                    for (int i = 0; i < count && outIndex < total; i++, outIndex++) WritePixel(outIndex, px);
                }
                else
                {
                    for (int i = 0; i < count && outIndex < total; i++, outIndex++)
                    {
                        if (pos + srcBpp > data.Length) throw new InvalidDataException("TGA raw packet is truncated.");
                        WritePixel(outIndex, data.AsSpan(pos, srcBpp));
                        pos += srcBpp;
                    }
                }
            }
        }

        var bmp = BitmapSource.Create(width, height, 96, 96, PixelFormats.Bgra32, null, pixels, width * 4);
        bmp.Freeze();
        return bmp;
    }

    public static void Save(BitmapSource source, string path)
    {
        var bgra = new FormatConvertedBitmap(source, PixelFormats.Bgra32, null, 0);
        int w = bgra.PixelWidth, h = bgra.PixelHeight;
        int stride = w * 4;
        var pixels = new byte[stride * h];
        bgra.CopyPixels(pixels, stride, 0);

        using var fs = File.Create(path);
        Span<byte> header = stackalloc byte[18];
        header.Clear();
        header[2] = 2;
        header[12] = (byte)(w & 0xFF);
        header[13] = (byte)((w >> 8) & 0xFF);
        header[14] = (byte)(h & 0xFF);
        header[15] = (byte)((h >> 8) & 0xFF);
        header[16] = 32;
        header[17] = 0x28; // top-left origin + 8 alpha bits
        fs.Write(header);
        fs.Write(pixels);
    }
}
