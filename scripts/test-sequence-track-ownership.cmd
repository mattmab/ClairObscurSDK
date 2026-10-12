@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\sequence-track-fixture" mkdir "%PROJECT_ROOT%\build\sequence-track-fixture"
pushd "%PROJECT_ROOT%\build\sequence-track-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:sequence_track_fixture.exe "%PROJECT_ROOT%\native\sequence_track_ownership_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
sequence_track_fixture.exe
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
