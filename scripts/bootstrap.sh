#!/usr/bin/env bash
# Astartes 하네스 부트스트랩 (멱등).
# - Python venv + pip 의존성 (.venv)
# - outputs/web 노드 의존성 (Playwright + TypeScript)
# - sentinel: .claude/.bootstrap_done
# 사용:
#   scripts/bootstrap.sh           # sentinel 있으면 skip
#   scripts/bootstrap.sh --force   # 강제 재설치
#   scripts/bootstrap.sh --browsers # Playwright 브라우저까지 설치 (수백 MB)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SENTINEL="$ROOT/.claude/.bootstrap_done"
FORCE=0
INSTALL_BROWSERS=0
QUIET=0

for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --browsers) INSTALL_BROWSERS=1 ;;
    --quiet) QUIET=1 ;;
  esac
done

log() { [ "$QUIET" -eq 1 ] || echo "[bootstrap] $*"; }
warn() { echo "[bootstrap] $*" >&2; }

if [ "$FORCE" -eq 0 ] && [ -f "$SENTINEL" ]; then
  log "이미 완료됨 ($SENTINEL). --force로 재실행."
  exit 0
fi

log "Astartes 하네스 부트스트랩 시작"

# 1) Python venv + 의존성
PYTHON="${PYTHON:-python3}"
VENV="$ROOT/.venv"
if [ ! -d "$VENV" ]; then
  log "venv 생성: $VENV"
  "$PYTHON" -m venv "$VENV"
fi

VENV_PY="$VENV/bin/python"
VENV_PIP="$VENV/bin/pip"

if [ -f "$ROOT/scripts/requirements.txt" ]; then
  log "pip 의존성 설치 (requirements.txt)"
  "$VENV_PIP" install --upgrade pip --quiet
  "$VENV_PIP" install -r "$ROOT/scripts/requirements.txt" --quiet
else
  warn "scripts/requirements.txt 없음, pip 단계 skip"
fi

# 2) outputs/web 노드 의존성
WEB_ROOT="$ROOT/outputs/web"
mkdir -p "$WEB_ROOT"

if command -v npm >/dev/null 2>&1; then
  if [ ! -f "$WEB_ROOT/package.json" ]; then
    log "outputs/web/package.json 생성"
    cat > "$WEB_ROOT/package.json" <<'JSON'
{
  "name": "astartes-web-tests",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "playwright test",
    "typecheck": "tsc --noEmit -p ."
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "typescript": "^5.6.0"
  }
}
JSON
  fi
  if [ ! -f "$WEB_ROOT/tsconfig.json" ]; then
    log "outputs/web/tsconfig.json 생성"
    cat > "$WEB_ROOT/tsconfig.json" <<'JSON'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "types": ["node"],
    "noEmit": true
  },
  "include": ["tests/**/*.ts", "pages/**/*.ts", "fixtures/**/*.ts"]
}
JSON
  fi
  if [ ! -f "$WEB_ROOT/playwright.config.ts" ]; then
    log "outputs/web/playwright.config.ts 생성"
    cat > "$WEB_ROOT/playwright.config.ts" <<'TS'
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  reporter: [['list']],
  use: {
    baseURL: process.env.BASE_URL,
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
  ],
});
TS
  fi
  if [ ! -d "$WEB_ROOT/node_modules" ] || [ "$FORCE" -eq 1 ]; then
    log "npm install (outputs/web/)"
    (cd "$WEB_ROOT" && npm install --silent --no-audit --no-fund)
  else
    log "outputs/web/node_modules 이미 존재"
  fi
  if [ "$INSTALL_BROWSERS" -eq 1 ]; then
    log "Playwright 브라우저 설치 (chromium/webkit/firefox)"
    (cd "$WEB_ROOT" && npx --no-install playwright install)
  fi
else
  warn "npm 미설치 — outputs/web 단계 skip. Web TC 자동화는 npm 설치 후 다시 실행하세요."
fi

# 3) inputs 하위 raw 디렉토리 사전 확보 (mkdir 권한이 있는 곳만)
mkdir -p "$ROOT/inputs/figma/raw" "$ROOT/inputs/figma/export" \
         "$ROOT/inputs/pdf/raw" "$ROOT/inputs/slack/raw" \
         "$ROOT/inputs/notion/raw" 2>/dev/null || true

# 4) sentinel 기록
mkdir -p "$(dirname "$SENTINEL")"
cat > "$SENTINEL" <<EOF
ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
python_venv=$VENV
python_version=$("$VENV_PY" --version 2>&1 || echo "unknown")
npm_present=$(command -v npm >/dev/null 2>&1 && echo yes || echo no)
playwright_browsers=$([ "$INSTALL_BROWSERS" -eq 1 ] && echo installed || echo deferred)
EOF

log "완료. sentinel: $SENTINEL"
log "Python: source .venv/bin/activate 또는 .venv/bin/python 사용"
[ "$INSTALL_BROWSERS" -eq 0 ] && log "Playwright 브라우저는 미설치. 필요 시: scripts/bootstrap.sh --browsers"
