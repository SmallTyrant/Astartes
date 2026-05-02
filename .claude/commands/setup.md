---
description: Astartes 하네스 의존성 부트스트랩 (venv + Playwright/TS). sentinel 있으면 skip.
argument-hint: [--force] [--browsers]
allowed-tools: Bash(bash scripts/bootstrap.sh:*), Bash(scripts/bootstrap.sh:*)
model: sonnet
---

## 작업

`scripts/bootstrap.sh $1 $2` 를 실행한다.

옵션:
- 인자 없음 → 처음 1회 설치 (sentinel 있으면 skip)
- `--force` → 강제 재설치 (venv·node_modules 재생성)
- `--browsers` → Playwright 브라우저까지 설치 (수백 MB, 시간 소요)

실행 후 sentinel 위치(`.claude/.bootstrap_done`)와 다음 단계 안내를 1줄 보고.
