param(
    [Parameter(Mandatory=$true)]
    [string]$RtcwMainPath,

    [string]$OutputDirectory = ".\\rtcw-testlab-upload",

    [int]$PartSizeMiB = 500
)

$ErrorActionPreference = "Stop"

$main = (Resolve-Path $RtcwMainPath).Path
if (-not (Test-Path (Join-Path $main "pak0.pk3"))) {
    $pak0 = Get-ChildItem -Path $main -File | Where-Object { $_.Name -ieq "pak0.pk3" } | Select-Object -First 1
    if (-not $pak0) {
        throw "pak0.pk3 was not found in $main"
    }
}

$out = [System.IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path $out) {
    Remove-Item -Recurse -Force $out
}
New-Item -ItemType Directory -Path $out | Out-Null

$stage = Join-Path $out "stage"
$stageMain = Join-Path $stage "Main"
New-Item -ItemType Directory -Path $stageMain -Force | Out-Null

$pk3 = Get-ChildItem -Path $main -File | Where-Object { $_.Extension -ieq ".pk3" } | Sort-Object Name
if ($pk3.Count -eq 0) {
    throw "No PK3 files were found in $main"
}
foreach ($f in $pk3) {
    Copy-Item -LiteralPath $f.FullName -Destination $stageMain
}

$zip = Join-Path $out "rtcw-assets.zip"
Compress-Archive -Path $stageMain -DestinationPath $zip -CompressionLevel Optimal

$sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash.ToLowerInvariant()
"$sha  rtcw-assets.zip" | Set-Content -NoNewline -Encoding ascii (Join-Path $out "rtcw-assets.sha256")

$partSize = [int64]$PartSizeMiB * 1MB
$buffer = New-Object byte[] (4MB)
$input = [System.IO.File]::OpenRead($zip)
try {
    $part = 1
    while ($input.Position -lt $input.Length) {
        $partPath = Join-Path $out ("rtcw-assets.zip.part{0:D3}" -f $part)
        $output = [System.IO.File]::Create($partPath)
        try {
            $written = [int64]0
            while ($written -lt $partSize -and $input.Position -lt $input.Length) {
                $want = [int][Math]::Min($buffer.Length, $partSize - $written)
                $read = $input.Read($buffer, 0, $want)
                if ($read -le 0) { break }
                $output.Write($buffer, 0, $read)
                $written += $read
            }
        }
        finally {
            $output.Dispose()
        }
        $part++
    }
}
finally {
    $input.Dispose()
}

Remove-Item -Recurse -Force $stage
Remove-Item -Force $zip

Write-Host ""
Write-Host "DarkWolf RTCW TestLab upload package created:"
Get-ChildItem -Path $out -File | Sort-Object Name | ForEach-Object {
    Write-Host ("  {0}  {1:N1} MiB" -f $_.Name, ($_.Length / 1MB))
}
Write-Host ""
Write-Host "Upload ALL files above to the private GitHub Release."
