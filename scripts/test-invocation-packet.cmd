@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\invocation-fixture" mkdir "%PROJECT_ROOT%\build\invocation-fixture"
pushd "%PROJECT_ROOT%\build\invocation-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:invocation_fixture.exe "%PROJECT_ROOT%\native\invocation_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
invocation_fixture.exe
if errorlevel 1 (popd & exit /b 1)
rem Compile the default v5 paths without replacing the user's pinned DLL/reader.
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:v5_runtime.obj "%PROJECT_ROOT%\native\runtime_session.cpp"
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:v5_reader.obj "%PROJECT_ROOT%\native\research_probe.cpp"
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
