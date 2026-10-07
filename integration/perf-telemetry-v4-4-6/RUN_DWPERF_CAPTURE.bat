@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "DWPERF_ROOT=%CD%"
set "DWPERF_HOME=%DWPERF_ROOT%\DWPerfHome"
set "DWPERF_MAIN=%DWPERF_HOME%\Main"

echo ============================================================
echo DarkWolf ioRTCW Rend2 v4.4.6 Full Performance Telemetry
echo CLEAN CONFIG + HIGH QUALITY BENCHMARK PROFILE
echo ============================================================
echo.
echo This launcher DOES NOT use your normal home-folder wolfconfig.cfg or autoexec.cfg.
echo It starts ioRTCW in SAFE mode and uses a dedicated DWPerfHome folder.
echo Benchmark profile: HIGH QUALITY
echo Resolution: desktop native (r_mode -2)
echo Fullscreen: ON
echo VSync: OFF
echo FPS cap: OFF
echo.

if not exist "ioWolfSP.x64.exe" (
  echo ERROR: ioWolfSP.x64.exe was not found in this folder.
  pause
  exit /b 1
)

if not exist "Main" (
  echo ERROR: Main folder was not found.
  pause
  exit /b 1
)

if not exist "Main\UNIFIED_PRODUCTION.cfg" (
  echo ERROR: Main\UNIFIED_PRODUCTION.cfg was not found.
  pause
  exit /b 1
)

if not exist "Main\DWPERF_HIGH_QUALITY.cfg" (
  echo ERROR: Main\DWPERF_HIGH_QUALITY.cfg was not found.
  pause
  exit /b 1
)

rem ---------------------------------------------------------------------------
rem Hard isolation from normal user configuration.
rem A new clean home tree is created for every capture.
rem The engine's +safe command skips loading wolfconfig.cfg and autoexec.cfg.
rem ---------------------------------------------------------------------------
if exist "%DWPERF_HOME%" rmdir /s /q "%DWPERF_HOME%"
mkdir "%DWPERF_MAIN%" >nul 2>nul

rem Defensive empty files: SAFE mode should skip them, but these make the
rem isolated home self-contained even if startup behavior changes later.
> "%DWPERF_MAIN%\wolfconfig.cfg" echo // DWPERF CLEAN HOME - intentionally empty
> "%DWPERF_MAIN%\autoexec.cfg" echo // DWPERF CLEAN HOME - intentionally empty

echo DWPERF_ROOT=%DWPERF_ROOT% > "%DWPERF_HOME%\DWPERF_SESSION.txt"
echo DWPERF_HOME=%DWPERF_HOME% >> "%DWPERF_HOME%\DWPERF_SESSION.txt"
echo PROFILE=HIGH_QUALITY >> "%DWPERF_HOME%\DWPERF_SESSION.txt"
echo CONFIG_ISOLATION=SAFE_PLUS_DEDICATED_HOMEPATH >> "%DWPERF_HOME%\DWPERF_SESSION.txt"

echo Starting the game...
echo.
echo Play normally and visit the scenes listed in README_DWPERF_RU.txt.
echo When finished, quit the game normally.
echo The telemetry ZIP will be created automatically.
echo.

start /wait "" "ioWolfSP.x64.exe" ^
  +set fs_basepath "%DWPERF_ROOT%" ^
  +set fs_homepath "%DWPERF_HOME%" ^
  +safe ^
  +set com_introplayed 1 ^
  +set logfile 2 ^
  +set developer 0 ^
  +set cl_renderer rend2 ^
  +set r_renderer rend2 ^
  +exec UNIFIED_PRODUCTION.cfg ^
  +exec DWPERF_HIGH_QUALITY.cfg ^
  +vid_restart

echo.
echo Game closed. Collecting telemetry from isolated DWPerfHome...

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Collect-DWPerf.ps1" -HomePath "%DWPERF_HOME%"

echo.
echo Finished.
echo Send the newest DWPerfTelemetry_*.zip file to ChatGPT.
pause
endlocal
