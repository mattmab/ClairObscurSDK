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
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:button_target_compile.obj "%PROJECT_ROOT%\native\button_target_compile.cpp"
if errorlevel 1 (popd & exit /b 1)
set "RUNTIME_FLAGS=/DE33_BUTTON_REFERENCE_SESSION /DE33_MENU_SESSION /DE33_ENUM_SESSION /DE33_TEXT_SESSION /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 %RUNTIME_FLAGS% /c /Fo:runtime_v15_compat.obj "%PROJECT_ROOT%\native\runtime_session.cpp"
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 %RUNTIME_FLAGS% /DE33_BUTTON_ACTION_SESSION /c /Fo:runtime_actions.obj "%PROJECT_ROOT%\native\runtime_session.cpp"
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 %RUNTIME_FLAGS% /DE33_BUTTON_ACTION_SESSION /Fe:session_layout_v16.exe "%PROJECT_ROOT%\native\session_layout_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
session_layout_v16.exe
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
