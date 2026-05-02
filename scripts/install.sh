#!/usr/bin/env bash
# Astartes 전역 설치 스크립트
# 사용: curl -fsSL https://raw.githubusercontent.com/SmallTyrant/Astartes/main/scripts/install.sh | bash
set -e

REPO="https://github.com/SmallTyrant/Astartes.git"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "[1/3] Astartes 다운로드 중..."
git clone --depth 1 --quiet "$REPO" "$TMP/astartes"

echo "[2/3] ~/.claude/ 에 설치 중..."
mkdir -p ~/.claude/agents ~/.claude/commands ~/.claude/skills ~/.claude/hooks

# 기존 파일 덮어쓰기 (에러 무시)
cp -r "$TMP/astartes/.claude/agents/."  ~/.claude/agents/  2>/dev/null || true
cp -r "$TMP/astartes/.claude/commands/." ~/.claude/commands/ 2>/dev/null || true
cp -r "$TMP/astartes/.claude/skills/."  ~/.claude/skills/  2>/dev/null || true
cp -r "$TMP/astartes/.claude/hooks/."   ~/.claude/hooks/   2>/dev/null || true

echo "[3/3] 의존성 설치 중..."
pip install openpyxl -q

echo ""
echo "✅ Astartes 설치 완료!"
echo "   → Claude Code를 재시작하면 /astartes-tc, /astartes-doctor 명령어를 사용할 수 있습니다."
