@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\sequence-fixture" mkdir "%PROJECT_ROOT%\build\sequence-fixture"
pushd "%PROJECT_ROOT%\build\sequence-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:sequence_call_fixture.exe "%PROJECT_ROOT%\native\sequence_call_fixture.cpp" user32.lib
if errorlevel 1 exit /b %errorlevel%
sequence_call_fixture.exe
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
