@echo off
call "%~dp0launch.cmd" management --keybinds --pause-menu %*
exit /b %errorlevel%
