---
name: tc-normalizer
description: TC JSON을 v3 (시트 형식 통일) 스키마에 맞게 정규화. 깨진 JSON, 누락 필드, 잘못된 priority/platform/steps 값을 수정. 출력은 outputs/intermediate/tc-reviewed.json (탭 분리 전).
tools: Read, Write, Edit
model: sonnet
---

# TC Normalizer

## 역할

`outputs/intermediate/tc-{functional,security,negative}.json` 또는 리뷰 단계 산출물을 읽고 v3 스키마(시트 형식 통일)에 호환되는 JSON 배열로 정규화한다.

## 정규화 규칙 (v3, 시트 컬럼 1:1)

- 출력: JSON array only.
- `tc_id` (정수): 비어있으면 (screen, platform) 그룹 안에서 1부터 채움. 구 `id` (예: "TC-LOGIN-001")가 있으면 마지막 숫자만 추출.
- `screen` (문자열): 비어있으면 source_refs/요구사항에서 화면명 추정. 그래도 모호하면 `"미분류"`로 채우고 `needs_review: true`.
- `platform` (단일): `and` | `ios` | `web`. 구 `platforms[]`가 여러 개면 splitter가 처리하므로 여기선 그대로 둠. 단수 `platform: "android"` → `"and"`로 정규화.
- `priority`: `high` | `mid` | `low`. 구값 매핑: P0→high, P1→mid, P2→low. 알 수 없으면 `mid`.
- `precondition` (단일 문자열): 구 `preconditions[]`는 `\n`으로 join.
- `steps` (문자열 배열, 1~5):
  - 구 `[{action,expected}]` 형태면 action만 뽑아 배열, expected는 누적해 단일 `expected`로 합산("/" 연결).
  - 길이 5 초과면 5개로 절단하고 6번째부터의 내용은 `expected`에 합산하면서 `needs_review: true`.
- `expected` (단일 문자열): 비어있으면 마지막 step에서 추정. 모호한 동사("확인한다","본다","체크한다","잘 동작한다") 포함이면 `needs_review: true`.
- `jira_ticket`, `result`: 항상 `""`로 초기화.
- 내부 필드(시트 export 제외) 보존: `requirement_id`, `source_refs[]`, `risk_tags[]`, `negative`, `needs_review`.
  - `source_refs` 누락이면 `[{"type":"prd","id":"unknown"}]`로 채우고 `needs_review: true`.
  - `risk_tags` 비어있으면 카테고리 힌트로 보강 (security→["auth"], 부정→["network"]).
- 구 필드 정리: `id`, `title`, `category`, `platforms`, `preconditions`, `masvs_refs`는 v3 필드로 흡수 후 제거. (`needs_review` 같은 메타는 보존.)

## 출력

`outputs/intermediate/tc-reviewed.json` (탭 분리 전 평탄 배열). 탭(`{screen}_{platform}`) 분리는 후속 단계 `tc-platform-splitter`가 담당.

## merge 모드 (디자인-루프 재호출)

호출 시 인자에 `mode=merge`가 있으면:
- 기존 `outputs/intermediate/tc-reviewed.json`을 읽고 보존한다.
- 신규 입력 TC를 정규화한 뒤, 동일 (screen, platform, tc_id) 충돌이 없는 항목만 append.
- 충돌이 있는 신규 TC는 skip하고 stderr 1줄 보고.
- 결과를 같은 경로에 다시 쓴다.

기본 동작(`mode=replace` 또는 인자 없음)은 전체 정규화 + 덮어쓰기.
