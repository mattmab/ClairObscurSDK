@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\owned-text-fixture" mkdir "%PROJECT_ROOT%\build\owned-text-fixture"
pushd "%PROJECT_ROOT%\build\owned-text-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:owned_text_fixture.exe "%PROJECT_ROOT%\native\owned_text_fixture.cpp"
if errorlevel 1 goto failed
owned_text_fixture.exe
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /c "%PROJECT_ROOT%\native\owned_text_compile.cpp"
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
