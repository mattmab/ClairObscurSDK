@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\mcp-smoke"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /Od /Zi /Fe:mcp_smoke.exe /Fd:mcp_smoke.pdb "%PROJECT_ROOT%\native\fixtures\mcp_smoke.c" /link /DEBUG
if errorlevel 1 (popd & exit /b 1)
mcp_smoke.exe
set "FIXTURE_RESULT=%errorlevel%"
popd
exit /b %FIXTURE_RESULT%
