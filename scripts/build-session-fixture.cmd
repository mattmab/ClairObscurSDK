@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
set "BUILD_DIR=%PROJECT_ROOT%\build\session-fixture"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
pushd "%BUILD_DIR%"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /LD /Fe:session_fixture.dll /Fd:session_fixture_dll.pdb "%PROJECT_ROOT%\native\session_fixture_dll.cpp" /link /DEBUG user32.lib
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Zi /Fe:session_fixture.exe /Fd:session_fixture.pdb "%PROJECT_ROOT%\native\session_fixture.cpp" /link /DEBUG user32.lib bcrypt.lib
:failed
set "SESSION_BUILD_RESULT=%errorlevel%"
popd
exit /b %SESSION_BUILD_RESULT%
