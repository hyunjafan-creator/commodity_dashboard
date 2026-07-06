@echo off
cd /d "%~dp0"
echo ============================================================
echo  GitHub Upload Helper  (commodity dashboard)
echo ------------------------------------------------------------
echo  STEP 1 (do this first in your browser):
echo    - Go to  https://github.com/new
echo    - Repository name:  commodity-dashboard
echo    - Visibility:  Public   (required for free GitHub Pages)
echo    - Do NOT add README / .gitignore / license
echo    - Click "Create repository", then copy the repo URL
echo ============================================================
echo.
set /p URL="STEP 2 - Paste repo URL (https://github.com/USER/commodity-dashboard.git): "
git remote remove origin 2>nul
git remote add origin %URL%
git branch -M main
echo.
echo Pushing... (a browser window may pop up to sign in to GitHub)
git push -u origin main
echo.
echo ============================================================
echo  STEP 3 - Enable GitHub Pages:
echo    Repo -^> Settings -^> Pages
echo    Source: Deploy from a branch
echo    Branch: main   Folder: / (root)   -^> Save
echo.
echo  After ~1 minute your dashboard will be live at:
echo    https://USER.github.io/commodity-dashboard/
echo ============================================================
pause
