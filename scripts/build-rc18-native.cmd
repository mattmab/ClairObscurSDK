@echo off
setlocal
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
call "%~dp0build-cinematic-retirement-candidate.cmd"
if errorlevel 1 exit /b 1
call "%~dp0build-readonly-worker-values.cmd"
if errorlevel 1 exit /b 1
if not exist "%PROJECT_ROOT%\build\release\thumbnail-worker-v2" mkdir "%PROJECT_ROOT%\build\release\thumbnail-worker-v2"
pushd "%PROJECT_ROOT%\build\release\thumbnail-worker-v2"
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /LD /Fe:thumbnail_worker.dll "%PROJECT_ROOT%\native\thumbnail_worker.cpp" /link ole32.lib windowscodecs.lib
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%
