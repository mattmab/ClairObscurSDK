@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\object-assignment-fixture" mkdir "%PROJECT_ROOT%\build\object-assignment-fixture"
pushd "%PROJECT_ROOT%\build\object-assignment-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:object_assignment_fixture.exe "%PROJECT_ROOT%\native\object_assignment_fixture.cpp"
if errorlevel 1 goto failed
object_assignment_fixture.exe
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /c "%PROJECT_ROOT%\native\object_assignment_compile.cpp"
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
