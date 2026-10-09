@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\button-pool-fixture" mkdir "%PROJECT_ROOT%\build\button-pool-fixture"
pushd "%PROJECT_ROOT%\build\button-pool-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:menu_focus_controls_fixture.exe "%PROJECT_ROOT%\native\menu_focus_controls_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
menu_focus_controls_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:button_delegate_pool_fixture.exe "%PROJECT_ROOT%\native\button_delegate_pool_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
button_delegate_pool_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:multi_button_target_compile.obj "%PROJECT_ROOT%\native\button_target_compile.cpp"
if errorlevel 1 (popd & exit /b 1)
set "FLAGS=/DE33_MULTI_BUTTON_SESSION /DE33_BUTTON_ACTION_SESSION /DE33_BUTTON_REFERENCE_SESSION /DE33_MENU_SESSION /DE33_ENUM_SESSION /DE33_TEXT_SESSION /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 %FLAGS% /c /Fo:runtime_multi.obj "%PROJECT_ROOT%\native\runtime_session.cpp"
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:multi_button_protocol_fixture.exe "%PROJECT_ROOT%\native\multi_button_protocol_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
multi_button_protocol_fixture.exe
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
