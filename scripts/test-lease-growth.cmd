@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\lease-growth-fixture" mkdir "%PROJECT_ROOT%\build\lease-growth-fixture"
pushd "%PROJECT_ROOT%\build\lease-growth-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:lease_growth_fixture.exe "%PROJECT_ROOT%\native\lease_growth_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
lease_growth_fixture.exe
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
