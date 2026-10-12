@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\binding-query-tests" mkdir "%PROJECT_ROOT%\build\binding-query-tests"
pushd "%PROJECT_ROOT%\build\binding-query-tests"
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:camera_binding_fixture.exe "%PROJECT_ROOT%\native\camera_binding_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
camera_binding_fixture.exe
if errorlevel 1 exit /b %errorlevel%
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:binding_batch_fixture.exe "%PROJECT_ROOT%\native\binding_batch_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
binding_batch_fixture.exe
if errorlevel 1 exit /b %errorlevel%
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:spawn_membership_fixture.exe "%PROJECT_ROOT%\native\spawn_membership_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
spawn_membership_fixture.exe
set "BUILD_RESULT=%errorlevel%"
popd
exit /b %BUILD_RESULT%
