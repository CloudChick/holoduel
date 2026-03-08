#!/bin/bash
echo "HoloDuel Server - Quick Push"
echo "============================"

# 모든 변경사항 추가 및 커밋
git add .
git commit -m "Update server files - $(date '+%Y-%m-%d %H:%M:%S')"

# GitHub에 push (main 브랜치)
git push origin main

echo ""
echo "Push 완료!"
