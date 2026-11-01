# DarkWolf V4 diagnostic 1/2: read-only Windows screenshot and JSON collector
# Run immediately after DW_PS_V4_AUTOTEST.cfg on EACH map. No network upload.
$ErrorActionPreference = "Stop"
$names = @("DW_PS_V4_01_BASELINE.jpg","DW_PS_V4_02_LINKED_ONE.jpg",
           "DW_PS_V4_03_NEAREST_ONE.jpg","DW_PS_V4_04_TOP_THREE.jpg",
           "DW_PS_V4_05_RESTORED.jpg")
$needed = @{}
foreach($n in $names){$needed[$n.ToLowerInvariant()]=$true}
$found=@{}; $optional=@{}; $visited=@{}
$roots=New-Object 'System.Collections.Generic.List[string]'
$doc=[Environment]::GetFolderPath("MyDocuments")
$profileHome=[Environment]::GetFolderPath("UserProfile")
foreach($p in @($PSScriptRoot,$doc,$env:APPDATA,$env:LOCALAPPDATA,
  "$profileHome\Documents","$profileHome\OneDrive\Documents",
  "$profileHome\Saved Games","$env:LOCALAPPDATA\VirtualStore",
  $env:OneDrive,$env:OneDriveConsumer,$env:OneDriveCommercial,
  "C:\Return to Castle WolfensteinPBR")){
    if($p){$roots.Add($p)}
}
function Accept-File($item){
    if(-not $item -or $item.Length -lt 5){return}
    $name=$item.Name.ToLowerInvariant()
    if($script:needed.ContainsKey($name)){
        if(-not $script:found.ContainsKey($name) -or
           $item.LastWriteTimeUtc -gt $script:found[$name].LastWriteTimeUtc){
            $script:found[$name]=$item
        }
    } elseif($name -like 'dw_ps_v4_*_mode*.json' -or
             $name -eq 'dw_ps_v4_selection.cfg' -or
             $name -eq 'dw_ps_v4_autotest_console.txt'){
        if(-not $script:optional.ContainsKey($name) -or
           $item.LastWriteTimeUtc -gt $script:optional[$name].LastWriteTimeUtc){
            $script:optional[$name]=$item
        }
    }
}
function Search-Directory([string]$path,[bool]$recursive){
    if(-not $path){return}
    try{$path=[IO.Path]::GetFullPath($path)}catch{return}
    $key=($path+"|"+$recursive).ToLowerInvariant()
    if($script:visited.ContainsKey($key) -or
       -not (Test-Path -LiteralPath $path -PathType Container)){return}
    $script:visited[$key]=$true
    Write-Host ("Looking in: "+$path)
    foreach($filter in @("DW_PS_V4_*.jpg","dw_ps_v4_*.json",
                         "DW_PS_V4_SELECTION.cfg","DW_PS_V4_AUTOTEST_CONSOLE.txt")){
        try{
            $items=Get-ChildItem -LiteralPath $path -File -Filter $filter -Recurse:$recursive -Force -ErrorAction SilentlyContinue
            foreach($item in $items){Accept-File $item}
        }catch{}
    }
}
foreach($r in $roots){
    foreach($x in @("RTCW\main\screenshots","RTCW\Main\screenshots",
                     "main\screenshots","Main\screenshots","screenshots",
                     "RTCW\main","main","Main","RTCW\Main")){
        Search-Directory (Join-Path $r $x) $false
    }
}
foreach($r in @($PSScriptRoot,$doc,"$profileHome\Documents",$env:APPDATA,
                "$env:LOCALAPPDATA\VirtualStore",$env:OneDrive,
                "C:\Return to Castle WolfensteinPBR")){
    if($script:found.Count -eq 5 -and $script:optional.Count -ge 5){break}
    Search-Directory $r $true
}
if($found.Count -lt 5){
    Write-Host ("Only "+$found.Count+"/5 screenshots found. Searching user home...")
    Search-Directory $profileHome $true
}
if($found.Count -lt 5){
    $extra=Read-Host "Optional: enter game folder containing screenshots (Enter to skip)"
    if($extra){Search-Directory $extra $true}
}
$stage=Join-Path $env:TEMP ("DW_PS_V4_"+[guid]::NewGuid().ToString("N"))
New-Item -Path $stage -ItemType Directory -Force | Out-Null
$status=New-Object 'System.Collections.Generic.List[string]'
$csv=New-Object 'System.Collections.Generic.List[string]'
$csv.Add("name,sha256,bytes,source_path")
foreach($name in $names){
    $key=$name.ToLowerInvariant()
    if($found.ContainsKey($key)){
        $item=$found[$key];$dest=Join-Path $stage $name
        Copy-Item -LiteralPath $item.FullName -Destination $dest -Force
        $hash=(Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant()
        $stream=[IO.File]::OpenRead($dest)
        try{$b1=$stream.ReadByte();$b2=$stream.ReadByte()}finally{$stream.Dispose()}
        if($b1 -ne 255 -or $b2 -ne 216){$status.Add("BAD_JPEG_MAGIC "+$name)}
        $status.Add("FOUND "+$name+" "+$item.FullName)
        $csv.Add('"' + $name + '","' + $hash + '",' + $item.Length + ',"' +
                 $item.FullName.Replace('"','""') + '"')
    } else {$status.Add("MISSING "+$name)}
}
foreach($key in $optional.Keys){
    $item=$optional[$key]
    Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $stage $item.Name) -Force
    $status.Add("TELEMETRY "+$item.Name+" "+$item.FullName)
}
$map="unknown"
$mode0=@($optional.Keys | Where-Object {$_ -like 'dw_ps_v4_*_mode0.json'})
if($mode0.Count -gt 0){
    $latest=$mode0 | Sort-Object { $optional[$_].LastWriteTimeUtc } -Descending | Select-Object -First 1
    try{
        $j=Get-Content -LiteralPath $optional[$latest].FullName -Raw | ConvertFrom-Json
        if($j.map){$map=[string]$j.map}
        $status.Add("AUTO_MAP "+$map)
        $status.Add("AUTO_SELECTED_SOURCE_INDEX "+$j.selectedSourceIndex)
        $status.Add("AUTO_SELECTED_SURFACES "+($j.selectedSurfaceIds -join ","))
        $status.Add("AUTO_SOURCE_LINKED "+$j.selectedLinked)
    }catch{$status.Add("WARNING: telemetry JSON parse failed "+$_.Exception.Message)}
}
$stamp=Get-Date -Format "yyyyMMdd_HHmmss"
$status.Add("IMAGES_FOUND "+$found.Count+"/5")
$status.Add("SEARCHED_DIRS "+$visited.Count)
$status.Add("NETWORK_UPLOAD NO")
$status | Set-Content (Join-Path $stage "DW_PS_V4_COLLECTION_STATUS.txt") -Encoding UTF8
$csv | Set-Content (Join-Path $stage "DW_PS_V4_SHA256.csv") -Encoding UTF8
$map=$map -replace '[^a-zA-Z0-9_-]','_'
$out=Join-Path $PSScriptRoot ("DW_PS_V4_"+$map+"_"+$stamp+".zip")
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $out -CompressionLevel Optimal -Force
Remove-Item -LiteralPath $stage -Force -Recurse -ErrorAction SilentlyContinue
Write-Host ("RESULTS: "+$found.Count+"/5 screenshots; ZIP: "+$out)
Write-Host "Attach this ZIP to the current chat. It does not upload itself."
if($found.Count -eq 5){exit 0}else{exit 2}
