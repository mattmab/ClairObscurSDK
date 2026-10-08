# Dot-source this in a project shell. Does not change global Windows settings.
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot'
$env:GRADLE_USER_HOME = 'D:\HobbyDevelopment\Caches\Gradle'
$env:PIP_CACHE_DIR = 'D:\HobbyDevelopment\Caches\pip'
$env:PYTHONPYCACHEPREFIX = 'D:\HobbyDevelopment\Caches\PythonBytecode'
$env:TEMP = 'D:\HobbyDevelopment\Caches\ClairObscurSDK'
$env:TMP = $env:TEMP
$env:PATH = "$env:JAVA_HOME\bin;D:\HobbyDevelopment\Python\expedition33-tools\Scripts;$env:PATH"
