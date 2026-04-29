#!/usr/bin/env bash
# PII 마스킹 hook - 출력 파일에 실 계좌/주민번호/카드번호 패턴이 있으면 차단.
# 입력: stdin JSON에서 file_path 또는 환경변수 FILE_PATH 또는 $1.
set -euo pipefail

# 다양한 호출 컨벤션 대응
INPUT_JSON=""
if ! [ -t 0 ]; then INPUT_JSON="$(cat || true)"; fi
FILE="${FILE_PATH:-${1:-}}"
if [ -z "$FILE" ] && [ -n "$INPUT_JSON" ]; then
  FILE="$(echo "$INPUT_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path') or d.get('file_path') or '')" 2>/dev/null || true)"
fi
[ -z "$FILE" ] || [ ! -f "$FILE" ] && exit 0

# inputs/는 검사 제외 (정상 fixture sqlite 등)
case "$FILE" in inputs/*) exit 0 ;; esac

VIOLATIONS=()

# 주민등록번호 (6자리-7자리, 7번째 자리 1~4)
if grep -nE '\b[0-9]{6}-[1-4][0-9]{6}\b' "$FILE" >/dev/null 2>&1; then
  VIOLATIONS+=("주민등록번호 패턴 발견")
fi

# 카드번호 (16자리 연속 또는 4-4-4-4)
if grep -nE '\b[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}\b' "$FILE" >/dev/null 2>&1; then
  VIOLATIONS+=("카드번호 패턴 발견")
fi

# 계좌번호 하드코딩 (account: "10자리 이상 숫자")
if grep -niE '"account(_?number)?"\s*:\s*"[0-9]{10,}"' "$FILE" >/dev/null 2>&1; then
  VIOLATIONS+=("계좌번호 하드코딩 의심")
fi

# OTP/보안카드 값 하드코딩
if grep -niE '"(otp|security_card|securityCard)"\s*:\s*"?[0-9]{4,8}"?' "$FILE" >/dev/null 2>&1; then
  VIOLATIONS+=("OTP/보안카드 값 하드코딩")
fi

if (( ${#VIOLATIONS[@]} > 0 )); then
  echo "[mask_pii] $FILE 차단:" >&2
  for v in "${VIOLATIONS[@]}"; do echo "  - $v" >&2; done
  echo "fixture로 대체하세요 (outputs/{ios,android}/Fixtures/)." >&2
  exit 2
fi
exit 0
