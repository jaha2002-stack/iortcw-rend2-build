@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if not exist "ioWolfSP.x64.exe" exit /b 1
if not exist "Main\PRODUCTION_HIGH_QUALITY.cfg" exit /b 1
set "DW_RELEASE_ROOT=%CD%"
set "DW_RELEASE_HOME=%CD%\DWOptimizedHome"
if not exist "%DW_RELEASE_HOME%\Main" mkdir "%DW_RELEASE_HOME%\Main"
if not exist "%DW_RELEASE_HOME%\Main" exit /b 1
rem Copy only the controlled preset; never delete saves or the normal user profile.
copy /y "Main\PRODUCTION_HIGH_QUALITY.cfg" "%DW_RELEASE_HOME%\Main\PRODUCTION_HIGH_QUALITY.cfg" >nul
if errorlevel 1 exit /b 1
"%DW_RELEASE_ROOT%\ioWolfSP.x64.exe" +set fs_basepath "%DW_RELEASE_ROOT%" +set fs_homepath "%DW_RELEASE_HOME%" +safe +set com_introplayed 1 +set com_recommendedSet 1 +set cl_renderer rend2 +set r_renderer rend2 +exec PRODUCTION_HIGH_QUALITY.cfg +vid_restart
exit /b %errorlevel%
