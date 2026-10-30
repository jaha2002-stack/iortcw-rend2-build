@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: RUN_HYBRID_V2_AUDIT.bat "C:\Path\to\sp_pak1.pk3" [map_basename]
  echo Example: RUN_HYBRID_V2_AUDIT.bat "C:\Games\RTCW\Main\sp_pak1.pk3" norway
  exit /b 2
)
where py >nul 2>&1
if errorlevel 1 (
  echo Python 3 launch tool 'py' is missing.
  exit /b 2
)
set "REPORT=%~dp0HYBRID_V2_MAP_AUDIT.json"
if "%~2"=="" (
  py -3 "%~dp0integration\hybrid-relight-v2\bsp.py" audit-pk3 "%~1" > "%REPORT%"
) else (
  py -3 "%~dp0integration\hybrid-relight-v2\bsp.py" audit-pk3 "%~1" --only "%~2" > "%REPORT%"
)
if errorlevel 1 (
  echo Failed. Consult console error; no map files were modified.
  exit /b 1
)
echo Read-only audit written to %REPORT%
exit /b 0
