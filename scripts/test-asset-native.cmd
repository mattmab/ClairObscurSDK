@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\asset-fixture" mkdir "%PROJECT_ROOT%\build\asset-fixture"
pushd "%PROJECT_ROOT%\build\asset-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:asset_call_fixture.exe "%PROJECT_ROOT%\native\asset_call_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
asset_call_fixture.exe
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%

