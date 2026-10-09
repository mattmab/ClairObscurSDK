@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\button-pool-fixture" mkdir "%PROJECT_ROOT%\build\button-pool-fixture"
pushd "%PROJECT_ROOT%\build\button-pool-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:button_delegate_pool_fixture.exe "%PROJECT_ROOT%\native\button_delegate_pool_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
button_delegate_pool_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:multi_button_target_compile.obj "%PROJECT_ROOT%\native\button_target_compile.cpp"
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
