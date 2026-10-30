@echo off
setlocal
where cl >nul 2>nul
if errorlevel 1 (echo Run from an x64 Visual Studio developer prompt. & exit /b 1)
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\readonly-worker-values-v2"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
pushd "%BUILD_DIR%"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:research_probe.exe "%PROJECT_ROOT%\native\research_probe.cpp" /link bcrypt.lib user32.lib
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%
