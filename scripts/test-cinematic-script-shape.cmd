@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\cinematic-script-shape-fixture" mkdir "%PROJECT_ROOT%\build\cinematic-script-shape-fixture"
pushd "%PROJECT_ROOT%\build\cinematic-script-shape-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:cinematic_script_shape_fixture.exe "%PROJECT_ROOT%\native\cinematic_script_shape_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
cinematic_script_shape_fixture.exe
if errorlevel 1 exit /b %errorlevel%
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:numbered_field_name_fixture.exe "%PROJECT_ROOT%\native\numbered_field_name_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
numbered_field_name_fixture.exe
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
