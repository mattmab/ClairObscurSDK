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
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /c /Fo:runtime_v9_compat.obj /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION "%PROJECT_ROOT%\native\runtime_session.cpp"
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /c /Fo:runtime_v5_compat.obj "%PROJECT_ROOT%\native\runtime_session.cpp"
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
