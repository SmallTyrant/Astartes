# 범용 디자인-to-TC 자동생성 하네스

## 도메인 컨텍스트
- 본 하네스는 디자인(Figma)·기획(PDF/Notion)·협의 로그(Slack)·PRD/API 스펙으로부터 iOS/Android/Web 3개 플랫폼의 테스트 케이스(TC)와 자동화 스켈레톤을 생성하는 범용 도구다.
- 어떤 도메인이든 입력만 주어지면 동작한다. 도메인 가정(금융/헬스/커머스 등)은 입력에 명시되지 않으면 추가하지 않는다.
- 모든 TC와 자동화 코드의 자연어는 한국어. 코드 식별자만 영문.
- 어떤 도메인의 PII/시크릿(주민번호·계좌번호·OTP·API 키·토큰)도 절대 하드코딩 금지. fixture 또는 환경변수로만 주입.

## 입출력 경로
- 입력:
  - `inputs/figma/raw/` — MCP/figma fetcher 캐시 (자동 생성, 수정 금지)
  - `inputs/figma/export/` — 사용자 직접 export 드롭
  - `inputs/pdf/` — PDF 드롭
  - `inputs/slack/` — MCP/slack fetcher 캐시
  - `inputs/notion/` — MCP/notion fetcher 캐시
  - `inputs/prd/`, `inputs/api-spec/` — 자유 텍스트(레거시 호환)
- 출력:
  - `outputs/intermediate/req-model.json`, `tc-{functional,negative,security}.json`
  - `outputs/testcases/{screen-slug}_{and|ios|web}.json` — 시트 탭 단위 최종 JSON (v3 스키마)
  - `outputs/sheets/{appname}.xlsx` — **앱당 1개의 워크북 (단일 파일)**. summury 시트(환경 블록 + 통계 표) + (screen, platform)별 탭으로 구성. 통계는 수식(COUNTA/COUNTIF/SUM)으로 자동 계산.
  - `outputs/testcases/automation_candidates.json`
  - `outputs/ios/{Tests,PageObjects,Fixtures}/`
  - `outputs/android/{tests,screens,fixtures}/`
  - `outputs/web/{tests,pages,fixtures}/`
  - `outputs/traceability.csv`

## TC 작성 원칙
1. 검증 가능성: `expected`가 코드/UI/네트워크/상태로 관측 가능해야 함.
2. 격리성: 한 TC는 다른 TC 결과에 의존 금지. `precondition`에 사전조건 명시.
3. 추적성: `requirement_id`와 `source_refs[]` 필수(시트 export에는 빠지나 JSON에는 보존). 누락 시 PostToolUse 훅이 차단.
4. 위험 우선순위: `risk_tags`에 auth/data/payment/network/storage 중 하나 이상 포함된 TC는 priority=high 부여.

## TC 스키마 (시트 형식 통일, v3)

전체 스키마·시트 컬럼 매핑·탭 분리 규칙·구 스키마 호환성은 `.claude/skills/astartes-tc/references/tc-schema-v3.md` 참조.
시트 작성 자체의 골자(1 워크북/앱, 헤더 위치, priority 색, result 빈 칸, 명시적 행 범위 수식, 1 버튼=1 step)는 `astartes-tc` skill 이 강제한다.

## 자동화 코드 컨벤션
- iOS: Page Object 패턴, XCTest + XCUITest. `outputs/ios/PageObjects/`에 화면별 PO 클래스. accessibility identifier로만 매칭.
- Android: Espresso + Kotlin coroutines. `outputs/android/screens/`에 화면별 Screen 객체. `onView(withId(R.id...))`만 매칭.
- Web: Playwright + TypeScript, Page Object 패턴. `outputs/web/pages/{Screen}Page.ts`. `page.getByTestId()`만 매칭(텍스트/CSS selector 금지).
- 공통: 텍스트 매칭/하드코딩 금지. fixture 또는 환경변수로 데이터 주입.

## 표현 규칙
- "확인한다", "본다", "체크한다" 같은 모호한 동사 대신 "표시되어야 한다", "활성화되어야 한다"로.
- Prefer fixture 주입 over 하드코딩.
- Prefer accessibility id/data-testid 매칭 over 텍스트 매칭.

## 실행 명령

- `/gen-tc <source-spec> <platforms>`: 전체 파이프라인 실행 (예: `/gen-tc figma:URL,pdf:./inputs/pdf/spec.pdf ios,web`)
- `/review-tc`: 기존 TC 리뷰만 실행
- `/normalize-tc`: JSON 정규화만 실행
- `/export-tc`: 최종 TC를 Markdown/CSV/자동화 skeleton으로 변환

## 단계별 산출물 규칙

1. 입력 수집본 → `inputs/{figma,notion,slack,pdf}/raw/{hash}.json` (또는 export/`)
2. 행위 모델 → `outputs/intermediate/req-model.json` (모든 행위에 `source_refs`·`screen` 부착)
3. 카테고리별 초안 → `outputs/intermediate/tc-{functional,security,negative}.json` (v3 스키마)
4. 리뷰 반영본 → `outputs/intermediate/tc-reviewed.json`
5. 시트 탭별 최종 JSON → `outputs/testcases/{screen-slug}_{platform}.json`
6. 앱 단위 시트 워크북 → `outputs/sheets/{appname}.xlsx` — `astartes-tc` skill로 위임 (골자/포맷/수식 사양은 skill SKILL.md + references/ 참조).
7. 요구사항 추적성 → `outputs/traceability.csv` (컬럼: requirement_id, screen, platform, tc_id, priority, risk_tags, source_refs, note)
8. 자동화 후보 → `outputs/testcases/automation_candidates.json`

## 실패 처리

- JSON 파싱 실패 시 `tc-normalizer`를 먼저 실행한다.
- `requirement_id`/`source_refs` 누락 시 `coverage-auditor`가 실패로 보고한다.
- 고위험 risk_tag(auth/data/payment) 영역에 부정/보안 P0 케이스가 0개면 추가 TC를 생성한다.
- PII/시크릿(계좌번호·주민번호·OTP·토큰·API 키)이 발견되면 fixture 또는 환경변수로 마스킹한다.
- 단일 `.ts` 파일 tsc 검증이 의존성으로 실패하면 `outputs/web/tsconfig.json` + `node_modules` 사전 배치 또는 eslint syntax 폴백.
