@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_dashboard.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" echo [DONE] Latest local dashboard opened. Web deployment may take a few minutes.
if "%RESULT%"=="2" echo [PARTIAL] Some sources need attention. See run.log and dashboard source dates.
if "%RESULT%"=="1" echo [FAILED] Update or upload failed. See run.log for details.
pause
exit /b %RESULT%
