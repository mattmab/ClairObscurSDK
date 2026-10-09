@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\trace-slots-fixture"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:trace_slots_fixture.exe "%PROJECT_ROOT%\native\trace_slots_fixture.cpp"
if errorlevel 1 goto finished
trace_slots_fixture.exe
:finished
set "FIXTURE_RESULT=%errorlevel%"
popd
exit /b %FIXTURE_RESULT%
