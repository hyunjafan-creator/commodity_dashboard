@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dashboard.ps1" -NoOpen %*
exit /b %ERRORLEVEL%
