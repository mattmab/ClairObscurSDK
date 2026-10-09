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
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:text_call_fixture.exe "%PROJECT_ROOT%\native\text_call_fixture.cpp"
if errorlevel 1 goto failed
text_call_fixture.exe
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:text_frame_fixture.exe "%PROJECT_ROOT%\native\text_frame_fixture.cpp"
if errorlevel 1 goto failed
text_frame_fixture.exe
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:text_dispatch_gate_fixture.exe "%PROJECT_ROOT%\native\text_dispatch_gate_fixture.cpp"
if errorlevel 1 goto failed
text_dispatch_gate_fixture.exe
if errorlevel 1 goto failed
cl /nologo /W4 /WX /EHsc /std:c++17 /Fe:target_text_type_fixture.exe "%PROJECT_ROOT%\native\target_text_type_fixture.cpp"
if errorlevel 1 goto failed
target_text_type_fixture.exe
:failed
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
