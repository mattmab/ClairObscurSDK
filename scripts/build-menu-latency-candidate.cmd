@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\menu-latency-probe" mkdir "%PROJECT_ROOT%\build\menu-latency-probe"
pushd "%PROJECT_ROOT%\build\menu-latency-probe"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:session_wait_fixture.exe "%PROJECT_ROOT%\native\session_wait_fixture.cpp"
if errorlevel 1 goto finished
session_wait_fixture.exe
if errorlevel 1 goto finished
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /DE33_VECTOR_SESSION /DE33_KEYBIND_SESSION /DE33_TRACE_SESSION /DE33_MULTI_BUTTON_SESSION /DE33_BUTTON_ACTION_SESSION /DE33_BUTTON_REFERENCE_SESSION /DE33_MENU_SESSION /DE33_ENUM_SESSION /DE33_TEXT_SESSION /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /Fe:research_probe.exe "%PROJECT_ROOT%\native\research_probe.cpp" /link bcrypt.lib user32.lib
:finished
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%
