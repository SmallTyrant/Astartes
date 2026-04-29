#!/usr/bin/env bash
# Kotlin 구문 lint hook (ktlint). ktlint 미설치 시 skip.
set -euo pipefail
FILE="${FILE_PATH:-${1:-}}"
if [ -z "$FILE" ] && ! [ -t 0 ]; then
  FILE="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path') or d.get('file_path') or '')" 2>/dev/null || true)"
fi
[ -z "$FILE" ] || [ ! -f "$FILE" ] && exit 0

if ! command -v ktlint >/dev/null 2>&1; then
  echo "[check_kotlin] ktlint 미설치, skip ($FILE)" >&2
  exit 0
fi

if ! ktlint "$FILE" 2>&1; then
  echo "[check_kotlin] $FILE lint 실패" >&2
  exit 2
fi
exit 0
