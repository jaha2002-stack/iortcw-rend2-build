#!/usr/bin/env python3
"""Package exact accepted SP archive with one replacement renderer and a self-running test."""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--base-zip', type=Path,required=True)
p.add_argument('--renderer', type=Path,required=True)
p.add_argument('--manifest', type=Path,required=True)
p.add_argument('--out', type=Path,required=True)
a=p.parse_args()
sha=lambda b:hashlib.sha256(b).hexdigest()
EXPECTED_BASE_ZIP='cabbf853370ba544cc13eca4467dba3be855cf9525b36bd610620e1777a2ead5'
EXPECTED_RENDERER='11a67525c3f930165391912aced7358d8f827a1669700230c6b4672a253cf2f0'
base=a.base_zip.read_bytes()
assert sha(base)==EXPECTED_BASE_ZIP,("WRONG_RUNTIME_BASE",sha(base))
new_renderer=a.renderer.read_bytes()
assert new_renderer[:2]==b'MZ' and len(new_renderer)>1000000,'Win64 renderer absent/invalid'
assert sha(new_renderer)!=EXPECTED_RENDERER,'diagnostic renderer is unchanged'
manifest=json.loads(a.manifest.read_text())
assert manifest['status']=='APPLIED' and len(manifest['modes'])==5
with zipfile.ZipFile(io.BytesIO(base)) as z:
    original={x.filename:z.read(x) for x in z.infolist() if not x.is_dir()}
roots={s.split('/')[0] for s in original}
assert len(roots)==1,roots
root=next(iter(roots))
assert all(not s.startswith('/') and '..' not in Path(s).parts for s in original)
renderer_path=root+'/renderer_sp_rend2_x64.dll'
assert sha(original[renderer_path])==EXPECTED_RENDERER,'accepted renderer does not match handoff'
for n in ('ioWolfSP.x64.exe','renderer_sp_opengl1_x64.dll','Main/cgame_sp_x64.dll','Main/qagame_sp_x64.dll','Main/ui_sp_x64.dll'):
    assert root+'/'+n in original,n
for name in original:
    assert not re.search(r'(^|/)pak[0-9]*\.pk3$',name,re.I),'commercial asset'

launcher=r'''@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not exist "ioWolfSP.x64.exe" (echo Missing SP EXE & pause & exit /b 1)
if not exist "renderer_sp_rend2_x64.dll" (echo Missing Rend2 renderer & pause & exit /b 1)
set "DW_HOME=%CD%\DW_SkyDiag_Home"
if not exist "%DW_HOME%\Main" mkdir "%DW_HOME%\Main"
if not exist "%DW_HOME%\Main" (echo Cannot create diagnostic home & pause & exit /b 1)
rem Preserve and reuse legal savegames. No modification of the original profile.
if exist "%CD%\DW_September_FourWeek_Home\Main\save" (
  if not exist "%DW_HOME%\Main\save" xcopy "%CD%\DW_September_FourWeek_Home\Main\save\*" "%DW_HOME%\Main\save\" /E /I /Y >nul
)
if exist "%CD%\Main\save" (
  if not exist "%DW_HOME%\Main\save" xcopy "%CD%\Main\save\*" "%DW_HOME%\Main\save\" /E /I /Y >nul
)
if exist "%CD%\..\DarkWolf_Sky_MSAA_RootCause_Matrix_V1\DW_SkyDiag_Home\Main\save" (
  if not exist "%DW_HOME%\Main\save" xcopy "%CD%\..\DarkWolf_Sky_MSAA_RootCause_Matrix_V1\DW_SkyDiag_Home\Main\save\*" "%DW_HOME%\Main\save\" /E /I /Y >nul
)
rem Eliminate all stale captures from earlier sessions BEFORE the new game starts.
del /q "%DW_HOME%\Main\DW_SKY_*.pfm" >nul 2>&1
del /q "%DW_HOME%\Main\DW_SKY_*.ppm" >nul 2>&1
del /q "%DW_HOME%\Main\DW_SKY_*_TRACE.csv" >nul 2>&1
del /q "%DW_HOME%\Main\DW_SKY_*_VERDICT.txt" >nul 2>&1
copy /Y "Main\DW_SKY_DIAG_AUTORUN.cfg" "%DW_HOME%\Main\DW_SKY_DIAG_AUTORUN.cfg" >nul
cls
echo ====================================================================
echo  DarkWolf Sky MSAA V3 - corrected 5-mode diagnostic
echo ====================================================================
echo 1. Load Trainyard, look DIRECTLY at the visible sky dashes, press F8 ONCE.
echo 2. Do not move the camera for 20 seconds. The five modes run automatically.
echo 3. Load Factory, look at the sky dashes, press F8 ONCE, stay still 20s.
echo 4. Exit game. The launcher verifies all 40 expected captured files.
echo  NO console commands and NO per-mode switching are required.
echo.
"%CD%\ioWolfSP.x64.exe" +set fs_basepath "%CD%" +set fs_homepath "%DW_HOME%" +set cl_renderer rend2 +set r_renderer rend2 +set r_mode -1 +set r_customwidth 1280 +set r_customheight 768 +set com_recommendedSet 1 +set r_hdr 1 +set r_postProcess 1 +set r_ext_framebuffer_multisample 8 +set r_skyDiagAuto 1 +set r_clear 0 +exec DW_SKY_DIAG_AUTORUN.cfg
set "DW_GAME_EXIT=%ERRORLEVEL%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\VERIFY_SKY_DIAG.ps1" -HomePath "%DW_HOME%\Main" -OutPath "%CD%\SKY_DIAG_RESULTS.zip"
set "DW_VERIFY_EXIT=%ERRORLEVEL%"
if not "%DW_VERIFY_EXIT%"=="0" echo Diagnostic NOT VALIDATED - send the zip for exact failure analysis.
if not "%DW_GAME_EXIT%"=="0" echo Game exit code: %DW_GAME_EXIT%.
echo.
echo Upload SKY_DIAG_RESULTS.zip to ChatGPT.
pause
exit /b %DW_VERIFY_EXIT%
'''
cfg='''// Only diagnostic activation; all production shaders/effects remain enabled.
seta r_skyDiagAuto "1"
seta r_skyDiagArm "0"
bind F8 "set r_skyDiagArm 1"
seta r_clear "0"
seta r_hdr "1"
seta r_postProcess "1"
seta r_ext_framebuffer_multisample "8"
'''
readme='''DARKWOLF SKY MSAA 5-MODE ROOT-CAUSE MATRIX V3 - CAPTURE CORRECTION
================================================================
STATUS: DIAGNOSTIC ONLY; NOT A VISUALLY ACCEPTED FIX.
EXACT RUNTIME BASE: Actions #40294211216, renderer SHA256:
11a67525c3f930165391912aced7358d8f827a1669700230c6b4672a253cf2f0

V1 FAILED: premature indoor captures and trace overflow.
V2 FAILED: all 40 mandatory snapshots gated by skySeen=0, despite valid 8x MSAA.
V3 FIX: mandatory early/HDR/depth/final independent of sky iterator.
Portal sky stages are explicitly probed and mode controls work in auxiliary views.
When no sky stage can be captured, early color comes from pre-post scene resolve
and is labeled FALLBACK_PRE_POST_SCENE_NOT_SKY_ONLY in trace.

ONE-BUTTON LAUNCHER + ONE KEY WHEN READY ON EACH MAP:
  1. Extract into a folder alongside RTCW legally owned Main/pak*.pk3 files.
  2. Start RUN_SKY_DIAG.cmd, load Trainyard.
  3. Walk to the visible sky-dashes vantage point and LOOK at the defect.
  4. Press F8 once, keep camera absolutely still for 20 seconds.
  5. Load Factory, look at sky-dashes, press F8 once, keep still for 20 seconds.
  6. Exit normally. The launcher validates files and creates SKY_DIAG_RESULTS.zip.
NO console commands, NO manual graphics mode changes, NO separate game launches.
The separate DW_SkyDiag_Home profile never changes your installed preferences.

MODES (automatic 0..4 once F8 is pressed):
0 Reference accepted renderer
1 Magenta MSAA color clear control
2 Full six-face outer skybox coverage
3 Clouds skipped; outer/inner skybox retained
4 Full skybox + no clouds

EACH MAP x MODE records:
- sky_early.pfm: sky-only capture if sky iterator fires; otherwise PRE-POST
  SCENE capture via a temporary MSAA resolve; exact source tagged in TRACE.csv
- resolved_hdr.pfm: HDR color after ordinary resolve, before postprocess
- resolved_depth.pfm: depth after resolve
- final.ppm: final 8-bit backbuffer, after all postprocessing
- map TRACE.csv: real sample counts, framebuffer states, camera, GL readback/errors
- SKY_DIAG_VERDICT.txt: machine-verified run completeness and capture integrity.

VALIDITY: 5 modes with successful 4 captures per map, real >=4 MSAA samples,
fixed camera and visible defect. A fallback early image is NOT sky-only. No inference about a clean MSAA stage until
pre/post images are actually present. GL state may require driver-specific analysis.

This package does not contain licensed retail RTCW pak files.
All original accepted binaries except renderer are byte-identical.
'''
verifier=r'''param(
    [Parameter(Mandatory=$true)][string]$HomePath,
    [Parameter(Mandatory=$true)][string]$OutPath
)
$ErrorActionPreference = 'Stop'
$maps = @('trainyard','factory')
$stages = @('sky_early.pfm','resolved_hdr.pfm','resolved_depth.pfm','final.ppm')
$report = New-Object 'System.Collections.Generic.List[string]'
$allValid = $true
$report.Add('DARKWOLF_SKY_MSAA_V3_RUNTIME_VERDICT')
foreach($map in $maps) {
    $trace = Join-Path $HomePath ("DW_SKY_{0}_TRACE.csv" -f $map)
    if(-not (Test-Path -LiteralPath $trace)) {
        $report.Add("MAP_${map}=FAIL_TRACE_MISSING")
        $allValid = $false
        continue
    }
    $body = [System.IO.File]::ReadAllText($trace)
    $skypasses=[regex]::Matches($body,'SKY_PROBE,mode=')
    $skycontrols=[regex]::Matches($body,'SKY_CONTROL_APPLIED,mode=')
    $fallbacks=[regex]::Matches($body,'SKY_EARLY_SOURCE,FALLBACK_PRE_POST_SCENE_NOT_SKY_ONLY')
    $report.Add("MAP_${map}_SKY_PROBES=" + $skypasses.Count + "; appliedControls=" + $skycontrols.Count + "; earlySceneFallbacks=" + $fallbacks.Count)
    $complete = [regex]::Match($body,'RUN_COMPLETE,5,failures=(\d+),glErrors=(\d+),maxRealSamples=(-?\d+),cameraMotion=(\d+),traceOverflow=(\d+)')
    if(-not $complete.Success) {
        $report.Add("MAP_${map}=FAIL_NO_RUN_COMPLETE")
        $allValid = $false
    } else {
        $failures=[int]$complete.Groups[1].Value
        $samples=[int]$complete.Groups[3].Value
        $motion=[int]$complete.Groups[4].Value
        $overflow=[int]$complete.Groups[5].Value
        $valid = $failures -eq 0 -and $samples -ge 4 -and $motion -eq 0 -and $overflow -eq 0
        $report.Add("MAP_${map}_RUNTIME=" + ($(if($valid){'PASS'}else{'FAIL'})) + "; failures=$failures; samples=$samples; motion=$motion; overflow=$overflow")
        if(-not $valid){$allValid=$false}
    }
    for($i=0;$i -lt 5;$i++){
        foreach($stage in $stages){
            $file = Join-Path $HomePath ("DW_SKY_{0}_M{1}_{2}" -f $map,$i,$stage)
            if(-not(Test-Path -LiteralPath $file)){
                $report.Add("MISSING=" + [IO.Path]::GetFileName($file))
                $allValid=$false
            } else {
                if((Get-Item -LiteralPath $file).Length -lt 1000){
                    $report.Add("INVALID_SIZE=" + [IO.Path]::GetFileName($file))
                    $allValid=$false
                }
            }
        }
    }
}
$report.Insert(1,('OVERALL_STATUS=' + $(if($allValid){'COMPLETE'}else{'INCOMPLETE'})))
$reportPath = Join-Path $HomePath 'DW_SKY_DIAG_VERDICT.txt'
[System.IO.File]::WriteAllLines($reportPath,$report.ToArray())
Get-ChildItem -LiteralPath $HomePath -Filter 'DW_SKY_*' -File |
    Compress-Archive -DestinationPath $OutPath -Force
Write-Host ('RESULT: ' + $(if($allValid){'COMPLETE'}else{'INCOMPLETE'}))
Write-Host ('ZIP: ' + $OutPath)
if($allValid){exit 0}else{exit 2}
'''

base_map={s.split('/',1)[1]:v for s,v in original.items()}
assert 'renderer_sp_rend2_x64.dll' in base_map
base_map['renderer_sp_rend2_x64.dll']=new_renderer
base_map['RUN_SKY_DIAG.cmd']=launcher.encode('utf-8')
base_map['VERIFY_SKY_DIAG.ps1']=verifier.encode('utf-8')
base_map['Main/DW_SKY_DIAG_AUTORUN.cfg']=cfg.encode('utf-8')
base_map['README_SKY_DIAGNOSTIC.txt']=readme.encode('utf-8')
base_map['docs/SKY_DIAG_PATCH_MANIFEST.json']=json.dumps(manifest,indent=2).encode('utf-8')
base_map['docs/ACCEPTANCE_STATUS.txt']=b'STATIC_AND_CI_BUILD_DIAGNOSTIC_ONLY; RUNTIME_ACCEPTANCE_PENDING\n'
for name,contents in original.items():
    relative=name.split('/',1)[1]
    if relative=='renderer_sp_rend2_x64.dll': continue
    assert base_map[relative]==contents, ('OTHER_BASE_FILE_MUTATED', relative)
assert all(not re.search(r'(^|/)pak[0-9]*\.pk3$',name,re.I) for name in base_map)
newroot='DarkWolf_Sky_MSAA_RootCause_Matrix_V3'
a.out.mkdir(parents=True,exist_ok=True)
path=a.out/'DarkWolf_Sky_MSAA_RootCause_Matrix_V3_Win64.zip'
with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for name,buf in sorted(base_map.items()):
        info=zipfile.ZipInfo(newroot+'/'+name,date_time=(2026,10,27,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,buf,compress_type=zipfile.ZIP_DEFLATED,compresslevel=7)
(path.with_suffix('.zip.sha256')).write_text(sha(path.read_bytes())+'  '+path.name+'\n')
print('DARKWOLF_SKY_DIAG_V3_FULL_SP_CLEAN_PACKAGE_PASS')
print('PACKAGE',path,'SHA256',sha(path.read_bytes()))
print('REFERENCE_UNMODIFIED_FILES',len(original)-1,'NEW_RENDERER_SHA256',sha(new_renderer))
