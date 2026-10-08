@echo off
setlocal
set "SDK_PYTHON=D:\HobbyDevelopment\Python\expedition33-tools\Scripts\python.exe"
if not exist "%SDK_PYTHON%" (
  echo Missing CPython 3.13.15 environment: %SDK_PYTHON%
  echo See DEVELOPMENT.md for setup.
  exit /b 1
)
"%SDK_PYTHON%" -I -S -B "%~dp0scripts\run_sdk.py" %*
exit /b %errorlevel%
