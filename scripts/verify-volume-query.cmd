@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\volume-query-fixture" mkdir "%PROJECT_ROOT%\build\volume-query-fixture"
pushd "%PROJECT_ROOT%\build\volume-query-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:volume_query_fixture.exe "%PROJECT_ROOT%\native\volume_query_fixture.cpp"
if errorlevel 1 goto failed
volume_query_fixture.exe
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
