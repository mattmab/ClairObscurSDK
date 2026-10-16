@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%PROJECT_ROOT%\build\menu-latency-probe"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /DE33_UI_CONSTRUCTION_SESSION /DE33_LAYOUT_BATCH_SESSION /DE33_UI_BATCH_SESSION /DE33_VECTOR_SESSION /DE33_KEYBIND_SESSION /DE33_TRACE_SESSION /DE33_MULTI_BUTTON_SESSION /DE33_BUTTON_ACTION_SESSION /DE33_BUTTON_REFERENCE_SESSION /DE33_MENU_SESSION /DE33_ENUM_SESSION /DE33_TEXT_SESSION /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /Fe:ui_batch_fixture.exe "%PROJECT_ROOT%\native\ui_batch_fixture.cpp"
if errorlevel 1 goto finished
ui_batch_fixture.exe
:finished
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%

