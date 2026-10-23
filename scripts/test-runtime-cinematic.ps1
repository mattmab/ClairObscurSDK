$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskOutput=Join-Path $taskRoot '.test-tmp/runtime-cinematic'
New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
$taskWrapper=Join-Path $taskOutput 'native-test.cmd'
$taskText="@echo off`r`ncall D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64`r`nif errorlevel 1 exit /b %errorlevel%`r`ncd /d `"$taskOutput`"`r`ncl /nologo /W4 /WX /EHsc /std:c++17 /O2 /Fe:runtime_cinematic_timing_fixture.exe `"$taskRoot\native\runtime_cinematic_timing_fixture.cpp`"`r`nif errorlevel 1 exit /b %errorlevel%`r`nruntime_cinematic_timing_fixture.exe`r`n"
[IO.File]::WriteAllText($taskWrapper,$taskText,[Text.Encoding]::ASCII)
& $env:ComSpec /d /c $taskWrapper
if($LASTEXITCODE -ne 0){throw 'Native timing fixture failed'}
Push-Location $taskRoot
try {
    & "$taskRoot/runtime/python.exe" -I -S -B -c "import sys,tempfile,unittest;sys.path[:0]=['src','tests'];tempfile.tempdir='$($taskOutput.Replace('\','/'))';unittest.main(module=None,argv=['tests','test_runtime_cinematic_demo','test_runtime_cinematic_wire','test_invocation','test_pod_invocation','test_sequence_camera_owner','test_sequence_binding_query','test_media_audio_timeline','test_mod_archive'],verbosity=1)"
    if($LASTEXITCODE -ne 0){throw 'Python cinematic regression tests failed'}
} finally {Pop-Location}
