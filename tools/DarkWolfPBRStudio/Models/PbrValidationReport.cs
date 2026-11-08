namespace DarkWolfPBRStudio.Models;

public sealed record PbrValidationReport(
    double MeanNormalAngleDeg,
    double P90NormalAngleDeg,
    double MeanAo,
    double MinAo,
    double MeanRoughness,
    double MinRoughness,
    double MaxRoughness,
    double MeanMetallic,
    double HeightP05,
    double HeightP95,
    IReadOnlyList<string> Warnings)
{
    public string Summary
    {
        get
        {
            string w = Warnings.Count == 0 ? "PASS" : string.Join(" | ", Warnings);
            return $"Normal mean {MeanNormalAngleDeg:0.0}°, P90 {P90NormalAngleDeg:0.0}°; " +
                   $"AO {MeanAo:0.00}; Roughness {MeanRoughness:0.00} [{MinRoughness:0.00}-{MaxRoughness:0.00}]; " +
                   $"Metallic {MeanMetallic:0.00}; Height P05-P95 {HeightP05:0.00}-{HeightP95:0.00}. {w}";
        }
    }
}
