@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===== %DATE% %TIME% (auto/local) =====>> run.log
py run.py >> run.log 2>&1
git add -A >> run.log 2>&1
git commit -m "local auto-update" >> run.log 2>&1
git pull --no-edit -X ours origin main >> run.log 2>&1
git push >> run.log 2>&1
