@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\text-compatibility" mkdir "%PROJECT_ROOT%\build\text-compatibility"
pushd "%PROJECT_ROOT%\build\text-compatibility"
rem Compile only: never replace a DLL or executable used by a live controller.
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:runtime_v5.obj "%PROJECT_ROOT%\native\runtime_session.cpp"
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /Fo:runtime_v11.obj "%PROJECT_ROOT%\native\runtime_session.cpp"
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /Fo:controller_v11.obj "%PROJECT_ROOT%\native\research_probe.cpp"
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
