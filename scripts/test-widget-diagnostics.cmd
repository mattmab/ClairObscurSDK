@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
call D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 exit /b 1
if not exist "%PROJECT_ROOT%\build\widget-diagnostics-fixture" mkdir "%PROJECT_ROOT%\build\widget-diagnostics-fixture"
pushd "%PROJECT_ROOT%\build\widget-diagnostics-fixture"
for %%F in (cinematic_component_frame cinematic_widget_journal cinematic_widget_diagnostics cinematic_widget_lifecycle) do (
  cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:%%F.exe "%PROJECT_ROOT%\native\%%F_fixture.cpp"
  if errorlevel 1 exit /b 1
  %%F.exe
  if errorlevel 1 exit /b 1
)
popd
exit /b 0
