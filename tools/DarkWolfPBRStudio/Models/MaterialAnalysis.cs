namespace DarkWolfPBRStudio.Models;

public sealed record MaterialAnalysis(
    MaterialKind Kind,
    double Confidence,
    string Reason,
    double MeanLuminance,
    double MeanSaturation,
    double LuminanceStdDev,
    double EdgeDensity)
{
    public string Summary =>
        $"{MaterialProfile.For(Kind).DisplayName} — confidence {Confidence:P0}; " +
        $"luma {MeanLuminance:0.00}, saturation {MeanSaturation:0.00}, detail {EdgeDensity:0.00}. {Reason}";
}
