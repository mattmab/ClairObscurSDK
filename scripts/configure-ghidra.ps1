param([Parameter(Mandatory=$true)][string]$InstallDirectory)
$ErrorActionPreference = 'Stop'
$installRoot = (Resolve-Path -LiteralPath $InstallDirectory).Path
if (-not $installRoot.StartsWith('D:\HobbyDevelopment\Tools\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Configure only the project Ghidra build under D:\HobbyDevelopment\Tools.'
}
$properties = Join-Path $installRoot 'support\launch.properties'
if (-not (Test-Path -LiteralPath (Join-Path $installRoot 'Ghidra\application.properties'))) {
    throw 'Expected a built Ghidra distribution.'
}
$original = Get-Content -LiteralPath $properties -Raw
$marker = '# ClairObscurSDK local research directories'
if ($original.Contains($marker)) {
    Write-Output 'Project directory configuration already present.'
    exit 0
}
$settings = 'D:/HobbyDevelopment/Analysis/ClairObscurSDK/settings'
$cache = 'D:/HobbyDevelopment/Caches/Ghidra'
$temporary = 'D:/HobbyDevelopment/Caches/Ghidra/temp'
foreach ($directory in @($settings, $cache, $temporary)) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}
# LaunchSupport reads launch.properties before launching Ghidra, so caller-only
# JVM arguments would not redirect its saved JDK selection.
$configuration = @"

$marker
VMARGS=-Dapplication.settingsdir=$settings
VMARGS=-Dapplication.cachedir=$cache
VMARGS=-Dapplication.tempdir=$temporary
VMARGS=-Djava.io.tmpdir=$temporary
"@
Add-Content -LiteralPath $properties -Value $configuration
Write-Output "Configured Ghidra state directories in $properties"
