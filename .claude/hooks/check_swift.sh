#!/usr/bin/env bash
# Swift 구문 검증 hook (swiftc -parse). swiftc 미설치 시 skip.
set -euo pipefail
FILE="${FILE_PATH:-${1:-}}"
if [ -z "$FILE" ] && ! [ -t 0 ]; then
  FILE="$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path') or d.get('file_path') or '')" 2>/dev/null || true)"
fi
[ -z "$FILE" ] || [ ! -f "$FILE" ] && exit 0

if ! command -v swiftc >/dev/null 2>&1; then
  echo "[check_swift] swiftc 미설치, skip ($FILE)" >&2
  exit 0
fi

if ! swiftc -parse "$FILE" 2>&1; then
  echo "[check_swift] $FILE 구문 오류" >&2
  exit 2
fi
exit 0
