param([ValidateRange(1,99)][int]$Version=12,[switch]$SceneEditor)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskBuild = Join-Path $taskRoot 'build/release/runtime-cinematic-build'
New-Item -ItemType Directory -Path $taskBuild -Force | Out-Null
$taskOriginal = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build-zone-travel-candidate.cmd') -Raw
$taskContent = $taskOriginal.Replace('/DE33_ZONE_TRAVEL_SESSION', "/DE33_RUNTIME_CINEMATIC_VERSION=$Version /DE33_RUNTIME_CINEMATIC_SESSION /DE33_ZONE_TRAVEL_SESSION")
if ($SceneEditor) { $taskContent = $taskContent.Replace('/DE33_RUNTIME_CINEMATIC_SESSION','/DE33_RUNTIME_CINEMATIC_SESSION /DE33_RUNTIME_SCENE_EDITOR_SESSION') }
$taskContent = $taskContent.Replace('runtime-session-zone-v68', "runtime-session-cinematic-v$Version").Replace('runtime_session_zone_v68', "runtime_session_cinematic_v$Version").Replace('research-probe-zone-v68', "research-probe-cinematic-v$Version")
$taskContent = $taskContent.Substring(0, $taskContent.IndexOf('if not exist "%PROJECT_ROOT%\build\release\thumbnail-worker-v2"')) + "exit /b %BUILD_RESULT%`r`n"
# Keep the existing source-root calculation: this generated file lives in scripts.
$taskGenerated = Join-Path $PSScriptRoot 'build-runtime-cinematic-generated.cmd'
[IO.File]::WriteAllText($taskGenerated, $taskContent, [Text.Encoding]::ASCII)
$taskWrapper = Join-Path $taskBuild 'build.cmd'
$taskCommands = "@echo off`r`ncall D:\HobbyDevelopment\Tools\VSBuildTools\VC\Auxiliary\Build\vcvarsall.bat x64`r`nif errorlevel 1 exit /b %errorlevel%`r`ncall `"$taskGenerated`"`r`n"
[IO.File]::WriteAllText($taskWrapper, $taskCommands, [Text.Encoding]::ASCII)
& $env:ComSpec /d /c $taskWrapper
if ($LASTEXITCODE -ne 0) { throw "Native cinematic candidate build failed: $LASTEXITCODE" }
