@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo DarkWolf ioRTCW Rend2 v4.4.6 Full Performance Telemetry
echo ============================================================
echo.
echo This launcher does not change renderer quality settings.
echo It temporarily disables VSync and FPS cap for the capture session.
echo Your local wolfconfig.cfg is backed up and restored after the run.
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

if exist "Main\wolfconfig.dwperf_backup.cfg" del /q "Main\wolfconfig.dwperf_backup.cfg" >nul 2>nul
if exist "Main\wolfconfig.cfg" copy /y "Main\wolfconfig.cfg" "Main\wolfconfig.dwperf_backup.cfg" >nul

if exist "Main\qconsole.log" (
  if exist "Main\qconsole.dwperf_previous.log" del /q "Main\qconsole.dwperf_previous.log" >nul 2>nul
  move /y "Main\qconsole.log" "Main\qconsole.dwperf_previous.log" >nul
)

echo Starting the game...
echo Play normally and visit the scenes listed in README_DWPERF_RU.txt.
echo When finished, quit the game normally. The telemetry ZIP will be created automatically.
echo.

start /wait "" "ioWolfSP.x64.exe" ^
  +set fs_basepath "%CD%" ^
  +set fs_homepath "%CD%" ^
  +set com_introplayed 1 ^
  +set logfile 2 ^
  +set developer 0 ^
  +set cl_renderer rend2 ^
  +set r_renderer rend2 ^
  +set r_swapInterval 0 ^
  +set com_maxfps 0 ^
  +exec UNIFIED_PRODUCTION.cfg

echo.
echo Game closed. Collecting telemetry...

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Collect-DWPerf.ps1"

if exist "Main\wolfconfig.dwperf_backup.cfg" (
  copy /y "Main\wolfconfig.dwperf_backup.cfg" "Main\wolfconfig.cfg" >nul
  del /q "Main\wolfconfig.dwperf_backup.cfg" >nul 2>nul
)

echo.
echo Finished.
echo Send the newest DWPerfTelemetry_*.zip file to ChatGPT.
pause
endlocal
