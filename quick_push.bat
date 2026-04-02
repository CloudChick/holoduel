@echo off
echo HoloDuel Server - Quick Push
echo ============================

REM Commit local changes first
git add .
git commit -m "Update server files - %date% %time%"

REM Pull remote changes with rebase
git pull --rebase origin main

REM Push to GitHub
git push origin main

echo.
echo Push complete!
pause
