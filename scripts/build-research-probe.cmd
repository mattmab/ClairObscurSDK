@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
if not exist "%TEMP%" mkdir "%TEMP%"
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\research-probe"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /EHsc /std:c++17 /O2 /Zi /Fe:research_probe.exe /Fd:research_probe.pdb "%PROJECT_ROOT%\native\research_probe.cpp" /link /DEBUG bcrypt.lib user32.lib
set "PROBE_BUILD_RESULT=%errorlevel%"
popd
exit /b %PROBE_BUILD_RESULT%
