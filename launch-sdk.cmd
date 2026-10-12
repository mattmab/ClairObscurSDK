@echo off
setlocal
if exist "%~dp0release-manifest.json" (
  "%~dp0runtime\python.exe" -I -S -B "%~dp0scripts\run_release_sdk.py" %*
  exit /b
)
if not defined SDK_GAME_DIR if exist "%~dp0settings\install-path.txt" set /p SDK_GAME_DIR=<"%~dp0settings\install-path.txt"
if not defined SDK_GAME_DIR (
  echo Install the release ZIP, then set SDK_GAME_DIR to the game directory.
  exit /b 1
)
if not exist "%SDK_GAME_DIR%\SDK\launch-sdk.cmd" (
  echo Installed SDK launcher is missing in SDK_GAME_DIR.
  exit /b 1
)
call "%SDK_GAME_DIR%\SDK\launch-sdk.cmd" %*
exit /b %errorlevel%
