namespace DarkWolfPBRStudio.Models;

public sealed class VariantItem
{
    public required string Name { get; init; }
    public required string FilePath { get; init; }
    public required string Kind { get; init; }
    public long? Seed { get; init; }
    public string? Prompt { get; init; }

    public override string ToString() => Name;
}
