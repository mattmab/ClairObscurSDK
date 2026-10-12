@echo off
setlocal
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\bootstrap" mkdir "%PROJECT_ROOT%\build\bootstrap"
pushd "%PROJECT_ROOT%\build\bootstrap"
ml64 /nologo /c /Foforwarders.obj "%PROJECT_ROOT%\native\bootstrap\forwarders.asm"
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /MT /LD "%PROJECT_ROOT%\native\bootstrap\bootstrap.cpp" forwarders.obj /link /DEF:"%PROJECT_ROOT%\native\bootstrap\version.def" /OUT:version.dll
:failed
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%
