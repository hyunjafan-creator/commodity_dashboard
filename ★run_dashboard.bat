@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Updating Commodity Dashboard...  (takes 1-2 minutes)
echo   Do NOT close this window until it finishes!
echo ============================================================
echo.
echo ===== %DATE% %TIME% =====>> run.log
py run.py
echo.
echo ============================================================
echo   [DONE] Open / refresh (F5):  Commodity_dashboard.html
echo ============================================================
pause
