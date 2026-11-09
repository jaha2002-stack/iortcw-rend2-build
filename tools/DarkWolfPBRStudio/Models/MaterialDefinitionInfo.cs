namespace DarkWolfPBRStudio.Models;

public sealed record MaterialDefinitionInfo(
    string ShaderName,
    string SourcePk3,
    string ScriptPath,
    string Block)
{
    // Rend2 discovers only scripts/*.shader. If a same-basename .mtr exists,
    // the .mtr replaces the entire .shader text for Rend2 parsing.
    public string DiscoveryShaderPath { get; init; } =
        ScriptPath.EndsWith(".mtr", StringComparison.OrdinalIgnoreCase)
            ? ScriptPath[..^4] + ".shader"
            : ScriptPath;

    // Full legacy fallback file that must remain loadable by renderers which
    // do not understand Rend2 PBR material extensions.
    public string FallbackShaderText { get; init; } = Block;

    // Full text Rend2 actually parsed: same-basename .mtr when present,
    // otherwise the discovery .shader text.
    public string EffectiveScriptText { get; init; } = Block;

    public string ScriptBasePath =>
        DiscoveryShaderPath.EndsWith(".shader", StringComparison.OrdinalIgnoreCase)
            ? DiscoveryShaderPath[..^7]
            : Path.ChangeExtension(DiscoveryShaderPath, null)!.Replace('\\', '/');

    public bool UsesMtr => ScriptPath.EndsWith(".mtr", StringComparison.OrdinalIgnoreCase);
}
