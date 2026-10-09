@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\strong-reference-fixture" mkdir "%PROJECT_ROOT%\build\strong-reference-fixture"
pushd "%PROJECT_ROOT%\build\strong-reference-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:strong_reference_fixture.exe "%PROJECT_ROOT%\native\strong_reference_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
strong_reference_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:target_adapter.obj "%PROJECT_ROOT%\native\strong_reference_compile.cpp"
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
