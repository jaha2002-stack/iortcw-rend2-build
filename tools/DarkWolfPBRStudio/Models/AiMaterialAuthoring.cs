namespace DarkWolfPBRStudio.Models;

public enum AiAuthoringMode
{
    OriginalRestore4x,
    ArtisticRebuild
}

public enum SurfaceFinish
{
    Dry,
    Wet,
    Snowy,
    WetSnow,
    Mossy
}

public static class AiMaterialAuthoringPresets
{
    public static string BuildPrompt(
        MaterialProfile profile,
        SurfaceFinish finish,
        string? userPrompt = null)
    {
        string finishPrompt = finish switch
        {
            SurfaceFinish.Wet =>
                "slightly damp material with darker moisture coloration in coherent patches and recesses, no painted specular highlights",
            SurfaceFinish.Snowy =>
                "natural settled snow on upward and sheltered areas, preserved underlying material structure, no painted lighting",
            SurfaceFinish.WetSnow =>
                "partially wet material with natural snow deposits, damp exposed areas and melt-darkened recesses, no painted reflections",
            SurfaceFinish.Mossy =>
                "restrained natural moss in cracks and sheltered recesses, preserve original material identity, no excessive vegetation",
            _ =>
                "dry material response, preserve original material identity"
        };

        string extra = string.IsNullOrWhiteSpace(userPrompt) ? "" : $", {userPrompt.Trim()}";

        return $"{profile.PromptHint}, {finishPrompt}, preserve exact original UV layout, geometry cues, composition and color identity, seamless tileable game texture, high-frequency material detail, albedo/base-color authoring only, neutral diffuse lighting, no directional shadows, no baked ambient occlusion, no baked specular highlights, no text, no new objects, no perspective distortion{extra}";
    }
}
