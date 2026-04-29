---
description: 디자인/문서 입력으로부터 시트 형식 TC 풀세트 생성 (수집→분석→중복검사→생성→정규화→탭분리→시트export→코드젠→감사→디자인루프)
argument-hint: <source-spec> [platforms]
allowed-tools: Read, Glob, Grep, Bash(git diff:*), Bash(ls:*), Bash(python3 scripts/fetch_figma.py:*), Bash(python3 scripts/fetch_notion.py:*), Bash(python3 scripts/fetch_slack.py:*), Bash(python3 scripts/parse_pdf.py:*), Bash(python3 .claude/skills/tc-sheet/scripts/export_workbook.py:*), Bash(npx:*)
model: sonnet
---

## 컨텍스트
- 변경된 입력: !`git diff --name-only HEAD~1 -- inputs 2>/dev/null || echo "diff unavailable"`
- 기존 TC 카운트: !`ls outputs/testcases 2>/dev/null | wc -l`
- 캐시된 inputs/raw: !`ls inputs/figma/raw inputs/notion/raw inputs/slack/raw inputs/pdf/raw 2>/dev/null | head -20`

## 작업

source-spec: $1   (예: `figma:URL,notion:URL,slack:URL,pdf:./inputs/pdf/x.pdf`, `local`, `fixture-mode`, 또는 혼용 `local,figma:URL`)
platforms: $2     (예: `ios,android,web` 또는 일부; Android는 시트 키 "and"로 매핑됨)

**$2 미지정/빈 문자열이면 platforms = `"ios,android,web"` 으로 정규화한다.** 이하 단계에서 `target_platforms = $2 || "ios,android,web"`.

**스키마**: 모든 TC는 v3 (시트 형식 통일)을 따른다. 자세한 스키마/시트 컬럼 매핑은 CLAUDE.md 참조.

순서대로:

1. **`mcp-ingester`** 서브에이전트로 source-spec 페치. MCP 서버 우선, 없으면 fetcher 폴백. `local` 토큰이면 `inputs/{type}/export/`를 스캔해 `raw/`로 정규화 복사. `fixture-mode`면 `tests/fixtures/sample-*`를 사용.
   - 결과: `inputs/{figma,notion,slack,pdf}/raw/*.json`
   - 페치 요약 1줄 보고.

2. **`requirement-analyzer`**: `inputs/{figma,notion,slack,pdf}/raw/`, `inputs/prd/`, `inputs/api-spec/` 통합 → 행위 모델 JSON.
   - 출력: `outputs/intermediate/req-model.json`
   - 모든 행위에 `source_refs` 부착 확인.

3. **`tc-reviewer` dedup 모드**: 행위 모델 기반 신규성 사전 평가. 기존 `outputs/testcases/*.json` 과 0.85 이상 유사 차단.

4. **병렬 호출**:
   - `tc-gen-functional` → `outputs/intermediate/tc-functional.json`
   - `tc-gen-security`   → `outputs/intermediate/tc-security.json`
   - `tc-gen-negative`   → `outputs/intermediate/tc-negative.json`

5. **`tc-reviewer` judge 모드**: 통합 평가. 평균 4점 미만 reject. 고위험 risk_tag(auth/data/payment) 영역에 priority="high" TC가 0개면 강제 reject.

6. **`tc-normalizer`**: 통과 TC 통합 → `outputs/intermediate/tc-reviewed.json` (탭 분리 전, v3 스키마).

7. **`tc-platform-splitter`** (`target_platforms=$2 || "ios,android,web"`): `tc-reviewed.json`을 (screen, platform) 탭으로 분기.
   - 출력: `outputs/testcases/{screen-slug}_{and|ios|web}.json` 다수 (target_platforms에 포함된 플랫폼만).
   - 각 파일 안에서 `tc_id` 1부터 연속 재부여.
   - PostToolUse hook이 자동으로 v3 스키마 검증.

8. **시트 export (`tc-sheet` skill 위임)**: Skill `tc-sheet` 호출 → 내부적으로 `python3 .claude/skills/tc-sheet/scripts/export_workbook.py <appname>` 실행.
   - 시트 골자(불변 5가지: 1 워크북/앱, B~L 헤더, priority 색, result 빈 칸, summury 명시적 행 범위 수식)와 step 분해 규칙(1 버튼=1 step)은 `tc-sheet` skill의 SKILL.md에서 강제. 자세한 사양은 `.claude/skills/tc-sheet/references/{sheet-layout,step-decomposition,tc-schema-v3}.md`.
   - 입력: `outputs/testcases/*.json` / 출력: `outputs/sheets/{appname}.xlsx`.
   - Google Sheets에 import: `파일 → 가져오기 → 업로드 → 새 스프레드시트로 가져오기`.

9. **병렬 코드젠** (target_platforms에 따라):
   - `ios` 포함 → `codegen-ios` (입력: `outputs/testcases/*_ios.json`)
   - `android` 포함 → `codegen-android` (입력: `outputs/testcases/*_and.json`)
   - `web` 포함 → `codegen-web` (입력: `outputs/testcases/*_web.json`)

10. **`coverage-auditor`** (`iteration=1`): 시트 탭 합집합 + 입력 `source_refs` 추적성 검증.
    - 출력: `outputs/traceability.csv` (컬럼: `requirement_id,screen,platform,tc_id,priority,risk_tags,source_refs,risk_gap,note`)
    - 출력: `outputs/intermediate/coverage-gaps.json` (디자인-루프용 신호)

11. **디자인-루프 (max iter = 3)**:
    - a) `outputs/intermediate/coverage-gaps.json`을 읽는다.
    - b) `complete=true` (= `primary_design_gaps == []`)면 루프 종료, 12로.
    - c) `iteration >= 3`이면 잔여 `uncovered_source_refs`를 인용하는 placeholder TC를 생성해 `needs_review: true` 부착 후 종료. 1줄 경고 보고.
    - d) 그 외:
       1. `tc-gen-functional`/`tc-gen-security`/`tc-gen-negative`를 `gap_source_refs = uncovered_source_refs`만 입력으로 재호출 (전체 재생성 금지).
       2. `tc-reviewer` dedup 모드 (loop=true: 기존 (screen, platform, steps) 시퀀스도 비교).
       3. `tc-normalizer` `mode=merge`로 신규 TC만 append → `outputs/intermediate/tc-reviewed.json` 갱신.
       4. `tc-platform-splitter` 재실행 — 신규 TC만 각 탭 파일에 append (`tc_id`는 기존 최댓값+1부터).
       5. `tc-sheet` skill 재호출 (`python3 .claude/skills/tc-sheet/scripts/export_workbook.py <appname>`) — 워크북 전체 재생성(탭 추가/갱신, summury 통계도 자동 재계산).
       6. `codegen-{ios,android,web}` (target_platforms에 따라) — 신규 TC에 대응되는 델타 파일만 생성, 기존 파일 보존.
       7. `coverage-auditor` 재실행, `iteration += 1`.
    - e) 매 iter 종료 시 1줄 요약: `iter=N, coverage=X/Y (Z%), figma_gaps=K, complete=true|false`.
    - f) (b)부터 반복.

12. 최종 산출물 카운트를 표로 정리.
    - 컬럼: `시트 탭 (screen_platform) | TC 수 | high | mid | low | needs_review`
    - 추가 1줄: 생성된 워크북 경로(`outputs/sheets/{appname}.xlsx`)와 탭 목록.

## 규칙

- 모든 TC는 v3 시트 스키마(`tc_id`, `screen`, `platform`, `priority`, `precondition`, `steps`, `expected`)를 가진다.
- 내부 메타(`requirement_id`, `source_refs[]`, `risk_tags[]`, `negative`, `needs_review`)는 JSON에 보존, 시트 export에서 자동 제외.
- 고위험 risk_tag(auth/data/payment/network/storage) 영역은 priority="high" 우선.
- PII/시크릿(주민번호·계좌번호·OTP·토큰·API 키)은 생성 금지. fixture/env로만 주입.
- JSON이 깨지면 반드시 `tc-normalizer`를 다시 수행.
- splitter가 표현 치환을 못 하면 `needs_review: true`를 TC에 부착.
- 디자인-루프는 figma source_ref 기준으로 cap을 트리거. notion/slack/pdf는 보조 통계로만 보고.
- 시트 import 시: 구글 시트에서 `파일 → 가져오기 → 업로드 → 새 스프레드시트로 가져오기`. XLSX 자체에 summury 시트 + 탭별 시트 + 수식 + 조건부 서식 + 드롭다운이 모두 포함되어 그대로 보존됨.
