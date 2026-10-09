@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\menu-action-fixture" mkdir "%PROJECT_ROOT%\build\menu-action-fixture"
pushd "%PROJECT_ROOT%\build\menu-action-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:menu_action_events_fixture.exe "%PROJECT_ROOT%\native\menu_action_events_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
menu_action_events_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:button_delegate_fixture.exe "%PROJECT_ROOT%\native\button_delegate_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
button_delegate_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:button_forward_fixture.exe "%PROJECT_ROOT%\native\button_forward_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
button_forward_fixture.exe
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
