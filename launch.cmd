@echo off
setlocal
if exist "%~dp0runtime\python.exe" (
  set "SDK_PYTHON=%~dp0runtime\python.exe"
)
if not defined SDK_PYTHON (
  echo Missing bundled Python. Prepare runtime or set SDK_PYTHON to CPython 3.13.15.
  exit /b 1
)
if not exist "%SDK_PYTHON%" (
  echo Missing CPython 3.13.15 executable: %SDK_PYTHON%
  echo See DEVELOPMENT.md for setup.
  exit /b 1
)
"%SDK_PYTHON%" -I -S -B "%~dp0scripts\run_sdk.py" %*
exit /b %errorlevel%
