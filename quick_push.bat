@echo off
echo HoloDuel Server - Quick Push
echo ============================

REM 로컬 변경사항 먼저 커밋
git add .
git commit -m "Update server files - %date% %time%"

REM 원격 변경사항 pull (rebase로 히스토리 정리)
git pull --rebase origin main

REM GitHub에 push
git push origin main

echo.
echo Push 완료!
pause