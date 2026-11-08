namespace DarkWolfPBRStudio.Services;

public sealed class RealEsrganService
{
    public string BundledExePath =>
        Path.Combine(AppContext.BaseDirectory, "Tools", "RealESRGAN", "realesrgan-ncnn-vulkan.exe");

    public bool IsAvailable => File.Exists(BundledExePath);

    public async Task<string> RestoreX4Async(string inputPng, string outputPng, CancellationToken ct = default)
    {
        if (!IsAvailable)
            throw new FileNotFoundException("Bundled Real-ESRGAN backend was not found.", BundledExePath);

        string args = $"-i {ProcessRunner.Q(inputPng)} -o {ProcessRunner.Q(outputPng)} -n realesrgan-x4plus -s 4 -f png";
        await ProcessRunner.RunAsync(BundledExePath, args, Path.GetDirectoryName(BundledExePath), ct);
        if (!File.Exists(outputPng)) throw new InvalidOperationException("Real-ESRGAN completed but produced no output image.");
        return outputPng;
    }
}
