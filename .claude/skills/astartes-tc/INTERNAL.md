---
name: astartes-tc-export
description: (내부 참조 전용) XLSX export 골자·step 분해·수식 사양. 사용자 진입점은 /astartes-tc 명령어.
---

# Astartes TC Skill

한국 QA 팀의 표준 스프레드시트 포맷(참조: `1A2kYCVhc0hICxErL5M1mwM17Bkx88aCXHf0nKvY9s1s`)에 맞춰 테스트 케이스 워크북을 만들고 검증한다.

## 언제 사용

- TC JSON을 작성·갱신한 직후 (`outputs/testcases/*.json`)
- 사용자가 "시트로 export", "엑셀로 뽑아줘", "워크북 갱신" 등을 요청
- 시트가 `#NAME?`, 빈 칸 노출, 칩셋 잔존 등으로 깨졌을 때
- TC step이 한 셀에 여러 동작이 묶여 있는 걸 발견했을 때 (Step 분해 규칙 적용)

## 시트 골자 (불변 5가지)

이 다섯은 절대 깨면 안 된다. 깨졌다면 export 스크립트나 TC JSON을 고친다.

1. **앱당 1 워크북**. `outputs/sheets/{appname}.xlsx` 단일 파일에 summury 시트 + (screen, platform) 탭들이 모두 들어간다. 화면별 CSV 분리 금지.
2. **레이아웃**: 컬럼 A 비움 / Row 1 비움 / Row 2 헤더 (B~M) / Row 3+ 데이터. 헤더는 연두(#B6D7A8), 가운데 정렬, 굵게.
3. **priority 조건부 서식**: high=빨강(#E06666, 흰 글씨 굵게), mid=노랑(#FFD966), low=초록(#93C47D). C{데이터행} 범위에만 적용.
4. **result 컬럼 (K)**: 드롭다운 옵션은 `Pass / Fail / Block / N/A`. **기본값은 빈 칸** (QA가 실행 후 채움). 드롭다운 적용 범위는 실제 TC 행만(`K3:K{last_row}`) — 빈 행에 칩셋이 노출되면 안 된다.
5. **summury 통계는 수식**: 직접 입력 금지. 모든 카운트는 `=COUNTA('탭'!B3:B{N})`, `=COUNTIF('탭'!K3:K{N},"Pass")` 같이 **명시적 마지막 행 번호**를 쓴다. open-ended (`K3:K`)는 COUNTIF에서 `#NAME?`을 일으키므로 절대 금지.

## Step 분해 규칙 (요약)

**1 버튼/1 옵션 탭 = 1 step.** 한 step에 여러 동작을 묶지 않는다.

```
나쁨: "라이브러리 '+' 버튼에서 '폴더'를 선택해 'Q2'를 생성한다"
좋음: ["'+' 버튼을 탭한다", "'폴더' 옵션을 탭한다", "이름 입력 필드에 'Q2'를 입력한다", "'생성' 버튼을 탭한다"]
```

5 step 한도(시트 컬럼 1 Step~5 Step)는 절대 한도이며, 더 길면 시나리오를 둘로 쪼개거나 사전조건으로 압축한다. 자세한 사례·어휘는 `references/step-decomposition.md`.

## 워크플로우

1. **TC JSON 점검** — `outputs/testcases/*.json` 모두 v3 스키마 준수, `result` 모두 `""`, `steps` 1~5개, 각 step이 단일 동작인지 확인. 위반 시 먼저 JSON을 고친다 (export 후 고치지 말 것).
2. **워크북 생성** — `python3 .claude/skills/astartes-tc/scripts/export_workbook.py <appname>` 실행.
3. **시트 검증** — openpyxl로 다시 읽거나 직접 열어서 다음 5가지 확인:
   - summury R10~ 의 수식이 명시적 행 번호 (`B3:B{N}`, `K3:K{N}`)인가
   - K 컬럼 데이터 검증 범위가 `K3:K{last_row}`인가 (빈 행 제외)
   - 모든 result 셀이 비어 있는가
   - priority 셀에 조건부 서식 색이 입혀졌는가
   - summury 환경 블록(R4~R7)·총 합계(R19) 자리가 채워졌는가
4. **재실행** — JSON을 고쳤다면 export를 다시 돌린다. export는 idempotent이므로 안전.
5. **Google Drive 업로드** — 검증 통과 후 `mcp__claude_ai_Google_Drive__create_file`로 `outputs/sheets/{appname}.xlsx`를 Drive에 업로드한다.
   - 첫 실행이거나 인증이 필요하면 `mcp__claude_ai_Google_Drive__authenticate`로 먼저 인증한다.
   - 업로드 성공 시 반환된 파일 URL을 출력해 사용자가 바로 열 수 있게 한다.
   - 같은 이름의 파일이 Drive에 이미 있으면 덮어쓰지 않고 사용자에게 확인한 뒤 업로드한다.

## 명세 변경 시 워크플로우 (기존 시트 유지)

명세서가 바뀌어 TC JSON이 갱신된 경우, 기존 시트의 수행 결과(result)를 최대한 보존한다.

### 원칙
- **기존 TC (tc_id 동일 + 내용 무변경)**: 기존 result 값(`Pass`/`Fail`/`Block`/`N/A`) 그대로 유지.
- **변경된 TC (tc_id 동일 + steps·expected 등 내용 변경)**: result를 `""`(빈 칸)으로 초기화. 내용이 바뀌었으므로 재수행 필요.
- **신규 TC (tc_id 신규)**: result `""` (초기 상태).
- **삭제된 TC (구 JSON에만 있는 tc_id)**: 시트 행을 유지하고 result를 `N/A`로 설정. 명세 변경·제거 이력 보존.

### 절차
1. **result 스냅샷 추출** — 기존 `outputs/sheets/{appname}.xlsx`에서 각 탭의 `tc_id → result` 매핑을 읽어 메모리에 보관.
   ```python
   # 예시
   snapshot = {"TC-001": "Pass", "TC-002": "Fail", "TC-003": ""}
   ```
2. **신규 TC JSON 점검** — 갱신된 `outputs/testcases/*.json`이 v3 스키마를 준수하는지 확인. `result`는 모두 `""`이어야 함 (JSON 단계에서는 result를 채우지 않음).
3. **result 병합** — export 직전, 각 TC의 `tc_id`를 스냅샷과 대조해 result를 결정:
   - 스냅샷에 있고 + 내용 동일 → 스냅샷 result 복원
   - 스냅샷에 있고 + 내용 변경 → `""` (초기화)
   - 스냅샷에 없음 → `""` (신규)
   - 새 JSON에 없음 (삭제된 TC) → `N/A` 유지 (tc_data가 사이드카에 있을 때만 복원)
4. **워크북 재생성** — `python3 .claude/skills/astartes-tc/scripts/export_workbook.py <appname>` 실행. 병합된 result가 K 컬럼에 반영되어야 함.
5. **시트 검증** — 기존 워크플로우 3단계와 동일. 추가로 보존된 result 셀이 올바르게 복원됐는지 확인.
6. **Google Drive 업로드** — 기존 워크플로우 5단계와 동일.

### 내용 변경 판정 기준
`steps`, `expected`, `precondition`, `priority`, `risk_tags` 중 하나라도 다르면 "내용 변경"으로 간주해 result를 초기화한다. `title`만 바뀐 경우도 초기화한다.

## 금지 사항

- `result` 컬럼에 `"N/A"` 등 기본값 자동 채우기 — QA만 채움.
- summury 수식에 open-ended 범위 (`K3:K`) 사용 — `#NAME?` 발생.
- 한 step에 여러 버튼·동작 묶기 (예: "탭하고 입력하고 생성한다").
- summury 통계 셀에 숫자 직접 입력 — 반드시 수식.
- 화면별로 CSV/XLSX를 따로 만들기 — 앱당 1 파일.
- TC 시트 헤더 위치/문구 변경 — `TC ID, priority, 1 Step ~ 5 Step, pre-condition, 기대결과, result, Jira ticket, 비고`로 고정.

## 참고 문서

- [sheet-layout.md](references/sheet-layout.md) — 셀 좌표·색상 hex·수식 패턴 전체 사양
- [step-decomposition.md](references/step-decomposition.md) — Step 분해 사례, 어휘, 5 step 한도 처리법
- [tc-schema-v3.md](references/tc-schema-v3.md) — TC JSON v3 스키마 (시트 컬럼 vs 내부 필드)

## 검증 fixture

이번 세션에서 생성된 `outputs/sheets/goodnotes.xlsx` (6 시트 + summury, 46 TC)가 골자 통과 기준. skill 변경 후에도 동일한 구조·수식이 나와야 한다.
