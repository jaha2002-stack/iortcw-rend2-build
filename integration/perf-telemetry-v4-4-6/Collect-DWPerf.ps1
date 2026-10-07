param()

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Out = Join-Path $Root ("DWPerfTelemetry_" + $Stamp)
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$Main = Join-Path $Root "Main"
$Qconsole = Join-Path $Main "qconsole.log"

function Copy-IfExists([string]$Path, [string]$DestName) {
    if (Test-Path $Path) {
        Copy-Item -Force $Path (Join-Path $Out $DestName)
    }
}

Copy-IfExists $Qconsole "qconsole.log"
Copy-IfExists (Join-Path $Main "wolfconfig.cfg") "wolfconfig_after_test.cfg"
Copy-IfExists (Join-Path $Main "wolfconfig.dwperf_backup.cfg") "wolfconfig_before_test.cfg"
Copy-IfExists (Join-Path $Main "UNIFIED_PRODUCTION.cfg") "UNIFIED_PRODUCTION.cfg"
Copy-IfExists (Join-Path $Root "README_DWPERF_RU.txt") "README_DWPERF_RU.txt"

try {
    Get-CimInstance Win32_Processor |
        Select-Object Name, Manufacturer, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed |
        Format-List | Out-File -Encoding utf8 (Join-Path $Out "cpu.txt")
} catch { $_ | Out-File -Encoding utf8 (Join-Path $Out "cpu_error.txt") }

try {
    Get-CimInstance Win32_VideoController |
        Select-Object Name, DriverVersion, DriverDate, AdapterRAM, VideoProcessor, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate |
        Format-List | Out-File -Encoding utf8 (Join-Path $Out "gpu.txt")
} catch { $_ | Out-File -Encoding utf8 (Join-Path $Out "gpu_error.txt") }

try {
    Get-CimInstance Win32_OperatingSystem |
        Select-Object Caption, Version, BuildNumber, OSArchitecture, TotalVisibleMemorySize, FreePhysicalMemory |
        Format-List | Out-File -Encoding utf8 (Join-Path $Out "os.txt")
} catch { $_ | Out-File -Encoding utf8 (Join-Path $Out "os_error.txt") }

try {
    powercfg /getactivescheme | Out-File -Encoding utf8 (Join-Path $Out "power_plan.txt")
} catch {}

if (Test-Path $Qconsole) {
    $Lines = Get-Content $Qconsole
    $Perf = $Lines | Where-Object { $_ -match '^DWPERF_' }
    $Perf | Set-Content -Encoding utf8 (Join-Path $Out "dwperf_raw.log")
    $Perf | Where-Object { $_ -match '^DWPERF_FRAME ' } | Set-Content -Encoding utf8 (Join-Path $Out "dwperf_frames.log")
    $Perf | Where-Object { $_ -match '^DWPERF_PROBE ' } | Set-Content -Encoding utf8 (Join-Path $Out "dwperf_probes.log")
    $Perf | Where-Object { $_ -match '^DWPERF_CFG ' } | Set-Content -Encoding utf8 (Join-Path $Out "dwperf_config.log")

    $Rows = @()
    foreach ($Line in ($Perf | Where-Object { $_ -match '^DWPERF_FRAME ' })) {
        $H = @{}
        foreach ($M in [regex]::Matches($Line, '([A-Za-z0-9_]+)=([^\s]+)')) {
            $H[$M.Groups[1].Value] = $M.Groups[2].Value
        }
        if ($H.ContainsKey("wall_ms") -and $H.ContainsKey("probe") -and [int]$H["probe"] -eq 0 -and [int]$H["wall_ms"] -gt 0) {
            $Rows += [pscustomobject]@{
                map = $H["map"]
                wall_ms = [double]$H["wall_ms"]
                frontend_ms = if ($H.ContainsKey("frontend_ms")) {[double]$H["frontend_ms"]} else {0}
                backend_ms = if ($H.ContainsKey("backend_ms")) {[double]$H["backend_ms"]} else {0}
                staticpromote_ms = if ($H.ContainsKey("staticpromote_ms")) {[double]$H["staticpromote_ms"]} else {0}
                dshadow_front_ms = if ($H.ContainsKey("dshadow_front_ms")) {[double]$H["dshadow_front_ms"]} else {0}
                dshadow_faces = if ($H.ContainsKey("dshadow_faces")) {[int]$H["dshadow_faces"]} else {0}
                fbo_changes = if ($H.ContainsKey("fbo_changes")) {[int]$H["fbo_changes"]} else {0}
                fastblits = if ($H.ContainsKey("fastblits")) {[int]$H["fastblits"]} else {0}
            }
        }
    }

    function Percentile($Values, [double]$P) {
        if (!$Values -or $Values.Count -eq 0) { return 0 }
        $S = @($Values | Sort-Object)
        $Index = [math]::Ceiling(($P / 100.0) * $S.Count) - 1
        if ($Index -lt 0) { $Index = 0 }
        if ($Index -ge $S.Count) { $Index = $S.Count - 1 }
        return [double]$S[$Index]
    }

    $Summary = @()
    $Summary += "DarkWolf ioRTCW Rend2 v4.4.6 Full Performance Telemetry"
    $Summary += "Generated: $(Get-Date -Format o)"
    $Summary += "Normal sampled frames: $($Rows.Count)"
    if ($Rows.Count -gt 0) {
        $Vals = @($Rows | ForEach-Object {$_.wall_ms})
        $Avg = ($Vals | Measure-Object -Average).Average
        $P50 = Percentile $Vals 50
        $P95 = Percentile $Vals 95
        $P99 = Percentile $Vals 99
        $Summary += ("ALL p50={0:N2}ms p95={1:N2}ms p99={2:N2}ms avg={3:N2}ms approx_avg_fps={4:N1}" -f $P50,$P95,$P99,$Avg,(1000.0/$Avg))
        foreach ($G in ($Rows | Group-Object map)) {
            $MV = @($G.Group | ForEach-Object {$_.wall_ms})
            $MA = ($MV | Measure-Object -Average).Average
            $Summary += ("MAP {0} samples={1} p50={2:N2}ms p95={3:N2}ms p99={4:N2}ms avg={5:N2}ms approx_avg_fps={6:N1}" -f
                $G.Name,$MV.Count,(Percentile $MV 50),(Percentile $MV 95),(Percentile $MV 99),$MA,(1000.0/$MA))
        }
    }
    $ProbeCount = @($Perf | Where-Object { $_ -match '^DWPERF_PROBE ' }).Count
    $Summary += "Serialized GPU probe frames: $ProbeCount"
    $Summary += "IMPORTANT: probe frames contain qglFinish synchronization and are excluded from normal frame-time summary."
    $Summary | Set-Content -Encoding utf8 (Join-Path $Out "SUMMARY.txt")
}

try {
    $DxPath = Join-Path $Out "dxdiag.txt"
    $DxArgs = '/dontskip /t "' + $DxPath + '"'
    Start-Process -FilePath "dxdiag.exe" -ArgumentList $DxArgs -Wait -WindowStyle Hidden
} catch {}

$Zip = Join-Path $Root ("DWPerfTelemetry_" + $Stamp + ".zip")
if (Test-Path $Zip) { Remove-Item -Force $Zip }
Compress-Archive -Path (Join-Path $Out "*") -DestinationPath $Zip -Force
Write-Host ""
Write-Host "Telemetry package created:"
Write-Host $Zip
Write-Host "Send this ZIP to ChatGPT for analysis."
