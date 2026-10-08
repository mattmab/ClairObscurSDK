param([ValidateSet('24G', '32G')][string]$Heap = '32G')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\project-environment.ps1"
$launcher = 'D:\HobbyDevelopment\Tools\ghidra-master\build\local-install\ghidra_12.3_DEV\support\launch.bat'
if (-not (Test-Path -LiteralPath $launcher)) { throw 'Existing built Ghidra launcher is missing.' }
# Never create a second instance against the same project while recovering one.
$existing = Get-CimInstance Win32_Process -Filter "Name = 'javaw.exe' OR Name = 'java.exe'" |
    Where-Object { $_.CommandLine -match 'ghidra\.GhidraRun' }
if ($existing) { throw 'Ghidra is already running. Save and close it before launching a larger heap.' }
Start-Process -FilePath "$env:SystemRoot\System32\cmd.exe" -WindowStyle Hidden -ArgumentList "/c $launcher bg jdk Ghidra $Heap `"`" ghidra.GhidraRun"
