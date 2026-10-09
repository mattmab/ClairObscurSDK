@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\menu-lifetime-fixture" mkdir "%PROJECT_ROOT%\build\menu-lifetime-fixture"
pushd "%PROJECT_ROOT%\build\menu-lifetime-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:menu_lifetime_fixture.exe "%PROJECT_ROOT%\native\menu_lifetime_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
menu_lifetime_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:slate_reference_fixture.exe "%PROJECT_ROOT%\native\slate_reference_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
slate_reference_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:menu_focus_adapter.obj "%PROJECT_ROOT%\native\menu_focus_compile.cpp"
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
