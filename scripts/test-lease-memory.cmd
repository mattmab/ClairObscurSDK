@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b 1
if not exist "%PROJECT_ROOT%\build\lease-memory-fixture" mkdir "%PROJECT_ROOT%\build\lease-memory-fixture"
pushd "%PROJECT_ROOT%"
git show 92306f24b2d6f4849f55564cb1e6c88bfd6142da:native/strong_lease_pool.h > build\lease-memory-fixture\baseline_lease_pool.h
if errorlevel 1 (popd & exit /b 1)
popd
pushd "%PROJECT_ROOT%\build\lease-memory-fixture"
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /DLEGACY_LEASE_MEASUREMENT /I. /I"%PROJECT_ROOT%\native" /Fe:legacy.exe "%PROJECT_ROOT%\native\lease_memory_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
legacy.exe
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /DE33_GROWING_LEASE_SESSION /I"%PROJECT_ROOT%\native" /Fe:growing.exe "%PROJECT_ROOT%\native\lease_memory_fixture.cpp"
if errorlevel 1 (popd & exit /b 1)
growing.exe
set "RESULT=%errorlevel%"
popd
exit /b %RESULT%
