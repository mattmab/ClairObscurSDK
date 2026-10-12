@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\media-fixture" mkdir "%PROJECT_ROOT%\build\media-fixture"
pushd "%PROJECT_ROOT%\build\media-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:media_owner_fixture.exe "%PROJECT_ROOT%\native\media_owner_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
media_owner_fixture.exe
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
