@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\menu-user-slots-fixture"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:trace_target_compile.obj "%PROJECT_ROOT%\native\trace_target_compile.cpp"
if errorlevel 1 goto finished
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:menu_user_slots_fixture.exe "%PROJECT_ROOT%\native\menu_user_slots_fixture.cpp"
if errorlevel 1 goto finished
menu_user_slots_fixture.exe
:finished
set "FIXTURE_RESULT=%errorlevel%"
popd
exit /b %FIXTURE_RESULT%



