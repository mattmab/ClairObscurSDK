@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\console-fixture"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /EHsc /std:c++17 /O2 /Fe:console_fixture.exe "%PROJECT_ROOT%\native\console_fixture.cpp"
set "CONSOLE_BUILD_RESULT=%errorlevel%"
popd
exit /b %CONSOLE_BUILD_RESULT%
