using System.Text.Json;

namespace DarkWolfPBRStudio.Services;

public sealed class AppSettings
{
    public string StableDiffusionCliPath { get; set; } = "";
    public string StableDiffusionModelPath { get; set; } = "";
    public string StableDiffusionExtraArgs { get; set; } = "";
    public string LastPk3Directory { get; set; } = "";
    public double AiStrength { get; set; } = 0.28;

    public static string SettingsPath
    {
        get
        {
            var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DarkWolfPBRStudio");
            Directory.CreateDirectory(dir);
            return Path.Combine(dir, "settings.json");
        }
    }

    public static AppSettings Load()
    {
        try
        {
            if (File.Exists(SettingsPath))
                return JsonSerializer.Deserialize<AppSettings>(File.ReadAllText(SettingsPath)) ?? new AppSettings();
        }
        catch { }
        return new AppSettings();
    }

    public void Save()
    {
        File.WriteAllText(SettingsPath, JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true }));
    }
}
