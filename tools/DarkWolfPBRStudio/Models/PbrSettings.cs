namespace DarkWolfPBRStudio.Models;

public sealed class PbrSettings
{
    public PbrGenerationMode GenerationMode { get; set; } = PbrGenerationMode.MacroReliefEnhanced;
    public MaterialKind MaterialKind { get; set; } = MaterialKind.GenericDielectric;
    public SurfaceFinish SurfaceFinish { get; set; } = SurfaceFinish.Dry;
    public double NormalStrength { get; set; } = 14.0;
    public double HeightContrast { get; set; } = 0.72;
    public double FineWeight { get; set; } = 0.78;
    public double CoarseWeight { get; set; } = 0.22;
    public double ChromaSuppression { get; set; } = 0.70;
    public double AoStrength { get; set; } = 0.72;
    public double AoFloor { get; set; } = 0.62;
    public double RoughnessMin { get; set; } = 0.48;
    public double RoughnessMax { get; set; } = 0.94;
    public double RoughnessBase { get; set; } = 0.72;
    public double MicroRoughness { get; set; } = 0.14;
    public double BrightnessRoughness { get; set; } = 0.0;
    public double Metallic { get; set; } = 0.0;
    public bool ParallaxEnabled { get; set; }
    public double ParallaxDepth { get; set; } = 0.01;
    public double MacroReliefBoost { get; set; } = 0.75;
    public double PhysicalReliefStrength { get; set; } = 1.0;
    public double PhysicalNormalCoupling { get; set; } = 1.25;

    public static PbrSettings FromProfile(MaterialProfile profile) => new()
    {
        MaterialKind = profile.Kind,
        NormalStrength = profile.NormalStrength,
        HeightContrast = profile.HeightContrast,
        FineWeight = profile.FineWeight,
        CoarseWeight = profile.CoarseWeight,
        ChromaSuppression = profile.ChromaSuppression,
        AoStrength = profile.AoStrength,
        AoFloor = profile.AoFloor,
        RoughnessBase = profile.RoughnessBase,
        RoughnessMin = profile.RoughnessMin,
        RoughnessMax = profile.RoughnessMax,
        MicroRoughness = profile.MicroRoughness,
        BrightnessRoughness = profile.BrightnessRoughness,
        Metallic = profile.Metallic,
        ParallaxEnabled = profile.ParallaxRecommended,
        ParallaxDepth = profile.ParallaxDepth
    };
}
