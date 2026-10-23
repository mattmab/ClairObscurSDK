$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot 'test-runtime-cinematic.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Cinematic regressions failed' }
$taskOutput=Join-Path $taskRoot '.test-tmp/scene-editor'
New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
$taskWrapper=Join-Path $taskOutput 'native-test.cmd'
$taskText="@echo off`r`ncall D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64`r`nif errorlevel 1 exit /b %errorlevel%`r`ncd /d `"$taskOutput`"`r`ncl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:runtime_scene_plan_fixture.exe `"$taskRoot\native\runtime_scene_plan_fixture.cpp`"`r`nif errorlevel 1 exit /b %errorlevel%`r`nruntime_scene_plan_fixture.exe`r`n"
[IO.File]::WriteAllText($taskWrapper,$taskText,[Text.Encoding]::ASCII)
& $env:ComSpec /d /c $taskWrapper
if ($LASTEXITCODE -ne 0) { throw 'Native scene plan fixture failed' }
Push-Location $taskRoot
try {
    & "$taskRoot/runtime/python.exe" -I -S -B -c "import sys,tempfile,unittest;sys.path[:0]=['src','tests'];tempfile.tempdir='$($taskOutput.Replace('\','/'))';unittest.main(module=None,argv=['tests','test_runtime_scene_editor'],verbosity=1)"
    if ($LASTEXITCODE -ne 0) { throw 'Scene Editor tests failed' }
} finally { Pop-Location }
