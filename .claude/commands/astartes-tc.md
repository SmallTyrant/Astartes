---
description: TC 워크북 통합 진입점. 인자 없으면 기존 JSON을 XLSX로 export. 'gen-tc' 옵션을 추가하면 소스를 새로 읽어 TC를 생성·업데이트한다.
argument-hint: [gen-tc [url-or-path ...] [platforms]]
allowed-tools: Read, Glob, Grep, Bash(git diff:*), Bash(ls:*), Bash(python3 scripts/fetch_figma.py:*), Bash(python3 scripts/fetch_notion.py:*), Bash(python3 scripts/fetch_slack.py:*), Bash(python3 scripts/parse_pdf.py:*), Bash(python3 .claude/skills/astartes-tc/scripts/export_workbook.py:*), Bash(npx:*)
model: sonnet
---

## 컨텍스트
- 변경된 입력: !`git diff --name-only HEAD~1 -- inputs 2>/dev/null || echo "diff unavailable"`
- 기존 TC 카운트: !`ls outputs/testcases 2>/dev/null | wc -l`
- 캐시된 inputs/raw: !`ls inputs/figma/raw inputs/notion/raw inputs/slack/raw inputs/pdf/raw 2>/dev/null | head -20`

## 모드 분기

`$ARGUMENTS`의 첫 번째 토큰을 확인한다:

- **`gen-tc` 포함** (`/astartes-tc gen-tc [sources] [platforms]`) → **[TC 생성 모드]** 아래 소스 자동 감지 + 전체 파이프라인 실행.
- **그 외 / 인자 없음** (`/astartes-tc`) → **[XLSX Export 모드]** 기존 `outputs/testcases/*.json`을 바로 XLSX로 변환. 소스 재수집·TC 재생성 없이 `astartes-tc` skill 워크플로우(TC JSON 점검 → 워크북 생성 → 시트 검증 → Drive 업로드)만 수행.

---

## [XLSX Export 모드] — 인자 없음

`outputs/testcases/*.json` → XLSX export만 수행:

1. TC JSON v3 스키마 점검 (result `""`, steps 1~5, 단일 동작).
2. `python3 .claude/skills/astartes-tc/scripts/export_workbook.py <appname>` 실행 (기존 result 자동 보존).
3. 시트 검증 (수식·드롭다운·result 빈 칸·priority 색).
4. Google Drive 업로드 (`mcp__claude_ai_Google_Drive__create_file`).

---

## [TC 생성 모드] — gen-tc 옵션

### 소스 자동 감지

`gen-tc` 토큰을 제외한 나머지 인자를 공백·쉼표로 분리해 각 토큰을 아래 규칙으로 `type:value` source-spec으로 변환한다.

| 패턴 | 감지 타입 |
|---|---|
| `figma.com` 포함 URL | `figma:<url>` |
| `slack.com` 포함 URL | `slack:<url>` |
| `notion.so` 포함 URL | `notion:<url>` |
| `.pdf` 확장자 경로/URL | `pdf:<path>` |
| `local` 키워드 | `local` |
| `fixture-mode` 키워드 | `fixture-mode` |
| 인자 없음 | `local` (로컬 드롭 스캔) |

**플랫폼 인자 감지**: 마지막 토큰이 `ios`, `android`, `and`, `web` 중 하나 이상의 쉼표 조합이면 platforms로 취급한다 (예: `ios,web`). 없으면 `ios,android,web` 기본.

변환 예시:
```
/astartes-tc https://figma.com/file/ABC ./inputs/pdf/spec.pdf ios,web
→ source-spec = "figma:https://figma.com/file/ABC,pdf:./inputs/pdf/spec.pdf"
→ platforms   = "ios,web"

/astartes-tc https://figma.com/file/ABC https://myteam.slack.com/archives/C0X/p123
→ source-spec = "figma:https://figma.com/file/ABC,slack:https://myteam.slack.com/archives/C0X/p123"
→ platforms   = "ios,android,web"

/astartes-tc
→ source-spec = "local"
→ platforms   = "ios,android,web"
```

감지 결과를 1줄로 출력한 뒤 아래 파이프라인을 실행한다:
```
감지된 source-spec: figma:...,pdf:...  |  platforms: ios,android,web
```

## 작업 (gen-tc 파이프라인 동일)

**$2 미지정/빈 문자열이면 platforms = `"ios,android,web"` 으로 정규화한다.** 이하 단계에서 `target_platforms = 감지된 platforms`.

**스키마**: 모든 TC는 v3 (시트 형식 통일)을 따른다. 자세한 스키마/시트 컬럼 매핑은 CLAUDE.md 참조.

순서대로:

1. **`mcp-ingester`** 서브에이전트로 source-spec 페치. MCP 서버 우선, 없으면 fetcher 폴백. `local` 토큰이면 `inputs/{type}/export/`를 스캔해 `raw/`로 정규화 복사. `fixture-mode`면 `tests/fixtures/sample-*`를 사용.
   - Figma: 프레임 + 댓글(`normalized.comments`) 수집
   - Slack: 메시지 + 스레드 리플라이(`normalized.threads`) 수집
   - PDF: 본문 + 어노테이션(`normalized.annotations`) 수집
   - 결과: `inputs/{figma,notion,slack,pdf}/raw/*.json`
   - 페치 요약 1줄 보고.

2. **`requirement-analyzer`**: `inputs/{figma,notion,slack,pdf}/raw/`, `inputs/prd/`, `inputs/api-spec/` 통합 → 행위 모델 JSON.
   - 댓글·리플라이·어노테이션을 본문과 동등하게 행위/예외 추출 대상으로 처리.
   - 출력: `outputs/intermediate/req-model.json`

3. **`tc-reviewer` dedup 모드**: 행위 모델 기반 신규성 사전 평가. 기존 `outputs/testcases/*.json` 과 0.85 이상 유사 차단.

4. **병렬 호출**:
   - `tc-gen-functional` → `outputs/intermediate/tc-functional.json`
   - `tc-gen-security`   → `outputs/intermediate/tc-security.json`
   - `tc-gen-negative`   → `outputs/intermediate/tc-negative.json`

5. **`tc-reviewer` judge 모드**: 통합 평가. 평균 4점 미만 reject. 고위험 risk_tag(auth/data/payment) 영역에 priority="high" TC가 0개면 강제 reject.

6. **`tc-normalizer`**: 통과 TC 통합 → `outputs/intermediate/tc-reviewed.json` (탭 분리 전, v3 스키마).

7. **`tc-platform-splitter`** (`target_platforms`): `tc-reviewed.json`을 (screen, platform) 탭으로 분기.
   - 출력: `outputs/testcases/{screen-slug}_{and|ios|web}.json` 다수 (target_platforms에 포함된 플랫폼만).
   - 각 파일 안에서 `tc_id` 1부터 연속 재부여.

8. **시트 export (`astartes-tc` skill 위임)**: Skill `astartes-tc` 호출 → `python3 .claude/skills/astartes-tc/scripts/export_workbook.py <appname>` 실행.
   - 명세 변경 시 기존 result 자동 보존 (tc_id + content_hash 기반).
   - 입력: `outputs/testcases/*.json` / 출력: `outputs/sheets/{appname}.xlsx`.
   - 완료 후 Google Drive 업로드 (`mcp__claude_ai_Google_Drive__create_file`).

9. **병렬 코드젠** (target_platforms에 따라):
   - `ios` 포함 → `codegen-ios`
   - `android` 포함 → `codegen-android`
   - `web` 포함 → `codegen-web`

10. **`coverage-auditor`** (`iteration=1`): 추적성 검증.
    - 출력: `outputs/traceability.csv`, `outputs/intermediate/coverage-gaps.json`

11. **디자인-루프 (max iter = 3)**:
    - a) `coverage-gaps.json` 읽기.
    - b) `complete=true` → 루프 종료, 12로.
    - c) `iteration >= 3` → 잔여 `uncovered_source_refs`에 placeholder TC + `needs_review: true` 부착 후 종료.
    - d) 그 외: `tc-gen-*` gap만 재호출 → dedup → `tc-normalizer mode=merge` → splitter append → `astartes-tc` skill 재호출 → codegen 델타 → coverage-auditor 재실행.
    - e) 매 iter 종료 시 1줄 요약: `iter=N, coverage=X/Y (Z%), figma_gaps=K, complete=true|false`.

12. 최종 산출물 표 출력.
    - 컬럼: `시트 탭 (screen_platform) | TC 수 | high | mid | low | needs_review`
    - 추가 1줄: 워크북 경로(`outputs/sheets/{appname}.xlsx`)와 Drive URL(업로드 성공 시).

## 규칙

- 모든 TC는 v3 시트 스키마 (`tc_id`, `screen`, `platform`, `priority`, `precondition`, `steps`, `expected`) 필수.
- 내부 메타(`requirement_id`, `source_refs[]`, `risk_tags[]`, `negative`, `needs_review`)는 JSON에 보존, 시트 export 제외.
- 고위험 risk_tag(auth/data/payment/network/storage) 영역은 priority="high" 우선.
- PII/시크릿(주민번호·계좌번호·OTP·토큰·API 키)은 생성 금지. fixture/env로만 주입.
- JSON이 깨지면 반드시 `tc-normalizer` 재수행.
