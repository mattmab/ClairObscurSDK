@echo off
cd /d "%~dp0"
"%~dp0runtime\python.exe" -I -S -B "%~dp0scripts\run_release_sdk.py" %*
