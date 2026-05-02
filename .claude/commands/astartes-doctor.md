---
description: Astartes 하네스 의존성 설치·상태 점검·자동 수복. /setup 대체 진입점.
argument-hint: [--force] [--browsers] [--check]
allowed-tools: Bash(bash scripts/bootstrap.sh:*), Bash(python3:*), Bash(node:*), Bash(npm:*), Bash(ls:*), Bash(which:*)
model: sonnet
---

## 옵션

| 인자 | 동작 |
|---|---|
| 없음 | 미설치 항목만 설치 (sentinel 있으면 skip) |
| `--force` | 강제 재설치 (venv·node_modules 재생성) |
| `--browsers` | Playwright 브라우저까지 설치 (~300MB) |
| `--check` | 설치 여부만 점검, 변경 없음 |

## 작업

### 1단계 — 상태 점검

다음 항목을 병렬로 확인한다:

```bash
python3 --version 2>/dev/null || echo "MISSING: python3"
node --version 2>/dev/null || echo "MISSING: node"
npm --version 2>/dev/null || echo "MISSING: npm"
ls .venv/bin/python3 2>/dev/null || echo "MISSING: .venv"
python3 -c "import openpyxl" 2>/dev/null || echo "MISSING: openpyxl"
ls outputs/web/node_modules/.bin/playwright 2>/dev/null || echo "MISSING: playwright"
ls .claude/.bootstrap_done 2>/dev/null || echo "MISSING: sentinel"
```

`--check` 인자면 점검 결과만 표로 출력하고 종료:

```
항목          | 상태
-------------|------
python3      | ✓ 3.x.x
node         | ✓ v2x.x
.venv        | ✓
openpyxl     | ✓
playwright   | ✓ / ✗ (--browsers 필요)
sentinel     | ✓ / ✗
```

### 2단계 — 설치 (--check 아닌 경우)

`bash scripts/bootstrap.sh $ARGUMENTS` 실행.

- `--force` 포함 시 sentinel 삭제 후 재실행.
- `--browsers` 포함 시 bootstrap.sh 에 전달.

### 3단계 — 설치 후 검증

설치 완료 후 1단계 점검을 재실행해 모든 항목이 ✓인지 확인.
실패 항목이 남아 있으면 원인과 해결 명령을 출력한다.

### 4단계 — 완료 보고

```
[astartes-doctor] 완료. sentinel: .claude/.bootstrap_done
다음: /astartes-tc gen-tc <url> 또는 /astartes-tc gen-tc fixture-mode
```
