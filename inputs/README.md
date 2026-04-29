# Astartes 입력 가이드

디자인(Figma) · 기획(PDF·Notion) · 협의(Slack) · 자유 텍스트(PRD·API 스펙) 4종을 어떻게 하네스에 넣는지 안내한다. 두 가지 진입 방식이 있고 둘 다 같은 파이프라인으로 합쳐진다.

## 두 가지 입력 경로

| 방식 | 사용 시점 | 사용자가 두는 위치 | 호출 예시 |
|---|---|---|---|
| **링크(URL)** | API 토큰이 있고 최신 원본을 즉시 페치하고 싶을 때 | (수동 입력 불필요 — fetcher가 자동으로 `inputs/{type}/raw/`에 캐시) | `/gen-tc figma:https://www.figma.com/file/AB,notion:https://notion.so/page,slack:https://slack.com/archives/C0X/p1700,pdf:./inputs/pdf/spec.pdf ios,web` |
| **로컬 드롭** | 토큰이 없거나 오프라인 export를 직접 받았을 때 | `inputs/figma/export/`, `inputs/pdf/`, `inputs/notion/export/`, `inputs/slack/export/` | `/gen-tc local ios,android,web` 또는 `/gen-tc local` (platforms 생략 시 3개 모두) |

두 방식 혼용 가능: `/gen-tc local,figma:URL ios,web` 처럼 콤마로 묶으면 양쪽을 모두 처리한다.

## 링크 방식 상세

### 환경변수
- `FIGMA_TOKEN` — Figma personal access token (read 권한)
- `NOTION_TOKEN` — Notion integration token (해당 페이지 access 부여 필요)
- `SLACK_TOKEN` — Slack `xoxb-...` bot token (`channels:history`, `groups:history`)
- PDF는 토큰 불필요 (로컬 파일만 사용)

토큰이 누락되면 fetcher는 stderr에 명시 에러 후 exit 2로 종료한다. 누락된 소스 1개로 다른 소스 처리는 막지 않는다.

### source-spec 문법

콤마로 구분된 `<type>:<value>` 토큰을 한 인자로 전달한다.

```
figma:https://www.figma.com/file/<KEY>/<NAME>?node-id=1%3A234
notion:https://www.notion.so/<workspace>/<page-id>
slack:https://<workspace>.slack.com/archives/<CHANNEL>/p<TS>
pdf:./inputs/pdf/<file>.pdf
```

여러 개를 한 번에: `figma:URL,notion:URL,slack:URL,pdf:./path`

### MCP 서버 vs fetcher 폴백

세션에 `mcp__*figma*` / `mcp__*notion*` / `mcp__*slack*` MCP 도구가 등록돼 있으면 자동으로 그쪽이 우선 사용된다. 없으면 `scripts/fetch_<type>.py`가 폴백으로 호출된다. 사용자가 별도 설정할 것은 없다.

## 로컬 드롭 방식 상세

각 type별 export 디렉토리에 파일을 그대로 떨어뜨리면 `mcp-ingester`의 `local` 모드가 스캔해 `inputs/{type}/raw/`로 정규화 복사한다.

### Figma
- Figma 데스크탑/웹에서 "Export frames" → JSON/PNG/SVG.
- `inputs/figma/export/<feature>/`에 폴더 단위로 드롭.
- `node_id`/`name`이 source_ref locator로 매핑된다.

### PDF
- `inputs/pdf/<spec>.pdf` 그대로 드롭.
- `scripts/parse_pdf.py`가 페이지·텍스트·테이블 추출.
- `source_refs[].locator`는 `page=N` 형식.

### Notion
- 페이지를 Markdown export → `inputs/notion/export/<page>.md`
- 또는 API 응답 JSON을 직접 저장해도 됨.

### Slack
- 스레드 텍스트/JSON export → `inputs/slack/export/<thread>.json` (또는 `.txt`)
- ts(`1700000000.000100`) 단위로 source_ref가 생성된다.

### PRD / API 스펙 (자유 텍스트)
- `inputs/prd/`, `inputs/api-spec/` 에 자유 형식 텍스트로 둔다.
- 권한상 사용자가 직접 수정해야 한다(에이전트는 read-only).

## fixture-mode

토큰도 없고 로컬 드롭할 자료도 없을 때 E2E 검증용 mode.

```
/gen-tc fixture-mode
```

`tests/fixtures/sample-{figma,notion,slack}.json` + `sample-pdf.txt`를 자동으로 `inputs/{type}/raw/`로 복사한 뒤 일반 파이프라인을 실행한다.

## 플랫폼 인자

```
/gen-tc <source-spec> [platforms]
```

`platforms` 생략 시 기본 `ios,android,web` 3개 모두 생성. 부분집합 예: `ios,web` / `android` / `web`.

## 디자인-루프 (자동)

파이프라인 종료 직전 `coverage-auditor`가 `outputs/intermediate/coverage-gaps.json`을 본다. Figma source_ref 중 0개 TC만 인용된 노드가 있으면 해당 gap만 입력으로 `tc-gen-*`을 재호출한다 (max 3 iter). cap 도달 시 잔여 gap은 `needs_review: true` 부착으로 사람 리뷰에 위임.

## 금지 사항

- `inputs/{type}/raw/`는 자동 캐시 — 수동 수정 금지(PreToolUse 훅이 차단).
- PII / 시크릿(주민번호 · 계좌번호 · OTP · 토큰 · API 키)은 입력 본문 텍스트에도 평문 포함 금지. fixture / 환경변수 경유.
- `inputs/prd/`, `inputs/api-spec/`은 권한상 에이전트가 못 쓰므로 사람이 직접 관리.

## 캐시 / 재실행

같은 입력은 `inputs/{type}/raw/{sha256[:12]}.json`에 이미 있으면 fetcher가 즉시 재사용한다. 강제 재페치는 raw 파일을 수동 삭제하거나 `/gen-tc` 호출 전 `inputs/{type}/raw/`를 비우면 된다.

## 문제 해결

- 토큰 누락 → fetcher stderr 메시지 확인, 환경변수 export 후 재시도
- MCP 미등록 → 자동 폴백, 별도 조치 불필요
- 로컬 드롭한 파일이 인식 안 됨 → `inputs/{type}/export/` 경로/확장자 확인 후 `/gen-tc local`로 재실행
- coverage-gaps.json이 계속 비지 않음 → cap=3 도달 후 needs_review로 종료. 해당 gap의 source_ref를 직접 검토 후 행위 모델 보강
