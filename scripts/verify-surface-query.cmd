@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\surface-query-fixture" mkdir "%PROJECT_ROOT%\build\surface-query-fixture"
pushd "%PROJECT_ROOT%\build\surface-query-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:surface_query_fixture.exe "%PROJECT_ROOT%\native\surface_query_fixture.cpp"
if errorlevel 1 goto failed
surface_query_fixture.exe
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
