namespace DarkWolfPBRStudio.Services;

public sealed class StableDiffusionService
{
    public string BundledCliPath =>
        Path.Combine(AppContext.BaseDirectory, "Tools", "StableDiffusionCpp", "sd-cli.exe");

    public bool IsBundledAvailable => File.Exists(BundledCliPath);

    public async Task<string> Img2ImgAsync(
        string cliPath, string modelPath, string inputPng, string outputPng,
        string prompt, double strength, long seed, string extraArgs, CancellationToken ct = default)
    {
        if (!File.Exists(cliPath)) throw new FileNotFoundException("sd-cli.exe was not found.", cliPath);
        if (!File.Exists(modelPath)) throw new FileNotFoundException("Stable Diffusion model was not found.", modelPath);

        string safePrompt = prompt.Replace("\"", "'");
        string args =
            $"-m {ProcessRunner.Q(modelPath)} -p {ProcessRunner.Q(safePrompt)} " +
            $"-i {ProcessRunner.Q(inputPng)} -o {ProcessRunner.Q(outputPng)} " +
            $"--strength {strength.ToString(System.Globalization.CultureInfo.InvariantCulture)} " +
            $"--seed {seed} --steps 20 --cfg-scale 5.0 " +
            extraArgs;

        await ProcessRunner.RunAsync(cliPath, args, Path.GetDirectoryName(cliPath), ct);
        if (!File.Exists(outputPng)) throw new InvalidOperationException("Stable Diffusion completed but produced no output image.");
        return outputPng;
    }
}
