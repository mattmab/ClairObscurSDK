@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
if not exist "%TEMP%" mkdir "%TEMP%"
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\scheduling-fixture"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /EHsc /std:c++17 /O2 /Zi /LD /Fe:scheduling_hook.dll /Fd:scheduling_hook.pdb "%PROJECT_ROOT%\native\scheduling_hook.cpp" /link /DEBUG user32.lib
if errorlevel 1 goto failed
cl /nologo /W4 /EHsc /std:c++17 /O2 /Zi /Fe:scheduling_fixture.exe /Fd:scheduling_fixture.pdb "%PROJECT_ROOT%\native\scheduling_fixture.cpp" /link /DEBUG user32.lib bcrypt.lib
:failed
set "FIXTURE_RESULT=%errorlevel%"
popd
exit /b %FIXTURE_RESULT%
