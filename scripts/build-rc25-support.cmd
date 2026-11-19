@echo off
setlocal
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
where cl >nul 2>nul
if errorlevel 1 (echo Run from an x64 Visual Studio developer prompt. & exit /b 1)
call "%PROJECT_ROOT%\scripts\build-bootstrap.cmd"
if errorlevel 1 exit /b %errorlevel%
call "%PROJECT_ROOT%\scripts\build-readonly-worker-values.cmd"
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\release\thumbnail-worker-v2" mkdir "%PROJECT_ROOT%\build\release\thumbnail-worker-v2"
pushd "%PROJECT_ROOT%\build\release\thumbnail-worker-v2"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /LD /Fe:thumbnail_worker.dll "%PROJECT_ROOT%\native\thumbnail_worker.cpp" /link ole32.lib windowscodecs.lib
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%
