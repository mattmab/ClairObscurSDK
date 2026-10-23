@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\enemy-arena-binding-fixture" mkdir "%PROJECT_ROOT%\build\enemy-arena-binding-fixture"
pushd "%PROJECT_ROOT%\build\enemy-arena-binding-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:enemy_arena_binding_fixture.exe "%PROJECT_ROOT%\native\enemy_arena_binding_fixture.cpp"
if errorlevel 1 goto failed
enemy_arena_binding_fixture.exe
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
