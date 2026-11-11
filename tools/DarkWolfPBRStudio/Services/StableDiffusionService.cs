namespace DarkWolfPBRStudio.Services;

public sealed class StableDiffusionService
{
    public string BundledRoot =>
        Path.Combine(AppContext.BaseDirectory, "Tools", "StableDiffusionCpp");

    public string BundledCliPath =>
        Path.Combine(BundledRoot, "sd-cli.exe");

    public string BundledModelsPath =>
        Path.Combine(BundledRoot, "models");

    public bool IsBundledAvailable => File.Exists(BundledCliPath);

    public string ResolveCliPath(string? configuredPath)
    {
        // Packaged builds always prefer their validated local CLI. This makes the
        // application portable across V2.06/V2.06.1 folders and prevents an old
        // absolute path from forcing the user into an sd-cli.exe file dialog.
        if (File.Exists(BundledCliPath))
            return BundledCliPath;

        string configured = configuredPath?.Trim() ?? "";
        return File.Exists(configured) ? configured : "";
    }

    public string ResolveModelPath(string? configuredPath)
    {
        string configured = configuredPath?.Trim() ?? "";
        if (File.Exists(configured) && IsSupportedModel(configured))
            return configured;

        // If settings point to the same model in an older Studio directory,
        // relocate it by file name into the current portable models directory.
        string preferredName = string.IsNullOrWhiteSpace(configured)
            ? ""
            : Path.GetFileName(configured);

        string? found = FindModelInDirectory(BundledModelsPath, preferredName);
        if (!string.IsNullOrEmpty(found))
            return found;

        // Also accept models placed beside sd-cli.exe for backwards compatibility.
        found = FindModelInDirectory(BundledRoot, preferredName);
        return found ?? "";
    }

    public static string? FindModelInDirectory(string directory, string? preferredFileName = null)
    {
        if (!Directory.Exists(directory))
            return null;

        var models = Directory.EnumerateFiles(directory, "*", SearchOption.TopDirectoryOnly)
            .Where(IsSupportedModel)
            .OrderBy(p => ModelExtensionPriority(Path.GetExtension(p)))
            .ThenBy(p => Path.GetFileName(p), StringComparer.OrdinalIgnoreCase)
            .ToList();

        if (!string.IsNullOrWhiteSpace(preferredFileName))
        {
            string? preferred = models.FirstOrDefault(p =>
                Path.GetFileName(p).Equals(preferredFileName, StringComparison.OrdinalIgnoreCase));
            if (preferred is not null)
                return preferred;
        }

        return models.FirstOrDefault();
    }

    public static bool IsSupportedModel(string path)
    {
        string ext = Path.GetExtension(path);
        return ext.Equals(".safetensors", StringComparison.OrdinalIgnoreCase)
            || ext.Equals(".gguf", StringComparison.OrdinalIgnoreCase)
            || ext.Equals(".ckpt", StringComparison.OrdinalIgnoreCase);
    }

    private static int ModelExtensionPriority(string ext)
        => ext.Equals(".safetensors", StringComparison.OrdinalIgnoreCase) ? 0
         : ext.Equals(".gguf", StringComparison.OrdinalIgnoreCase) ? 1
         : ext.Equals(".ckpt", StringComparison.OrdinalIgnoreCase) ? 2
         : 9;

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
