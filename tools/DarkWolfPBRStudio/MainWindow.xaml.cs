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
    private readonly string _sessionDir;

    private List<TextureAsset> _allTextures = new();
    private string? _pk3Path;
    private TextureAsset? _asset;
    private BitmapSource? _original;
    private BitmapSource? _current;
    private PbrResult? _pbrResult;
    private MaterialAnalysis? _analysis;
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
        MaterialProfileCombo.ItemsSource = Enum.GetValues<MaterialKind>();
        MaterialProfileCombo.SelectedItem = MaterialKind.Auto;

        SdCliPathBox.Text = !string.IsNullOrWhiteSpace(_settings.StableDiffusionCliPath)
            ? _settings.StableDiffusionCliPath
            : (_sd.IsBundledAvailable ? _sd.BundledCliPath : "");
        SdModelPathBox.Text = _settings.StableDiffusionModelPath;
        SdExtraArgsBox.Text = _settings.StableDiffusionExtraArgs;
        AiStrengthSlider.Value = _settings.AiStrength;

        ApplyProfile(MaterialProfile.For(MaterialKind.GenericDielectric), keepComboSelection: true);
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
        if (_pk3Path is null || TextureList.SelectedItem is not TextureAsset asset) return;
        _asset = asset;

        await BusyAsync($"Loading and analyzing {asset.EntryPath}…", async ct =>
        {
            byte[] bytes = await Task.Run(() => _pk3.ReadEntry(_pk3Path, asset.EntryPath), ct);
            BitmapSource bmp = await Dispatcher.InvokeAsync(() => ImageService.Load(bytes, asset.Extension));
            string originalPath = Path.Combine(_sessionDir, $"original_{Guid.NewGuid():N}.png");
            await Dispatcher.InvokeAsync(() => ImageService.SavePng(bmp, originalPath));

            bool hasDef = await Task.Run(() => _pk3.HasMaterialDefinitionInDirectory(_pk3Path, asset.ShaderName), ct);
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
                MaterialStatusText.Text = hasDef ? "Material: scripted" : "Material: implicit";
                ExplicitMtrCheck.IsChecked = !hasDef;
                CompatibilityHintText.Text = hasDef
                    ? "Existing scripted material detected. Safe default: export maps/BaseColor only. Enable explicit MTR only after reviewing the original shader stages."
                    : "Implicit texture: explicit BSP PBR MTR is appropriate and enables the complete Normal/ORM/lightmap path.";

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

    private void MaterialProfileCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_applyingProfile || MaterialProfileCombo.SelectedItem is not MaterialKind selected) return;

        MaterialKind actual = selected == MaterialKind.Auto
            ? (_analysis?.Kind ?? MaterialKind.GenericDielectric)
            : selected;

        ApplyProfile(MaterialProfile.For(actual), keepComboSelection: true);
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

        await BusyAsync("PBR V2: decomposing Height / Normal / AO / Roughness / Metallic…", async ct =>
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
        if (_pbrResult is null)
        {
            MessageBox.Show(this, "Generate the PBR3 material first.");
            return;
        }

        bool explicitMtr = ExplicitMtrCheck.IsChecked == true;
        if (_hasMaterialDefinition && explicitMtr)
        {
            var answer = MessageBox.Show(this,
                "A scripted material with this shader name was detected. An explicit replacement MTR may alter original stages. Continue anyway?",
                "Compatibility warning", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (answer != MessageBoxResult.Yes) return;
        }

        string stem = Path.GetFileNameWithoutExtension(_asset.DisplayName);
        var d = new SaveFileDialog
        {
            Filter = "RTCW PK3 (*.pk3)|*.pk3",
            FileName = $"zzz_dw_{stem}_pbr3_v2.pk3"
        };
        if (d.ShowDialog(this) != true) return;

        try
        {
            var settings = ReadPbrSettings();
            PbrExportService.Export(
                d.FileName,
                _asset,
                _current,
                IncludeBaseColorCheck.IsChecked == true,
                _pbrResult,
                explicitMtr,
                settings,
                _analysis,
                GetSelectedVariant()?.Name ?? "Original");

            string parallax = settings.ParallaxEnabled
                ? $"
{_asset.ShaderName}_nh.tga
{_asset.ShaderName}_h.tga"
                : "";

            Status($"Exported: {d.FileName}");
            MessageBox.Show(this,
                "PBR Studio V2 override PK3 created. The source PK3 was not modified.

" +
                $"{_asset.ShaderName}_n.tga
{_asset.ShaderName}_orm.tga{parallax}

" +
                _pbrResult.Report.Summary,
                "Export complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.ToString(), "Export failed");
        }
    }

    private PbrSettings ReadPbrSettings()
    {
        MaterialKind selected = MaterialProfileCombo.SelectedItem is MaterialKind k ? k : MaterialKind.Auto;
        MaterialKind actual = selected == MaterialKind.Auto
            ? (_analysis?.Kind ?? MaterialKind.GenericDielectric)
            : selected;

        var settings = PbrSettings.FromProfile(MaterialProfile.For(actual));
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
        if (AiStrengthText is null) return;
        AiStrengthText.Text = AiStrengthSlider.Value.ToString("0.00");
        NormalStrengthText.Text = NormalStrengthSlider.Value.ToString("0");
        HeightContrastText.Text = HeightContrastSlider.Value.ToString("0.00");
        RoughnessText.Text = $"{RoughnessMinSlider.Value:0.00} / {RoughnessMaxSlider.Value:0.00}";
        MetallicText.Text = MetallicSlider.Value.ToString("0.00");
        ParallaxDepthText.Text = ParallaxDepthSlider.Value.ToString("0.000");
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
            MessageBox.Show(this, ex.ToString(), "DarkWolf PBR Studio V2", MessageBoxButton.OK, MessageBoxImage.Error);
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
        VariantList.IsEnabled = enabled;
        MaterialProfileCombo.IsEnabled = enabled;
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
