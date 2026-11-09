using DarkWolfPBRStudio.Models;
using DarkWolfPBRStudio.Services;
using Microsoft.Win32;
using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;

namespace DarkWolfPBRStudio;

public partial class MainWindow : Window
{
    private readonly Pk3Service _pk3 = new();
    private readonly RealEsrganService _restore = new();
    private readonly StableDiffusionService _sd = new();
    private readonly AppSettings _settings = AppSettings.Load();
    private readonly ObservableCollection<VariantItem> _variants = new();
    private readonly ObservableCollection<BatchMaterialItem> _batchMaterials = new();
    private readonly string _sessionDir;

    private List<TextureAsset> _allTextures = new();
    private string? _pk3Path;
    private TextureAsset? _asset;
    private BitmapSource? _original;
    private BitmapSource? _current;
    private PbrResult? _pbrResult;
    private MaterialAnalysis? _analysis;
    private MaterialDefinitionInfo? _currentMaterialDefinition;
    private string? _aiSourcePath;
    private bool _hasMaterialDefinition;
    private bool _applyingProfile;
    private CancellationTokenSource? _busyCts;

    public MainWindow()
    {
        InitializeComponent();

        _sessionDir = Path.Combine(Path.GetTempPath(), "DarkWolfPBRStudioV2", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_sessionDir);

        VariantList.ItemsSource = _variants;
        BatchList.ItemsSource = _batchMaterials;
        MaterialProfileCombo.ItemsSource = Enum.GetValues<MaterialKind>();
        MaterialProfileCombo.SelectedItem = MaterialKind.Auto;
        GenerationModeCombo.ItemsSource = Enum.GetValues<PbrGenerationMode>();
        GenerationModeCombo.SelectedItem = PbrGenerationMode.MacroReliefEnhanced;
        ApplyGenerationModePreset(PbrGenerationMode.MacroReliefEnhanced);

        SdCliPathBox.Text = !string.IsNullOrWhiteSpace(_settings.StableDiffusionCliPath)
            ? _settings.StableDiffusionCliPath
            : (_sd.IsBundledAvailable ? _sd.BundledCliPath : "");
        SdModelPathBox.Text = _settings.StableDiffusionModelPath;
        SdExtraArgsBox.Text = _settings.StableDiffusionExtraArgs;
        AiStrengthSlider.Value = _settings.AiStrength;

        ApplyProfile(MaterialProfile.For(MaterialKind.GenericDielectric), keepComboSelection: true);
        ApplyGenerationModePreset(PbrGenerationMode.MacroReliefEnhanced);
        UpdateSliderLabels();

        Status($"Ready. Real-ESRGAN: {(_restore.IsAvailable ? "bundled" : "missing")}; stable-diffusion.cpp: {(_sd.IsBundledAvailable ? "bundled" : "missing")}.");

        Closed += (_, _) =>
        {
            SaveSettings();
            try { Directory.Delete(_sessionDir, true); } catch { }
        };
    }

    private async void OpenPk3Button_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog
        {
            Filter = "RTCW PK3 archives (*.pk3)|*.pk3|ZIP archives (*.zip)|*.zip|All files (*.*)|*.*",
            InitialDirectory = Directory.Exists(_settings.LastPk3Directory) ? _settings.LastPk3Directory : null
        };
        if (dlg.ShowDialog(this) != true) return;

        await BusyAsync("Reading PK3 texture index…", async ct =>
        {
            var textures = await Task.Run(() => _pk3.ListTextures(dlg.FileName), ct);
            await Dispatcher.InvokeAsync(() =>
            {
                _pk3Path = dlg.FileName;
                _settings.LastPk3Directory = Path.GetDirectoryName(dlg.FileName) ?? "";
                Pk3PathText.Text = dlg.FileName;
                _allTextures = textures.ToList();
                ApplyTextureFilter();
                Status($"Loaded {_allTextures.Count:N0} image entries from {Path.GetFileName(dlg.FileName)}.");
            });
        });
    }

    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e) => ApplyTextureFilter();

    private void ApplyTextureFilter()
    {
        string q = SearchBox?.Text?.Trim() ?? "";
        TextureList.ItemsSource = string.IsNullOrWhiteSpace(q)
            ? _allTextures
            : _allTextures.Where(x => x.EntryPath.Contains(q, StringComparison.OrdinalIgnoreCase)).ToList();
    }

    private async void TextureList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        SelectedTextureCountText.Text = $"Selected: {TextureList.SelectedItems.Count}";
        if (_pk3Path is null || TextureList.SelectedItem is not TextureAsset asset) return;
        if (TextureList.SelectedItems.Count > 1)
        {
            Status($"{TextureList.SelectedItems.Count} textures selected for batch generation.");
            return;
        }
        _asset = asset;

        await BusyAsync($"Loading and analyzing {asset.EntryPath}…", async ct =>
        {
            byte[] bytes = await Task.Run(() => _pk3.ReadEntry(_pk3Path, asset.EntryPath), ct);
            BitmapSource bmp = await Dispatcher.InvokeAsync(() => ImageService.Load(bytes, asset.Extension));
            string originalPath = Path.Combine(_sessionDir, $"original_{Guid.NewGuid():N}.png");
            await Dispatcher.InvokeAsync(() => ImageService.SavePng(bmp, originalPath));

            MaterialDefinitionInfo? materialDef = await Task.Run(() => _pk3.FindMaterialDefinitionInDirectory(_pk3Path, asset.ShaderName), ct);
            bool hasDef = materialDef is not null;
            MaterialAnalysis analysis = await Task.Run(() => MaterialClassifier.Analyze(asset.EntryPath, bmp), ct);

            await Dispatcher.InvokeAsync(() =>
            {
                _original = _current = bmp;
                OriginalImage.Source = bmp;
                CurrentImage.Source = bmp;
                ResetPbrPreview();

                _variants.Clear();
                _variants.Add(new VariantItem { Name = "Original", FilePath = originalPath, Kind = "Original" });
                VariantList.SelectedIndex = 0;
                _aiSourcePath = originalPath;

                _hasMaterialDefinition = hasDef;
                _currentMaterialDefinition = materialDef;
                MaterialStatusText.Text = hasDef ? "Material: scripted → full safe source pair" : "Material: implicit → safe fallback + PBR MTR";
                CompatibilityHintText.Text = hasDef
                    ? $"Existing scripted material: {materialDef!.SourcePk3} / {materialDef.DiscoveryShaderPath}. V2.05.2 exports the complete original .shader plus a complete same-basename .mtr with only the selected material upgraded."
                    : "Implicit texture: V2.05.2 creates a legacy-safe .shader fallback plus a same-basename PBR .mtr.";

                SetAnalysis(analysis, applyRecommendedProfile: true);
                Status($"{asset.EntryPath} — {bmp.PixelWidth}×{bmp.PixelHeight}; {MaterialProfile.For(analysis.Kind).DisplayName}.");
            });
        });
    }

    private void SetAnalysis(MaterialAnalysis analysis, bool applyRecommendedProfile)
    {
        _analysis = analysis;
        MaterialAnalysisText.Text = analysis.Summary;

        if (applyRecommendedProfile)
        {
            _applyingProfile = true;
            MaterialProfileCombo.SelectedItem = analysis.Kind;
            _applyingProfile = false;
            ApplyProfile(MaterialProfile.For(analysis.Kind), keepComboSelection: true);
            if (GenerationModeCombo.SelectedItem is PbrGenerationMode gm)
                ApplyGenerationModePreset(gm);

            if (string.IsNullOrWhiteSpace(PromptBox.Text) || PromptBox.Text.Contains("restore authentic", StringComparison.OrdinalIgnoreCase))
                PromptBox.Text = BuildPrompt(MaterialProfile.For(analysis.Kind));
            else if (!PromptBox.Text.Contains(MaterialProfile.For(analysis.Kind).PromptHint, StringComparison.OrdinalIgnoreCase))
                PromptBox.Text = BuildPrompt(MaterialProfile.For(analysis.Kind));
        }
    }

    private string BuildPrompt(MaterialProfile profile)
        => $"{profile.PromptHint}, preserve original UV layout, exact composition and color identity, seamless game texture, physically plausible PBR source";

    private async void AnalyzeMaterialButton_Click(object sender, RoutedEventArgs e)
    {
        if (_current is null || _asset is null) return;

        await BusyAsync("Analyzing material…", async ct =>
        {
            MaterialAnalysis analysis = await Task.Run(() => MaterialClassifier.Analyze(_asset.EntryPath, _current), ct);
            await Dispatcher.InvokeAsync(() =>
            {
                SetAnalysis(analysis, applyRecommendedProfile: true);
                Status($"Material analysis: {analysis.Summary}");
            });
        });
    }

    private void GenerationModeCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_applyingProfile || GenerationModeCombo.SelectedItem is not PbrGenerationMode mode) return;
        ApplyGenerationModePreset(mode);
        ResetPbrPreview();
    }

    private void ApplyGenerationModePreset(PbrGenerationMode mode)
    {
        _applyingProfile = true;
        try
        {
            switch (mode)
            {
                case PbrGenerationMode.ReferenceHandGenerated:
                    NormalStrengthSlider.Value = 20;
                    HeightContrastSlider.Value = 1.00;
                    MacroReliefBoostSlider.Value = 0.00;
                    GenerationModeHintText.Text = "Exact First Hand-Generated reference: 74% fine + 26% coarse absolute luminance, original successful ORM response, no artificial groove/pit detector.";
                    break;

                case PbrGenerationMode.MacroReliefEnhanced:
                    NormalStrengthSlider.Value = 20;
                    HeightContrastSlider.Value = 1.00;
                    MacroReliefBoostSlider.Value = 0.75;
                    GenerationModeHintText.Text = "Enhanced Macro Relief: keeps the First Hand-Generated height/ORM unchanged and strengthens only broad coherent stone-boundary normals. It cannot create new interior pits from dark JPEG specks.";
                    break;

                case PbrGenerationMode.PhysicalReliefPOM:
                    NormalStrengthSlider.Value = 20;
                    HeightContrastSlider.Value = 1.00;
                    MacroReliefBoostSlider.Value = 0.75;
                    ParallaxCheck.IsChecked = true;
                    if (ParallaxDepthSlider.Value < 0.018)
                        ParallaxDepthSlider.Value = 0.030;
                    GenerationModeHintText.Text = "Physical Relief / POM: preserves the accepted V2.03 macro Normal/ORM, but generates a separate wide-range low-frequency Height field for deep mortar and stone relief. Designed for PBR V3.2 POM.";
                    break;

                default:
                    NormalStrengthSlider.Value = 20;
                    HeightContrastSlider.Value = 1.00;
                    MacroReliefBoostSlider.Value = 0.42;
                    GenerationModeHintText.Text = "V2.02 compatibility mode.";
                    break;
            }
            UpdateSliderLabels();
        }
        finally
        {
            _applyingProfile = false;
        }
    }

    private void MaterialProfileCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_applyingProfile || MaterialProfileCombo.SelectedItem is not MaterialKind selected) return;

        MaterialKind actual = selected == MaterialKind.Auto
            ? (_analysis?.Kind ?? MaterialKind.GenericDielectric)
            : selected;

        ApplyProfile(MaterialProfile.For(actual), keepComboSelection: true);
        if (GenerationModeCombo.SelectedItem is PbrGenerationMode.PhysicalReliefPOM)
            ApplyGenerationModePreset(PbrGenerationMode.PhysicalReliefPOM);
        ResetPbrPreview();
        Status($"PBR profile: {MaterialProfile.For(actual).DisplayName}.");
    }

    private void ApplyProfile(MaterialProfile profile, bool keepComboSelection)
    {
        _applyingProfile = true;
        try
        {
            NormalStrengthSlider.Value = profile.NormalStrength;
            HeightContrastSlider.Value = profile.HeightContrast;
            RoughnessMinSlider.Value = profile.RoughnessMin;
            RoughnessMaxSlider.Value = profile.RoughnessMax;
            MetallicSlider.Value = profile.Metallic;
            ParallaxCheck.IsChecked = profile.ParallaxRecommended;
            ParallaxDepthSlider.Value = profile.ParallaxDepth;
            if (!keepComboSelection) MaterialProfileCombo.SelectedItem = profile.Kind;
            UpdateSliderLabels();
        }
        finally
        {
            _applyingProfile = false;
        }
    }

    private async void RestoreButton_Click(object sender, RoutedEventArgs e)
    {
        if (_current is null) { MessageBox.Show(this, "Select a texture first."); return; }
        if (!_restore.IsAvailable)
        {
            MessageBox.Show(this, "Bundled Real-ESRGAN backend is not present in this build.", "AI backend");
            return;
        }

        await BusyAsync("AI Restoration ×4…", async ct =>
        {
            string input = Path.Combine(_sessionDir, $"restore_in_{Guid.NewGuid():N}.png");
            string output = Path.Combine(_sessionDir, $"restore_x4_{Guid.NewGuid():N}.png");
            await Dispatcher.InvokeAsync(() => ImageService.SavePng(_current, input));
            await _restore.RestoreX4Async(input, output, ct);
            var bmp = ImageService.LoadFile(output);

            await Dispatcher.InvokeAsync(() =>
            {
                var item = new VariantItem
                {
                    Name = $"AI Restore ×4 #{_variants.Count}",
                    FilePath = output,
                    Kind = "AI Restoration"
                };
                _variants.Add(item);
                VariantList.SelectedItem = item;
                _aiSourcePath = output;
                Status($"AI Restoration complete: {bmp.PixelWidth}×{bmp.PixelHeight}.");
            });
        });
    }

    private async void AiNextButton_Click(object sender, RoutedEventArgs e)
    {
        if (_current is null) { MessageBox.Show(this, "Select a texture first."); return; }
        if (!EnsureStableDiffusionPaths()) return;

        _aiSourcePath ??= GetSelectedVariant()?.FilePath;
        if (string.IsNullOrEmpty(_aiSourcePath) || !File.Exists(_aiSourcePath))
        {
            _aiSourcePath = Path.Combine(_sessionDir, $"ai_source_{Guid.NewGuid():N}.png");
            ImageService.SavePng(_current, _aiSourcePath);
        }

        long seed = Random.Shared.NextInt64(1, int.MaxValue);
        string output = Path.Combine(_sessionDir, $"ai_variant_{seed}.png");
        string prompt = PromptBox.Text.Trim();
        double strength = AiStrengthSlider.Value;

        await BusyAsync($"AI Next — seed {seed}…", async ct =>
        {
            await _sd.Img2ImgAsync(
                SdCliPathBox.Text.Trim(), SdModelPathBox.Text.Trim(), _aiSourcePath!, output,
                prompt, strength, seed, SdExtraArgsBox.Text.Trim(), ct);

            await Dispatcher.InvokeAsync(() =>
            {
                var item = new VariantItem
                {
                    Name = $"AI Variant {seed}",
                    FilePath = output,
                    Kind = "AI img2img",
                    Seed = seed,
                    Prompt = prompt
                };
                _variants.Add(item);
                VariantList.SelectedItem = item;
                VariantList.ScrollIntoView(item);
                Status($"Generated AI variation seed {seed}. Press AI Next for another.");
            });
        });
    }

    private bool EnsureStableDiffusionPaths()
    {
        if (!File.Exists(SdCliPathBox.Text.Trim()))
        {
            BrowseSdCli_Click(this, new RoutedEventArgs());
            if (!File.Exists(SdCliPathBox.Text.Trim())) return false;
        }
        if (!File.Exists(SdModelPathBox.Text.Trim()))
        {
            BrowseSdModel_Click(this, new RoutedEventArgs());
            if (!File.Exists(SdModelPathBox.Text.Trim())) return false;
        }
        SaveSettings();
        return true;
    }

    private void BrowseSdCli_Click(object sender, RoutedEventArgs e)
    {
        var d = new OpenFileDialog { Filter = "stable-diffusion.cpp CLI (sd-cli.exe)|sd-cli.exe|Executables (*.exe)|*.exe" };
        if (d.ShowDialog(this) == true) SdCliPathBox.Text = d.FileName;
    }

    private void BrowseSdModel_Click(object sender, RoutedEventArgs e)
    {
        var d = new OpenFileDialog { Filter = "AI models (*.safetensors;*.gguf;*.ckpt)|*.safetensors;*.gguf;*.ckpt|All files (*.*)|*.*" };
        if (d.ShowDialog(this) == true) SdModelPathBox.Text = d.FileName;
    }

    private void SetAiSource_Click(object sender, RoutedEventArgs e)
    {
        var v = GetSelectedVariant();
        if (v is null) return;
        _aiSourcePath = v.FilePath;
        Status($"AI source fixed to: {v.Name}. AI Next will branch from this source.");
    }

    private void VariantList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        var v = GetSelectedVariant();
        if (v is null || !File.Exists(v.FilePath)) return;

        try
        {
            _current = ImageService.LoadFile(v.FilePath);
            CurrentImage.Source = _current;
            IncludeBaseColorCheck.IsChecked = v.Kind != "Original";
            ResetPbrPreview();
            Status($"Selected variant: {v.Name}.");
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Variant load error");
        }
    }

    private VariantItem? GetSelectedVariant() => VariantList.SelectedItem as VariantItem;

    private void PreviousVariant_Click(object sender, RoutedEventArgs e)
    {
        if (_variants.Count == 0) return;
        VariantList.SelectedIndex = Math.Max(0, VariantList.SelectedIndex - 1);
        VariantList.ScrollIntoView(VariantList.SelectedItem);
    }

    private void NextVariant_Click(object sender, RoutedEventArgs e)
    {
        if (_variants.Count == 0) return;
        VariantList.SelectedIndex = Math.Min(_variants.Count - 1, VariantList.SelectedIndex + 1);
        VariantList.ScrollIntoView(VariantList.SelectedItem);
    }

    private async void GeneratePbrButton_Click(object sender, RoutedEventArgs e)
    {
        if (_current is null) { MessageBox.Show(this, "Select a texture or variant first."); return; }

        var settings = ReadPbrSettings();
        var source = _current;

        await BusyAsync("PBR V2.03: generating Height / Normal / AO / Roughness / Metallic…", async ct =>
        {
            var result = await Task.Run(() => PbrGenerator.Generate(source, settings), ct);
            await Dispatcher.InvokeAsync(() =>
            {
                _pbrResult = result;
                HeightImage.Source = result.Height;
                NormalImage.Source = result.Normal;
                OrmImage.Source = result.Orm;
                ValidationText.Text = "Validation: " + result.Report.Summary;
                Status($"PBR3 material generated. {result.Report.Summary}");
            });
        });
    }

    private void ResetPbrPreview()
    {
        _pbrResult = null;
        if (HeightImage is not null) HeightImage.Source = null;
        if (NormalImage is not null) NormalImage.Source = null;
        if (OrmImage is not null) OrmImage.Source = null;
        if (ValidationText is not null) ValidationText.Text = "Validation: not generated";
    }

    private void ExportButton_Click(object sender, RoutedEventArgs e)
    {
        if (_asset is null || _current is null) { MessageBox.Show(this, "Select a texture first."); return; }
        if (_pbrResult is null) { MessageBox.Show(this, "Generate the PBR3 material first."); return; }

        string stem = Path.GetFileNameWithoutExtension(_asset.DisplayName);
        var d = new SaveFileDialog
        {
            Filter = "RTCW PK3 (*.pk3)|*.pk3",
            FileName = $"zzz_dw_{stem}_pbr3_v2052.pk3"
        };
        if (d.ShowDialog(this) != true) return;

        try
        {
            var analysis = _analysis ?? MaterialClassifier.Analyze(_asset.EntryPath, _current);
            var item = new BatchMaterialItem
            {
                Asset = _asset,
                BaseColor = _current,
                Analysis = analysis,
                Settings = ReadPbrSettings(),
                Result = _pbrResult,
                ExistingMaterial = _currentMaterialDefinition,
                IncludeBaseColor = IncludeBaseColorCheck.IsChecked == true
            };

            BatchPbrExportService.Export(d.FileName, new[] { item });
            Status($"Exported V2.05.2 material set: {d.FileName}");
            MessageBox.Show(this,
                "PBR Studio V2.05.2 PK3 created. Rend2 material registration is automatic.\n\n" +
                $"{_asset.ShaderName}_n.tga\n{_asset.ShaderName}_orm.tga\n" +
                "Safe material registration was written into scripts/. Implicit materials use a legacy fallback + PBR MTR pair; scripted materials keep their original discovery basename and complete source file.",
                "Export complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.ToString(), "Export failed");
        }
    }

    private async void GenerateBatchButton_Click(object sender, RoutedEventArgs e)
    {
        if (_pk3Path is null)
        {
            MessageBox.Show(this, "Open a PK3 first.");
            return;
        }

        var selected = TextureList.SelectedItems.Cast<TextureAsset>()
            .GroupBy(x => x.ShaderName, StringComparer.OrdinalIgnoreCase)
            .Select(g => g.First())
            .OrderBy(x => x.EntryPath, StringComparer.OrdinalIgnoreCase)
            .ToList();

        if (selected.Count == 0)
        {
            MessageBox.Show(this, "Select two or more textures (Ctrl/Shift click) first.");
            return;
        }

        var uiTemplate = ReadPbrSettings();
        MaterialKind requestedKind = MaterialProfileCombo.SelectedItem is MaterialKind k ? k : MaterialKind.Auto;
        var generated = new List<BatchMaterialItem>(selected.Count);

        await BusyAsync($"Generating batch: 0/{selected.Count}…", async ct =>
        {
            for (int index = 0; index < selected.Count; index++)
            {
                ct.ThrowIfCancellationRequested();
                TextureAsset asset = selected[index];

                var item = await Task.Run(() =>
                {
                    byte[] bytes = _pk3.ReadEntry(_pk3Path, asset.EntryPath);
                    BitmapSource source = ImageService.Load(bytes, asset.Extension);
                    MaterialAnalysis analysis = MaterialClassifier.Analyze(asset.EntryPath, source);
                    MaterialKind actual = requestedKind == MaterialKind.Auto ? analysis.Kind : requestedKind;

                    PbrSettings settings = PbrSettings.FromProfile(MaterialProfile.For(actual));
                    settings.GenerationMode = uiTemplate.GenerationMode;
                    settings.MacroReliefBoost = uiTemplate.MacroReliefBoost;
                    settings.NormalStrength = uiTemplate.NormalStrength;
                    settings.HeightContrast = uiTemplate.HeightContrast;
                    settings.RoughnessMin = uiTemplate.RoughnessMin;
                    settings.RoughnessMax = uiTemplate.RoughnessMax;
                    settings.RoughnessBase = Math.Clamp(settings.RoughnessBase, settings.RoughnessMin, settings.RoughnessMax);
                    settings.Metallic = uiTemplate.Metallic;
                    settings.ParallaxEnabled = uiTemplate.ParallaxEnabled;
                    settings.ParallaxDepth = uiTemplate.ParallaxDepth;

                    PbrResult result = PbrGenerator.Generate(source, settings);
                    MaterialDefinitionInfo? existing = _pk3.FindMaterialDefinitionInDirectory(_pk3Path, asset.ShaderName);

                    return new BatchMaterialItem
                    {
                        Asset = asset,
                        BaseColor = source,
                        Analysis = analysis,
                        Settings = settings,
                        Result = result,
                        ExistingMaterial = existing,
                        IncludeBaseColor = false
                    };
                }, ct);

                generated.Add(item);
                int done = index + 1;
                await Dispatcher.InvokeAsync(() => Status($"Generating batch: {done}/{selected.Count} — {asset.EntryPath}"));
            }

            await Dispatcher.InvokeAsync(() =>
            {
                _batchMaterials.Clear();
                foreach (var item in generated) _batchMaterials.Add(item);
                if (_batchMaterials.Count > 0) BatchList.SelectedIndex = 0;
                Status($"Batch ready: {_batchMaterials.Count} materials. Review them, remove any rejected item, then export ONE PK3.");
            });
        });
    }

    private void BatchList_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (BatchList.SelectedItem is not BatchMaterialItem item) return;

        OriginalImage.Source = item.BaseColor;
        CurrentImage.Source = item.BaseColor;
        HeightImage.Source = item.Result.Height;
        NormalImage.Source = item.Result.Normal;
        OrmImage.Source = item.Result.Orm;
        ValidationText.Text = "Validation: " + item.Result.Report.Summary;

        _asset = item.Asset;
        _original = _current = item.BaseColor;
        _pbrResult = item.Result;
        _analysis = item.Analysis;
        _currentMaterialDefinition = item.ExistingMaterial;
        _hasMaterialDefinition = item.ExistingMaterial is not null;

        MaterialStatusText.Text = item.ExistingMaterial is null
            ? "Material: implicit → safe fallback + PBR MTR"
            : "Material: scripted → full safe source pair";
        CompatibilityHintText.Text = item.ExistingMaterial is null
            ? "Batch export will create one owned legacy-fallback/PBR-MTR pair for implicit materials."
            : $"Batch export will preserve the complete original {item.ExistingMaterial.DiscoveryShaderPath} and emit a complete same-basename .mtr with only this selected material upgraded.";
        Status($"Batch review: {item.EntryPath} — {item.Validation}");
    }

    private void ClearBatchButton_Click(object sender, RoutedEventArgs e)
    {
        _batchMaterials.Clear();
        BatchList.Items.Refresh();
        Status("Batch cleared.");
    }

    private void RemoveBatchButton_Click(object sender, RoutedEventArgs e)
    {
        if (BatchList.SelectedItem is BatchMaterialItem item)
        {
            _batchMaterials.Remove(item);
            Status($"Removed from batch: {item.EntryPath}. Remaining: {_batchMaterials.Count}.");
        }
    }

    private void ExportBatchButton_Click(object sender, RoutedEventArgs e)
    {
        if (_batchMaterials.Count == 0)
        {
            MessageBox.Show(this, "Generate and review a batch first.");
            return;
        }

        var d = new SaveFileDialog
        {
            Filter = "RTCW PK3 (*.pk3)|*.pk3",
            FileName = $"zzz_dw_pbrstudio_v205_batch_{_batchMaterials.Count}.pk3"
        };
        if (d.ShowDialog(this) != true) return;

        try
        {
            BatchPbrExportService.Export(d.FileName, _batchMaterials.ToList());
            Status($"Batch exported: {_batchMaterials.Count} materials → {d.FileName}");
            MessageBox.Show(this,
                $"Exported {_batchMaterials.Count} materials into ONE PK3.\n\n" +
                "All generated Normal/ORM maps are included.\n" +
                "Parallax maps are included only for items generated with Parallax enabled.\n" +
                "One unique combined .shader + .mtr pair was written for the whole batch.\n" +
                "Scripted materials were merged; implicit materials received automatic definitions.",
                "Batch export complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.ToString(), "Batch export failed");
        }
    }

    private PbrSettings ReadPbrSettings()
    {
        MaterialKind selected = MaterialProfileCombo.SelectedItem is MaterialKind k ? k : MaterialKind.Auto;
        MaterialKind actual = selected == MaterialKind.Auto
            ? (_analysis?.Kind ?? MaterialKind.GenericDielectric)
            : selected;

        var settings = PbrSettings.FromProfile(MaterialProfile.For(actual));
        settings.GenerationMode = GenerationModeCombo.SelectedItem is PbrGenerationMode gm
            ? gm : PbrGenerationMode.MacroReliefEnhanced;
        settings.MacroReliefBoost = MacroReliefBoostSlider.Value;
        settings.NormalStrength = NormalStrengthSlider.Value;
        settings.HeightContrast = HeightContrastSlider.Value;
        settings.RoughnessMin = Math.Min(RoughnessMinSlider.Value, RoughnessMaxSlider.Value);
        settings.RoughnessMax = Math.Max(RoughnessMinSlider.Value, RoughnessMaxSlider.Value);
        settings.RoughnessBase = Math.Clamp(settings.RoughnessBase, settings.RoughnessMin, settings.RoughnessMax);
        settings.Metallic = MetallicSlider.Value;
        settings.ParallaxEnabled = ParallaxCheck.IsChecked == true;
        settings.ParallaxDepth = ParallaxDepthSlider.Value;
        return settings;
    }

    private void PbrSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        UpdateSliderLabels();
        if (!_applyingProfile) ResetPbrPreview();
    }

    private void ParallaxCheck_Changed(object sender, RoutedEventArgs e)
    {
        if (!_applyingProfile) ResetPbrPreview();
    }

    private void UpdateSliderLabels()
    {
        // WPF can fire ValueChanged while InitializeComponent is still constructing
        // controls in XAML order. AiStrengthSlider appears before the PBR section, so
        // the first event can arrive before NormalStrengthSlider and friends exist.
        // Never touch later controls until the entire window has been initialized.
        if (!IsInitialized ||
            AiStrengthText is null || AiStrengthSlider is null ||
            NormalStrengthText is null || NormalStrengthSlider is null ||
            HeightContrastText is null || HeightContrastSlider is null ||
            RoughnessText is null || RoughnessMinSlider is null || RoughnessMaxSlider is null ||
            MetallicText is null || MetallicSlider is null ||
            ParallaxDepthText is null || ParallaxDepthSlider is null ||
            MacroReliefBoostText is null || MacroReliefBoostSlider is null)
            return;

        AiStrengthText.Text = AiStrengthSlider.Value.ToString("0.00");
        NormalStrengthText.Text = NormalStrengthSlider.Value.ToString("0");
        HeightContrastText.Text = HeightContrastSlider.Value.ToString("0.00");
        RoughnessText.Text = $"{RoughnessMinSlider.Value:0.00} / {RoughnessMaxSlider.Value:0.00}";
        MetallicText.Text = MetallicSlider.Value.ToString("0.00");
        ParallaxDepthText.Text = ParallaxDepthSlider.Value.ToString("0.000");
        MacroReliefBoostText.Text = MacroReliefBoostSlider.Value.ToString("0.00");
    }

    private async Task BusyAsync(string message, Func<CancellationToken, Task> work)
    {
        if (_busyCts is not null) return;
        _busyCts = new CancellationTokenSource();
        BusyProgress.Visibility = Visibility.Visible;
        SetControlsEnabled(false);
        Status(message);

        try
        {
            await work(_busyCts.Token);
        }
        catch (OperationCanceledException)
        {
            Status("Cancelled.");
        }
        catch (Exception ex)
        {
            Status("Error.");
            MessageBox.Show(this, ex.ToString(), "DarkWolf PBR Studio V2.05.2", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            _busyCts.Dispose();
            _busyCts = null;
            BusyProgress.Visibility = Visibility.Collapsed;
            SetControlsEnabled(true);
        }
    }

    private void SetControlsEnabled(bool enabled)
    {
        OpenPk3Button.IsEnabled = enabled;
        RestoreButton.IsEnabled = enabled;
        AiNextButton.IsEnabled = enabled;
        TextureList.IsEnabled = enabled;
        BatchList.IsEnabled = enabled;
        VariantList.IsEnabled = enabled;
        MaterialProfileCombo.IsEnabled = enabled;
        GenerationModeCombo.IsEnabled = enabled;
        MacroReliefBoostSlider.IsEnabled = enabled;
    }

    private void SaveSettings()
    {
        _settings.StableDiffusionCliPath = SdCliPathBox.Text.Trim();
        _settings.StableDiffusionModelPath = SdModelPathBox.Text.Trim();
        _settings.StableDiffusionExtraArgs = SdExtraArgsBox.Text.Trim();
        _settings.AiStrength = AiStrengthSlider.Value;
        _settings.Save();
    }

    private void Status(string message) => StatusText.Text = message;
}
