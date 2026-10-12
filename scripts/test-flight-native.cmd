@echo off
setlocal
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b 1
cd /d "%~dp0..\build\pod-value-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:vector_call_fixture.exe ..\..\native\vector_call_fixture.cpp
if errorlevel 1 exit /b 1
vector_call_fixture.exe
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:flight_schema_fixture.exe ..\..\native\pod_schema_fixture.cpp
if errorlevel 1 exit /b 1
flight_schema_fixture.exe
exit /b %errorlevel%
