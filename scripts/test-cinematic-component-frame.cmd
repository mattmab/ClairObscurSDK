@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\cinematic-component-frame-fixture" mkdir "%PROJECT_ROOT%\build\cinematic-component-frame-fixture"
pushd "%PROJECT_ROOT%\build\cinematic-component-frame-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:cinematic_component_frame_fixture.exe "%PROJECT_ROOT%\native\cinematic_component_frame_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
cinematic_component_frame_fixture.exe
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
