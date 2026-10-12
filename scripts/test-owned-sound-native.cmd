@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\owned-sound-fixture" mkdir "%PROJECT_ROOT%\build\owned-sound-fixture"
pushd "%PROJECT_ROOT%\build\owned-sound-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:owned_sound_fixture.exe "%PROJECT_ROOT%\native\owned_sound_fixture.cpp" user32.lib
if errorlevel 1 exit /b %errorlevel%
owned_sound_fixture.exe
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%

