namespace DarkWolfPBRStudio.Models;

public sealed class TextureAsset
{
    public required string EntryPath { get; init; }
    public required string DisplayName { get; init; }
    public required string Extension { get; init; }
    public required string ShaderName { get; init; }
    public long Size { get; init; }

    public override string ToString() => EntryPath;
}
