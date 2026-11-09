using System.Text;
using System.Windows;
using System.Windows.Threading;

namespace DarkWolfPBRStudio;

public partial class App : Application
{
    private static string DiagnosticsDir
        => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DarkWolfPBRStudio");

    private static string StartupLogPath => Path.Combine(DiagnosticsDir, "startup.log");
    private static string CrashLogPath => Path.Combine(DiagnosticsDir, "startup-crash.log");

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        if (e.Args.Any(x => x.Equals("--lab-author", StringComparison.OrdinalIgnoreCase)))
        {
            try
            {
                int rc = await V206LabRunner.RunAsync(e.Args);
                Shutdown(rc);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine(ex);
                try
                {
                    Directory.CreateDirectory(DiagnosticsDir);
                    File.WriteAllText(Path.Combine(DiagnosticsDir, "v206-lab-error.log"), ex.ToString(), Encoding.UTF8);
                }
                catch { }
                Shutdown(-10);
            }
            return;
        }

        Directory.CreateDirectory(DiagnosticsDir);
        SafeWrite(StartupLogPath,
            $"[{DateTime.Now:O}] DarkWolf PBR Studio V2.06 starting\r\n" +
            $"OS={Environment.OSVersion}\r\n" +
            $"64bitProcess={Environment.Is64BitProcess}\r\n" +
            $"BaseDirectory={AppContext.BaseDirectory}\r\n");

        DispatcherUnhandledException += OnDispatcherUnhandledException;
        AppDomain.CurrentDomain.UnhandledException += OnDomainUnhandledException;

        try
        {
            var window = new MainWindow();
            MainWindow = window;
            window.Show();
            SafeAppend(StartupLogPath, $"[{DateTime.Now:O}] MainWindow shown successfully.\r\n");
        }
        catch (Exception ex)
        {
            ReportStartupFailure("MainWindow construction/show failed", ex);
            Shutdown(-1);
        }
    }

    private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        ReportStartupFailure("DispatcherUnhandledException", e.Exception);
        e.Handled = true;
        Shutdown(-2);
    }

    private static void OnDomainUnhandledException(object? sender, UnhandledExceptionEventArgs e)
    {
        if (e.ExceptionObject is Exception ex)
            SafeAppend(CrashLogPath, FormatFailure("AppDomain.UnhandledException", ex));
        else
            SafeAppend(CrashLogPath, $"[{DateTime.Now:O}] AppDomain.UnhandledException: {e.ExceptionObject}\r\n");
    }

    private static void ReportStartupFailure(string phase, Exception ex)
    {
        string text = FormatFailure(phase, ex);
        SafeAppend(CrashLogPath, text);

        try
        {
            MessageBox.Show(
                text + "\r\nCrash log:\r\n" + CrashLogPath,
                "DarkWolf PBR Studio V2.06 startup error",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
        }
        catch { }
    }

    private static string FormatFailure(string phase, Exception ex)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"[{DateTime.Now:O}] {phase}");
        sb.AppendLine(ex.ToString());

        Exception? inner = ex.InnerException;
        int level = 1;
        while (inner is not null)
        {
            sb.AppendLine($"--- InnerException {level} ---");
            sb.AppendLine(inner.ToString());
            inner = inner.InnerException;
            level++;
        }
        return sb.ToString();
    }

    private static void SafeWrite(string path, string text)
    {
        try { File.WriteAllText(path, text, Encoding.UTF8); } catch { }
    }

    private static void SafeAppend(string path, string text)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.AppendAllText(path, text, Encoding.UTF8);
        }
        catch { }
    }
}
