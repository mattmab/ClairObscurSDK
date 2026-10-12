@echo off
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
pushd D:\HobbyDevelopment\ClairObscurSDK\build\menu-latency-probe
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:pause_attachment_fixture.exe ..\..\native\pause_attachment_fixture.cpp
if errorlevel 1 exit /b %errorlevel%
pause_attachment_fixture.exe
