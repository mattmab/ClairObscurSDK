@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b 1
if not exist "%PROJECT_ROOT%\build\timespan-fixture" mkdir "%PROJECT_ROOT%\build\timespan-fixture"
pushd "%PROJECT_ROOT%\build\timespan-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /DE33_TIMESPAN_SESSION /Fe:enabled.exe "%PROJECT_ROOT%\native\timespan_fixture.cpp"
if errorlevel 1 exit /b 1
enabled.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:disabled.exe "%PROJECT_ROOT%\native\timespan_fixture.cpp"
if errorlevel 1 exit /b 1
disabled.exe
if errorlevel 1 exit /b 1
popd
exit /b 0
