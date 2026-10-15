@echo off
setlocal
cd /d "%~dp0"
where cl >nul 2>nul
if errorlevel 1 (
  echo Run from an x64 Native Tools Command Prompt for Visual Studio.
  exit /b 1
)
if not exist build\release\thumbnail-worker-v2 mkdir build\release\thumbnail-worker-v2
pushd build\release\thumbnail-worker-v2
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /LD /Fe:thumbnail_worker.dll ..\..\..\native\thumbnail_worker.cpp /link ole32.lib windowscodecs.lib
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
