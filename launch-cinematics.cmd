@echo off
rem Compatibility alias: preserve Picto capabilities on Cinematics restarts.
call "%~dp0launch-sdk.cmd" %*
exit /b %errorlevel%
