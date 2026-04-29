# Astartes — 디자인-to-TC 자동생성 하네스 (+ astartes-tc 스킬)

Figma · PDF · Notion · Slack · PRD/API 스펙으로부터 iOS / Android / Web 3개 플랫폼의 테스트 케이스(TC)와 자동화 스켈레톤을 자동 생성하는 Claude Code 기반 하네스. **TC 시트 작성 노하우(한국 QA 표준 포맷)는 `astartes-tc` skill 로 응축되어 있다.**

## 한 눈에 보기

```
입력           →  하네스 + 스킬     →  산출물
─────────────────────────────────────────────────────────────────
Figma URL          /gen-tc           outputs/testcases/{screen}_{platform}.json
PDF                /astartes-tc:astartes-tc
                                     outputs/sheets/{appname}.xlsx  ← 단일 워크북
Notion 페이지                         outputs/{ios,android,web}/  (자동화 코드)
Slack 스레드                          outputs/traceability.csv
PRD/API 스펙                          outputs/intermediate/coverage-gaps.json
```

도메인 비특화. 어떤 분야의 디자인/문서든 입력만 주어지면 TC가 생성된다.

## 패키지 구성

이 저장소는 두 가지 자산을 제공한다:

| 자산 | 위치 | 역할 |
| ---- | ---- | ---- |
| **astartes-tc plugin** | `.claude/.claude-plugin/plugin.json` | 13개 subagent + 2개 slash command + hooks + 1개 skill 묶음 |
| **astartes-tc skill** | `.claude/skills/astartes-tc/` | TC JSON → 한국 QA 표준 XLSX 변환 노하우 (시트 골자/Step 분해/수식 사양) |

플러그인은 프로젝트-로컬(`.claude/`)로 묶여 있어 이 저장소를 clone 한 디렉토리에서 Claude Code 를 열면 자동으로 인식된다. marketplace 업로드는 별도 단계.

## 빠른 시작 (3분)

### 1. 의존성 부트스트랩

세션 시작 시 자동으로 1회 실행되지만, 명시 호출도 가능:

```
/setup
```

수행: `.venv` 생성 → `pip install -r scripts/requirements.txt` → `outputs/web/`에 `package.json`/`tsconfig.json`/`playwright.config.ts` 배치 → `npm install` (Playwright + TypeScript). sentinel `.claude/.bootstrap_done`로 멱등.

옵션:
- `/setup --force` — 강제 재설치
- `/setup --browsers` — Playwright 브라우저까지 (~300MB, 시간 소요)

### 2. 입력 준비

방식 A (링크): 토큰 환경변수 export 후 source-spec.

```bash
export FIGMA_TOKEN=...
export NOTION_TOKEN=...
export SLACK_TOKEN=...
```

방식 B (로컬 드롭): `inputs/{figma,notion,slack}/export/`와 `inputs/pdf/`에 파일 그대로 두기.

방식 C (테스트): `tests/fixtures/sample-*` 가 이미 있어 토큰/드롭 없이 즉시 검증 가능.

상세는 [`inputs/README.md`](./inputs/README.md).

### 3. 실행

```
/gen-tc <source-spec> [platforms]
```

| 호출 | 의미 |
|---|---|
| `/gen-tc fixture-mode` | 픽스처로 3 플랫폼 모두 생성 (가장 빠른 검증) |
| `/gen-tc local` | 로컬 드롭한 파일로 3 플랫폼 모두 생성 |
| `/gen-tc local web` | 로컬 드롭으로 Web만 생성 |
| `/gen-tc figma:URL,pdf:./inputs/pdf/x.pdf` | 링크 + PDF, 3 플랫폼 모두 |
| `/gen-tc figma:URL,notion:URL ios,web` | 링크 입력, iOS+Web만 |
| `/gen-tc local,figma:URL ios` | 로컬+링크 혼용, iOS만 |

`platforms` 인자 생략 시 `ios,android,web` 기본.

## 명령 레퍼런스

| 명령 | 역할 |
|---|---|
| `/setup [--force] [--browsers]` | 의존성 부트스트랩 (Python venv + npm + Playwright) |
| `/gen-tc <source-spec> [platforms]` | 전체 파이프라인 실행 (10단계, 디자인-루프 포함) |
| `/astartes-tc:astartes-tc` | TC JSON → 한국 QA 표준 XLSX 워크북 변환 (단독 호출 가능) |

`/gen-tc` 의 step 8 은 내부적으로 `astartes-tc` skill 을 호출한다. JSON 만 손으로 손봤다면 `/astartes-tc:astartes-tc` 단독 호출로 워크북만 다시 만들 수 있다.

> **호출 형식 주의**: 이 skill 은 `astartes-tc` plugin 안에 들어 있어서 **반드시 `<plugin-name>:<skill-name>` 네임스페이스**로 호출해야 한다. `/astartes-tc` 또는 `/astartes` 단독은 동작하지 않는다 (Claude Code 공식 동작).

## astartes-tc 스킬 단독 사용

다른 프로젝트에서도 이 skill 만 떼어 쓸 수 있다.

### 1. 호출 방법 (3가지)

| 시점 | 호출 |
| ---- | ---- |
| Claude 가 자동 판단 | `outputs/testcases/*.json` 가 보이거나 사용자가 "시트로 뽑아줘" 같이 말하면 SKILL.md frontmatter 의 description 매칭으로 자동 invoke |
| 사용자 명시 호출 | `/astartes-tc:astartes-tc` 입력 (plugin 네임스페이스 필수) |
| CLI 직접 호출 | `python3 .claude/skills/astartes-tc/scripts/export_workbook.py <appname>` |

### 2. 입력 / 출력 계약

- 입력: `outputs/testcases/*.json` (v3 스키마, `screen` + `platform` + `steps[1~5]` + `result=""` 필수)
- 출력: `outputs/sheets/<appname>.xlsx` (단일 워크북)
  - 시트 0 `summury` — 환경 블록 + 통계 표 (검증항목/Pass/Fail/Block/N/A/성공율/결함율/수행율)
  - 시트 1+ `{screen}_{platform}` — TC 1건당 1행

### 3. 시트 골자 (skill 이 강제하는 5가지 불변)

1. **앱당 1 워크북**. 화면별 CSV 분리 금지.
2. **레이아웃 고정**: 컬럼 A 비움 / Row 1 비움 / Row 2 헤더(B~L: `TC ID, priority, 1 Step ~ 5 Step, pre-condition, 기대결과, result, Jira ticket`) / Row 3+ 데이터.
3. **priority 조건부 서식**: `high`=빨강(#E06666 흰 글씨), `mid`=노랑(#FFD966), `low`=초록(#93C47D).
4. **result 컬럼**: 드롭다운 옵션 `Pass / Fail / Block / N/A`. **기본값은 빈 칸** (QA 가 실행 후 채움). 드롭다운 범위는 데이터 행만 (`K3:K{last_row}`).
5. **summury 통계는 수식**: 직접 입력 금지. `=COUNTA('탭'!B3:B{N})`, `=COUNTIF('탭'!K3:K{N},"Pass")` — **명시적 마지막 행 번호**. open-ended (`K3:K`)는 `#NAME?` 발생.

### 4. Step 분해 규칙

**1 버튼 / 1 옵션 탭 = 1 step**. 한 step 에 여러 동작을 묶지 않는다.

```
나쁨: "라이브러리 '+' 버튼에서 '폴더'를 선택해 'Q2'를 생성한다"
좋음: ["'+' 버튼을 탭한다",
       "'폴더' 옵션을 탭한다",
       "이름 입력 필드에 'Q2'를 입력한다",
       "'생성' 버튼을 탭한다"]
```

5 step 한도(`1 Step ~ 5 Step`)는 절대 한도. 더 길면 사전조건으로 압축하거나 시나리오를 둘로 쪼갠다. 자세한 어휘·예시는 [`.claude/skills/astartes-tc/references/step-decomposition.md`](./.claude/skills/astartes-tc/references/step-decomposition.md).

### 5. 다른 프로젝트로 이식

skill 디렉토리만 통째로 복사:

```bash
cp -r .claude/skills/astartes-tc /path/to/other-project/.claude/skills/
```

또는 사용자 전역(`~/.claude/skills/`)에 두면 모든 프로젝트에서 호출 가능. 의존성은 `pip install openpyxl` 한 줄.

### 6. skill 내부 문서

- [`.claude/skills/astartes-tc/SKILL.md`](./.claude/skills/astartes-tc/SKILL.md) — frontmatter + 6개 본문 섹션 (언제 사용 / 골자 / Step 분해 / 워크플로우 / 금지 사항 / 참고)
- [`.claude/skills/astartes-tc/references/sheet-layout.md`](./.claude/skills/astartes-tc/references/sheet-layout.md) — 셀 좌표·색상 hex·수식 패턴 전체 사양
- [`.claude/skills/astartes-tc/references/step-decomposition.md`](./.claude/skills/astartes-tc/references/step-decomposition.md) — Step 분해 사례·어휘·5 step 한도 처리법
- [`.claude/skills/astartes-tc/references/tc-schema-v3.md`](./.claude/skills/astartes-tc/references/tc-schema-v3.md) — TC JSON v3 스키마

## 파이프라인 10 단계

1. **mcp-ingester** — source-spec 페치 → `inputs/{type}/raw/`
2. **requirement-analyzer** — 입력 통합 → `outputs/intermediate/req-model.json` (모든 행위에 `source_refs`)
3. **tc-reviewer dedup** — 기존 TC와 0.85 이상 유사 차단
4. 병렬: **tc-gen-functional / security / negative** → 카테고리별 TC 생성
5. **tc-reviewer judge** — 평균 4점 미만 또는 고위험 risk_tag P0 0개면 reject
6. **tc-normalizer** → `testcases.reviewed.json` (플랫폼 중립)
7. **tc-platform-splitter** → `testcases.{ios,android,web}.final.json` (선택 플랫폼만)
8. 병렬 **codegen-{ios,android,web}** → 각 자동화 코드
9. **coverage-auditor** → `traceability.csv` + `coverage-gaps.json`
10. **디자인-루프** (max 3 iter) — figma source_ref 미커버 시 gap만 입력으로 4~9 재실행. cap 도달 시 잔여는 `needs_review: true` 부착 후 종료.

각 단계는 `.claude/agents/*.md`에 정의된 서브 에이전트가 담당.

## 산출물 구조

```
outputs/
├── intermediate/
│   ├── req-model.json                    # 행위 모델 (source_refs 포함)
│   ├── tc-{functional,security,negative}.json
│   ├── tc-reviewed.json                  # 리뷰·정규화 통과본 (탭 분리 전)
│   └── coverage-gaps.json                # 디자인-루프 신호
├── testcases/
│   ├── {screen-slug}_{and|ios|web}.json  # 시트 탭 단위 최종 JSON (v3 스키마)
│   └── automation_candidates.json
├── sheets/
│   └── {appname}.xlsx                    # 앱당 1개 워크북 (summury + 탭들, astartes-tc skill 출력)
├── ios/{Tests,PageObjects,Fixtures}/
├── android/{tests,screens,fixtures}/
├── web/{tests,pages,fixtures}/
└── traceability.csv                      # 요구사항 ↔ TC ↔ source_ref 추적성
```

## TC JSON 스키마 (v3, 시트 형식 통일)

기준 스프레드시트 컬럼과 1:1 정합:

```
TC ID | priority | 1 Step | 2 Step | 3 Step | 4 Step | 5 Step | pre-condition | 기대결과 | result | Jira ticket
```

필수 필드: `tc_id`, `screen`, `platform` (`and|ios|web`), `priority` (`high|mid|low`), `precondition`, `steps[]` (1~5), `expected`, `jira_ticket`, `result` (항상 `""`).

JSON 내부 전용(시트 export 시 제외): `requirement_id`, `source_refs[]`, `risk_tags[]`, `negative`, `needs_review`.

전체 사양·구 스키마 호환성은 [`.claude/skills/astartes-tc/references/tc-schema-v3.md`](./.claude/skills/astartes-tc/references/tc-schema-v3.md).

## 디자인-루프 동작

`coverage-auditor`가 매 iter 끝에 `coverage-gaps.json`을 본다.

```json
{
  "iteration": 1,
  "primary_design_gaps": [
    { "type": "figma", "id": "1:234", "locator": "Frame/Login/Button" }
  ],
  "complete": false
}
```

- `complete=true` (figma 0건 누락) → 즉시 종료.
- 그 외 → gap만 입력으로 `tc-gen-*` 재호출, `tc-normalizer mode=merge`로 append, splitter/codegen/auditor 재실행.
- iter 3 도달 → 잔여 gap에 placeholder TC + `needs_review: true` 부착 후 종료.

## 자동화 코드 컨벤션

- **iOS**: XCTest + XCUITest. accessibility identifier만 매칭. `outputs/ios/PageObjects/{Screen}Page.swift`
- **Android**: Espresso + Kotlin coroutines. `onView(withId(R.id...))`만 매칭. `outputs/android/screens/{Screen}Screen.kt`
- **Web**: Playwright + TypeScript. `page.getByTestId()`만 매칭(텍스트/CSS selector 금지). `outputs/web/pages/{Screen}Page.ts`
- 공통: 텍스트/하드코딩 매칭 금지. fixture 또는 환경변수로 데이터 주입.

## 보안·PII 정책

- PII/시크릿(주민번호 · 계좌번호 · OTP · 토큰 · API 키) 평문 포함·하드코딩 금지.
- `.env` / `.env.*` 파일 read 차단.
- PreToolUse 훅 `mask_pii.sh`가 Write/Edit 직전 검사.
- 보안 TC는 `risk_tags[]`에 `auth/session/data/input/network/storage/payment` 중 1개 이상 필수 (없으면 PostToolUse 훅이 차단).

## 디렉토리 구조 (요약)

```
.
├── README.md                # 본 문서
├── CLAUDE.md                # Claude용 프로젝트 지침
├── .claude/
│   ├── .claude-plugin/
│   │   └── plugin.json      # plugin manifest (astartes-tc)
│   ├── settings.json        # 권한 / 훅
│   ├── agents/              # 13 서브 에이전트
│   ├── commands/            # /setup, /gen-tc
│   ├── hooks/               # mask_pii, validate_tc_schema, check_*
│   └── skills/
│       └── astartes-tc/     # ← TC 시트 작성 스킬
│           ├── SKILL.md
│           ├── scripts/export_workbook.py
│           └── references/{sheet-layout,step-decomposition,tc-schema-v3}.md
├── inputs/                  # 사용자 입력 (상세: inputs/README.md)
├── outputs/                 # 산출물 (sheets/만 git 포함, 나머지는 gitignore)
│   └── sheets/{appname}.xlsx
├── scripts/                 # bootstrap.sh, fetch_*, parse_pdf, dedupe, traceability
├── tests/fixtures/          # E2E 픽스처
└── .venv/                   # Python venv (gitignore)
```

## 트러블슈팅

| 증상 | 원인·조치 |
|---|---|
| `/setup`이 의존성 설치 안 함 | sentinel `.claude/.bootstrap_done` 존재. `/setup --force`로 강제 재실행 |
| `FIGMA_TOKEN not set` 같은 stderr | 토큰 누락. shell에서 `export FIGMA_TOKEN=...` 후 재시도 (해당 소스만 skip되고 다른 소스는 진행) |
| MCP 서버 미등록 | 자동으로 `scripts/fetch_*.py` 폴백. 사용자 조치 불필요 |
| `coverage-gaps.json`이 계속 비지 않음 | iter 3 도달 시 `needs_review: true`로 종료. 해당 source_ref를 직접 검토 후 `inputs/`에 보강 |
| `validate_tc_schema.py` PostToolUse 차단 | `risk_tags`/`source_refs` 누락. TC JSON 점검 후 재시도 |
| Web TC 작성 시 `getByText` 사용했다며 reject | data-testid 매칭 강제. 디자인 시안에 testid 부여를 요청 |
| 단일 `.ts` 파일 tsc 실패 | `outputs/web/node_modules` 누락. `/setup` 재실행 |

## 참고 문서

- [`CLAUDE.md`](./CLAUDE.md) — Claude Code용 프로젝트 지침
- [`.claude/skills/astartes-tc/SKILL.md`](./.claude/skills/astartes-tc/SKILL.md) — TC 시트 스킬 진입점
- [`.claude/skills/astartes-tc/references/`](./.claude/skills/astartes-tc/references/) — 시트 레이아웃·step 분해·v3 스키마 사양
- [`inputs/README.md`](./inputs/README.md) — 입력 경로(링크/로컬/픽스처) 상세
- `.claude/agents/*.md` — 13개 서브 에이전트 명세
- `.claude/commands/*.md` — 슬래시 명령 정의
