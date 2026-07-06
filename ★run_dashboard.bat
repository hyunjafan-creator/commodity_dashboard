@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Updating Commodity Dashboard + uploading to web...
echo   (takes 1-2 minutes; do NOT close this window)
echo ============================================================
echo.
echo ===== %DATE% %TIME% =====>> run.log
py run.py
echo.
echo ------------------------------------------------------------
echo   Uploading to GitHub (web dashboard)...
echo ------------------------------------------------------------
git add -A
git commit -m "update dashboard" || echo (no changes to commit)
git pull --no-edit -X ours origin main
git push
echo.
echo ============================================================
echo   [DONE]
echo   Local :  Commodity_dashboard.html   (open, press F5)
echo   Web   :  https://hyunjafan-creator.github.io/commodity_dashboard/
echo ============================================================
pause
