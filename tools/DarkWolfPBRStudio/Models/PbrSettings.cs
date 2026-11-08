namespace DarkWolfPBRStudio.Models;

public sealed class PbrSettings
{
    public double NormalStrength { get; set; } = 20.0;
    public double AoFloor { get; set; } = 0.46;
    public double RoughnessMin { get; set; } = 0.46;
    public double RoughnessMax { get; set; } = 0.92;
    public double RoughnessBase { get; set; } = 0.60;
}
