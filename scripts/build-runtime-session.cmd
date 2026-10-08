@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\runtime-session"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /LD /Fe:runtime_session_v2.dll /Fd:runtime_session_v2.pdb "%PROJECT_ROOT%\native\runtime_session.cpp" /link /DEBUG user32.lib
set "SESSION_BUILD_RESULT=%errorlevel%"
popd
exit /b %SESSION_BUILD_RESULT%
