using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio.Models;

public sealed class BatchMaterialItem
{
    public required TextureAsset Asset { get; init; }
    public required BitmapSource BaseColor { get; init; }
    public required MaterialAnalysis Analysis { get; init; }
    public required PbrSettings Settings { get; init; }
    public required PbrResult Result { get; init; }
    public MaterialDefinitionInfo? ExistingMaterial { get; init; }
    public bool IncludeBaseColor { get; init; }

    public string DisplayName => Asset.DisplayName;
    public string EntryPath => Asset.EntryPath;
    public string MaterialKind => Analysis.Kind.ToString();
    public string MaterialMode => ExistingMaterial is null ? "Implicit → auto MTR" : "Scripted → merged MTR";
    public string Validation => Result.Report.Summary;
}
