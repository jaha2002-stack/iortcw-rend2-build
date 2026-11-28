param([string]$HomePath)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Game = Join-Path $Root 'ioWolfSP_Diagnostics.x64.exe'
if (!(Test-Path -LiteralPath $Game -PathType Leaf)) {
    throw 'Extract the full telemetry ZIP before starting.'
}

if (!$HomePath) {
    $candidates = @('DW_IFLC_Clean_Home', 'DW_TM_Fidelity_FINAL_Clean_Home', 'DW_September_FourWeek_Home') |
        ForEach-Object { Join-Path $Root $_ } |
        Where-Object { Test-Path -LiteralPath $_ -PathType Container }
    if (@($candidates).Count -eq 1) { $HomePath = @($candidates)[0] }
    else { $HomePath = (Read-Host 'Enter the fs_homepath used by your normal game launch').Trim('"') }
}
if (!$HomePath -or !(Test-Path -LiteralPath $HomePath -PathType Container)) {
    throw 'Select an existing game home folder to keep its graphics settings and saves.'
}
$GameHome = (Resolve-Path -LiteralPath $HomePath).Path.TrimEnd('\')
$LogRoot = Join-Path $Root 'DarkWolf_Performance_Logs'
$Session = Join-Path $LogRoot ('capture-{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'), ([guid]::NewGuid().ToString('N').Substring(0, 8)))
New-Item -ItemType Directory -Path $Session -Force | Out-Null
$Started = Get-Date
$Utc = $Started.ToUniversalTime().ToString('o')
$env:DARKWOLF_PERF_DIR = $Session
$launch = ('+set fs_basepath "{0}" +set fs_homepath "{1}" +set cl_renderer rend2 +set r_renderer rend2 +set com_recommendedSet 1' -f $Root, $GameHome)
$proc = Start-Process -FilePath $Game -ArgumentList $launch -WorkingDirectory $Root -PassThru
Remove-Item Env:DARKWOLF_PERF_DIR
"start_utc=`t$Utc`r`npid=`t$($proc.Id)" | Set-Content -LiteralPath (Join-Path $Session 'session.txt') -Encoding UTF8
"elapsed_s`tworking_set_bytes`tprivate_bytes`tprocess_cpu_seconds" | Set-Content -LiteralPath (Join-Path $Session 'memory.tsv') -Encoding ASCII
"elapsed_s`tmodule`tbase_hex`tsize_bytes" | Set-Content -LiteralPath (Join-Path $Session 'modules.tsv') -Encoding UTF8
$seen = @{}
$everSampled = $false
$timer = [Diagnostics.Stopwatch]::StartNew()
Write-Host "Recording to $Session"
while (!$proc.WaitForExit(1000)) {
    $elapsed = [int]$timer.Elapsed.TotalSeconds
    try {
        $proc.Refresh()
        "${elapsed}`t$($proc.WorkingSet64)`t$($proc.PrivateMemorySize64)`t$([int]$proc.TotalProcessorTime.TotalSeconds)" |
            Add-Content -LiteralPath (Join-Path $Session 'memory.tsv') -Encoding ASCII
        if (!$everSampled -or ($elapsed % 5) -eq 0) {
            foreach ($module in $proc.Modules) {
                $key = '{0}:{1:X}' -f $module.ModuleName, $module.BaseAddress.ToInt64()
                if (!$seen.ContainsKey($key)) {
                    $seen[$key] = $true
                    "{0}`t{1}`t{2:X}`t{3}" -f $elapsed, $module.ModuleName, $module.BaseAddress.ToInt64(), $module.ModuleMemorySize |
                        Add-Content -LiteralPath (Join-Path $Session 'modules.tsv') -Encoding UTF8
                }
            }
            $everSampled = $true
        }
    } catch {
        if ($proc.HasExited) { break }
    }
}
"stop_utc=`t$([DateTime]::UtcNow.ToString('o'))`r`nexit_dec=`t$($proc.ExitCode)`r`nexit_hex=`t$($proc.ExitCode.ToString('X8'))" |
    Add-Content -LiteralPath (Join-Path $Session 'session.txt') -Encoding UTF8
Start-Sleep -Seconds 2
$out = Join-Path $Session 'windows-events.tsv'
"utc`tprovider`tid`tfields" | Set-Content -LiteralPath $out -Encoding UTF8
foreach ($event in (Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000; StartTime=$Started} -ErrorAction SilentlyContinue)) {
    $xml = [xml]$event.ToXml()
    $data = @{}
    foreach ($item in $xml.Event.EventData.Data) { $data[$item.Name] = [string]$item.'#text' }
    if ($data['AppName'] -ne 'ioWolfSP_Diagnostics.x64.exe') { continue }
    if ($data['ProcessId'] -and $data['ProcessId'] -ne ('0x{0:x}' -f $proc.Id)) { continue }
    $fields = @('AppName', 'ModuleName', 'ExceptionCode', 'FaultingOffset', 'ProcessId') |
        ForEach-Object { "$_=$($data[$_])" }
    "$($event.TimeCreated.ToUniversalTime().ToString('o'))`t$($event.ProviderName)`t$($event.Id)`t$($fields -join ';')" |
        Add-Content -LiteralPath $out -Encoding UTF8
}
foreach ($event in (Get-WinEvent -FilterHashtable @{LogName='System'; Id=4101; StartTime=$Started} -ErrorAction SilentlyContinue)) {
    "$($event.TimeCreated.ToUniversalTime().ToString('o'))`t$($event.ProviderName)`t$($event.Id)`tdisplay_driver_reset" |
        Add-Content -LiteralPath $out -Encoding UTF8
}
Write-Host "Capture complete. Send this folder: $Session"
