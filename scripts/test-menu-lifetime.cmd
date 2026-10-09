@echo off
setlocal
set "TEMP=D:\HobbyDevelopment\Caches\ClairObscurSDK"
set "TMP=%TEMP%"
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\menu-lifetime-fixture" mkdir "%PROJECT_ROOT%\build\menu-lifetime-fixture"
pushd "%PROJECT_ROOT%\build\menu-lifetime-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:menu_lifetime_fixture.exe "%PROJECT_ROOT%\native\menu_lifetime_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
menu_lifetime_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:slate_reference_fixture.exe "%PROJECT_ROOT%\native\slate_reference_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
slate_reference_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:menu_call_fixture.exe "%PROJECT_ROOT%\native\menu_call_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
menu_call_fixture.exe
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /c /Fo:menu_focus_adapter.obj "%PROJECT_ROOT%\native\menu_focus_compile.cpp"
if errorlevel 1 (popd & exit /b 1)
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /DE33_ENUM_SESSION /DE33_TEXT_SESSION /DE33_REFLECTED_SESSION /DE33_LEASE_SESSION /DE33_RETAINED_SESSION /DE33_STABLE_SESSION /DE33_ASSIGNMENT_SESSION /DE33_POD_SESSION /c /Fo:runtime_compat.obj "%PROJECT_ROOT%\native\runtime_session.cpp"
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
