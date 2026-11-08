using System.Diagnostics;
using System.Text;

namespace DarkWolfPBRStudio.Services;

public static class ProcessRunner
{
    public static async Task<string> RunAsync(string exe, string arguments, string? workingDirectory = null, CancellationToken ct = default)
    {
        var psi = new ProcessStartInfo
        {
            FileName = exe,
            Arguments = arguments,
            WorkingDirectory = workingDirectory ?? Path.GetDirectoryName(exe) ?? Environment.CurrentDirectory,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };

        using var p = new Process { StartInfo = psi };
        var log = new StringBuilder();
        p.OutputDataReceived += (_, e) => { if (e.Data is not null) log.AppendLine(e.Data); };
        p.ErrorDataReceived += (_, e) => { if (e.Data is not null) log.AppendLine(e.Data); };
        if (!p.Start()) throw new InvalidOperationException($"Could not start {exe}");
        p.BeginOutputReadLine();
        p.BeginErrorReadLine();

        await p.WaitForExitAsync(ct);
        if (p.ExitCode != 0)
            throw new InvalidOperationException($"{Path.GetFileName(exe)} failed with exit code {p.ExitCode}.\n{log}");
        return log.ToString();
    }

    public static string Q(string value) => "\"" + value.Replace("\"", "\\\"") + "\"";
}
