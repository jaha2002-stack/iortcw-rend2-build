using DarkWolfPBRStudio.Models;
using DarkWolfPBRStudio.Services;
using Microsoft.Win32;
using System.Collections.ObjectModel;
using System.Diagnostics;
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
    private BitmapSource? _normal;
    private BitmapSource? _orm;
    private string? _aiSourcePath;
    private bool _hasMaterialDefinition;
    private CancellationTokenSource? _busyCts;

    public MainWindow()
    {
        InitializeComponent();
        _sessionDir = Path.Combine(Path.GetTempPath(), "DarkWolfPBRStudio", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_sessionDir);

        VariantList.ItemsSource = _variants;
        SdCliPathBox.Text = _settings.StableDiffusionCliPath;
        SdModelPathBox.Text = _settings.StableDiffusionModelPath;
        SdExtraArgsBox.Text = _settings.StableDiffusionExtraArgs;
        AiStrengthSlider.Value = _settings.AiStrength;
        UpdateSliderLabels();

        Status($"Ready. Real-ESRGAN: {(_restore.IsAvailable ? "bundled" : "not found in this build")}.");
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

        await BusyAsync($"Loading {asset.EntryPath}…", async ct =>
        {
            byte[] bytes = await Task.Run(() => _pk3.ReadEntry(_pk3Path, asset.EntryPath), ct);
            BitmapSource bmp = await Dispatcher.InvokeAsync(() => ImageService.Load(bytes, asset.Extension));
            string originalPath = Path.Combine(_sessionDir, $"original_{Guid.NewGuid():N}.png");
            ImageService.SavePng(bmp, originalPath);

            bool hasDef = await Task.Run(() => _pk3.HasMaterialDefinitionInDirectory(_pk3Path, asset.ShaderName), ct);

            await Dispatcher.InvokeAsync(() =>
            {
                _original = _current = bmp;
                _normal = _orm = null;
                OriginalImage.Source = bmp;
                CurrentImage.Source = bmp;
                NormalImage.Source = null;
                OrmImage.Source = null;
                _variants.Clear();
                _variants.Add(new VariantItem { Name = "Original", FilePath = originalPath, Kind = "Original" });
                VariantList.SelectedIndex = 0;
                _aiSourcePath = originalPath;
                _hasMaterialDefinition = hasDef;
                MaterialStatusText.Text = hasDef ? "Material: scripted" : "Material: implicit";
                ExplicitMtrCheck.IsChecked = !hasDef;
                CompatibilityHintText.Text = hasDef
                    ? "Existing material definition detected in the PK3 directory. Safe default: export maps/basecolor only; do not override the scripted material unless you deliberately enable explicit MTR."
                    : "No scripted material definition detected. Explicit BSP PBR MTR is appropriate for this implicit texture.";
                Status($"{asset.EntryPath} — {bmp.PixelWidth}×{bmp.PixelHeight}.");
            });
        });
    }

    private async void RestoreButton_Click(object sender, RoutedEventArgs e)
    {
        if (_current is null) { MessageBox.Show(this, "Select a texture first."); return; }
        if (!_restore.IsAvailable)
        {
            MessageBox.Show(this, "Real-ESRGAN backend is not present in this development build. Use the packaged Windows artifact where it is bundled.", "AI backend");
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
                var item = new VariantItem { Name = $"AI Restore ×4 #{_variants.Count}", FilePath = output, Kind = "AI Restoration" };
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
        Status($"AI source fixed to: {v.Name}. Next will generate alternatives from this source.");
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
            _normal = _orm = null;
            NormalImage.Source = OrmImage.Source = null;
            Status($"Selected variant: {v.Name}.");
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "Variant load error"); }
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

        await BusyAsync("Generating Normal + ORM for r_pbr 3…", async ct =>
        {
            var result = await Task.Run(() => PbrGenerator.Generate(source, settings), ct);
            await Dispatcher.InvokeAsync(() =>
            {
                _normal = result.Normal;
                _orm = result.Orm;
                NormalImage.Source = _normal;
                OrmImage.Source = _orm;
                Status("PBR maps generated: Normal + ORM (R=AO, G=Roughness, B=Metallic).");
            });
        });
    }

    private void ExportButton_Click(object sender, RoutedEventArgs e)
    {
        if (_asset is null || _current is null) { MessageBox.Show(this, "Select a texture first."); return; }
        if (_normal is null || _orm is null)
        {
            MessageBox.Show(this, "Generate Normal + ORM first.");
            return;
        }

        bool explicitMtr = ExplicitMtrCheck.IsChecked == true;
        if (_hasMaterialDefinition && explicitMtr)
        {
            var answer = MessageBox.Show(this,
                "A scripted material with this shader name was detected. An explicit replacement MTR may change its original stages. Continue anyway?",
                "Compatibility warning", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (answer != MessageBoxResult.Yes) return;
        }

        string stem = Path.GetFileNameWithoutExtension(_asset.DisplayName);
        var d = new SaveFileDialog
        {
            Filter = "RTCW PK3 (*.pk3)|*.pk3",
            FileName = $"zzz_dw_{stem}_pbr3.pk3"
        };
        if (d.ShowDialog(this) != true) return;

        try
        {
            PbrExportService.Export(
                d.FileName, _asset, _current, IncludeBaseColorCheck.IsChecked == true,
                _normal, _orm, explicitMtr, ReadPbrSettings(),
                GetSelectedVariant()?.Name ?? "Original");
            Status($"Exported: {d.FileName}");
            MessageBox.Show(this,
                "PBR override PK3 created. The original PK3 was not modified.\n\n" +
                $"{_asset.ShaderName}_n.tga\n{_asset.ShaderName}_orm.tga",
                "Export complete", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (Exception ex) { MessageBox.Show(this, ex.ToString(), "Export failed"); }
    }

    private PbrSettings ReadPbrSettings() => new()
    {
        NormalStrength = NormalStrengthSlider.Value,
        RoughnessMin = Math.Min(RoughnessMinSlider.Value, RoughnessMaxSlider.Value),
        RoughnessMax = Math.Max(RoughnessMinSlider.Value, RoughnessMaxSlider.Value),
        RoughnessBase = Math.Clamp((RoughnessMinSlider.Value + RoughnessMaxSlider.Value) * 0.5 - 0.06, 0.2, 0.95),
        AoFloor = 0.46
    };

    private void AiStrengthSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e) => UpdateSliderLabels();
    private void NormalStrengthSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e) => UpdateSliderLabels();
    private void RoughnessSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e) => UpdateSliderLabels();

    private void UpdateSliderLabels()
    {
        if (AiStrengthText is null) return;
        AiStrengthText.Text = AiStrengthSlider.Value.ToString("0.00");
        NormalStrengthText.Text = NormalStrengthSlider.Value.ToString("0");
        RoughnessMinText.Text = RoughnessMinSlider.Value.ToString("0.00");
        RoughnessMaxText.Text = RoughnessMaxSlider.Value.ToString("0.00");
    }

    private async Task BusyAsync(string message, Func<CancellationToken, Task> work)
    {
        if (_busyCts is not null) return;
        _busyCts = new CancellationTokenSource();
        BusyProgress.Visibility = Visibility.Visible;
        SetControlsEnabled(false);
        Status(message);
        try { await work(_busyCts.Token); }
        catch (OperationCanceledException) { Status("Cancelled."); }
        catch (Exception ex)
        {
            Status("Error.");
            MessageBox.Show(this, ex.ToString(), "DarkWolf PBR Studio", MessageBoxButton.OK, MessageBoxImage.Error);
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
