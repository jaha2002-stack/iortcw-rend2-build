@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0COLLECT_DW_PS_V4.ps1"
echo.
echo Attach DW_PS_V4_*.zip to ChatGPT. No automatic upload.
pause
