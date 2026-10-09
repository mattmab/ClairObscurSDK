@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\enum-schema-fixture" mkdir "%PROJECT_ROOT%\build\enum-schema-fixture"
pushd "%PROJECT_ROOT%\build\enum-schema-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:enum_schema_fixture.exe "%PROJECT_ROOT%\native\enum_schema_fixture.cpp"
if errorlevel 1 goto failed
enum_schema_fixture.exe
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
