#!/usr/bin/env bash
# TypeScript 구문 검증 hook. tsc 또는 eslint 미설치 시 skip.
set -euo pipefail
FILE="${FILE_PATH:-${1:-}}"
if [ -z "$FILE" ] && ! [ -t 0 ]; then
  FILE="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path') or d.get('file_path') or '')" 2>/dev/null || true)"
fi
[ -z "$FILE" ] || [ ! -f "$FILE" ] && exit 0

WEB_ROOT="$(cd "$(dirname "$0")/../../outputs/web" 2>/dev/null && pwd || true)"

# 1차: outputs/web/tsconfig.json + node_modules 존재하면 tsc로 풀 검증
if [ -n "$WEB_ROOT" ] && [ -f "$WEB_ROOT/tsconfig.json" ] && [ -d "$WEB_ROOT/node_modules" ]; then
  if (cd "$WEB_ROOT" && npx --no-install tsc --noEmit -p . 2>&1); then
    exit 0
  else
    echo "[check_typescript] $FILE tsc 검증 실패" >&2
    exit 2
  fi
fi

# 2차: tsc만 단독 사용 (의존성 부족하면 skip 처리)
if command -v npx >/dev/null 2>&1; then
  OUT="$(npx --no-install tsc --noEmit --target ES2022 --module commonjs --allowJs --skipLibCheck "$FILE" 2>&1 || true)"
  if echo "$OUT" | grep -qE "Cannot find module|Cannot find name '(test|expect|playwright)'|node_modules"; then
    echo "[check_typescript] node_modules 미설치, syntax-only fallback 권장: $FILE" >&2
    exit 0
  fi
  if echo "$OUT" | grep -qE "error TS"; then
    echo "$OUT" >&2
    echo "[check_typescript] $FILE 구문 오류" >&2
    exit 2
  fi
fi

exit 0
