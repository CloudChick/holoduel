#!/bin/bash
echo "HoloDuel Server - Quick Push"
echo "============================"

# 로컬 변경사항 먼저 커밋
git add .
git commit -m "Update server files - $(date '+%Y-%m-%d %H:%M:%S')"

# 원격 변경사항 pull (rebase로 히스토리 정리)
git pull --rebase origin main

# GitHub에 push
git push origin main

echo ""
echo "Push 완료!"
