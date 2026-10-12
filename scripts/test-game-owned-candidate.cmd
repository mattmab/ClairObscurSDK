@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call "D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 exit /b %errorlevel%
if not exist "%PROJECT_ROOT%\build\game-owned-fixtures" mkdir "%PROJECT_ROOT%\build\game-owned-fixtures"
pushd "%PROJECT_ROOT%\build\game-owned-fixtures"
cl /nologo /W4 /WX /EHsc /std:c++17 /I"%PROJECT_ROOT%\native" /Fe:admission_off.exe "%PROJECT_ROOT%\native\game_owned_cinematic_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
admission_off.exe
if errorlevel 1 exit /b %errorlevel%
cl /nologo /W4 /WX /EHsc /std:c++17 /DE33_GAME_OWNED_CINEMATIC_SESSION /I"%PROJECT_ROOT%\native" /Fe:admission_on.exe "%PROJECT_ROOT%\native\game_owned_cinematic_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
admission_on.exe
if errorlevel 1 exit /b %errorlevel%
cl /nologo /W4 /WX /EHsc /std:c++17 /I"%PROJECT_ROOT%\native" /Fe:repeat.exe "%PROJECT_ROOT%\native\scavenger_repeat_fixture.cpp"
if errorlevel 1 exit /b %errorlevel%
repeat.exe
set "TEST_RESULT=%errorlevel%"
popd
exit /b %TEST_RESULT%
