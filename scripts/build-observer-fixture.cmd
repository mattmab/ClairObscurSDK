@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\observer-fixture"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /LD /Fe:observer_fixture.dll /Fd:observer_fixture_dll.pdb "%PROJECT_ROOT%\native\observer_fixture_dll.cpp" /link /DEBUG
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /Fe:observer_fixture.exe /Fd:observer_fixture.pdb "%PROJECT_ROOT%\native\observer_fixture.cpp" /link /DEBUG
:failed
set "FIXTURE_RESULT=%errorlevel%"
popd
exit /b %FIXTURE_RESULT%
