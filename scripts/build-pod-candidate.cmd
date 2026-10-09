@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\runtime-session-v11" mkdir "%PROJECT_ROOT%\build\runtime-session-v11"
if not exist "%PROJECT_ROOT%\build\research-probe-v11" mkdir "%PROJECT_ROOT%\build\research-probe-v11"
pushd "%PROJECT_ROOT%\build\runtime-session-v11"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /LD /Fe:runtime_session_v11.dll /Fd:runtime_session_v11.pdb "%PROJECT_ROOT%\native\runtime_session.cpp" /link /DEBUG user32.lib
set "BUILD_RESULT=%errorlevel%"
popd
if not "%BUILD_RESULT%"=="0" exit /b %BUILD_RESULT%
pushd "%PROJECT_ROOT%\build\research-probe-v11"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /Fe:research_probe.exe /Fd:research_probe.pdb "%PROJECT_ROOT%\native\research_probe.cpp" /link /DEBUG bcrypt.lib user32.lib
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%




