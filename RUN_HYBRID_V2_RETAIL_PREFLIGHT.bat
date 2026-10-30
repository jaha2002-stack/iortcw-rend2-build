@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: RUN_HYBRID_V2_RETAIL_PREFLIGHT.bat ^<original-maps.zip or game.pk3^> ^<new-output-folder^>
  exit /b 2
)
if "%~2"=="" (
  echo Provide a NEW output folder as second argument. No existing folder will be overwritten.
  exit /b 2
)
py -3 "%~dp0integration\hybrid-relight-v2\policy.py" "%~1" --out "%~2"
if errorlevel 1 exit /b 1
echo HYBRID_RELIGHT_V2_STAGE1_RETAIL_PREFLIGHT_PASS
exit /b 0
