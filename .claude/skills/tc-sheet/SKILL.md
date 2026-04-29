---
name: tc-sheet
description: TC JSON을 한국 QA 표준 포맷의 단일 XLSX 워크북(summury 시트 + (screen, platform) 탭들)으로 변환한다. 시트 작성 시 강제 규칙 — 1 버튼=1 step, result 컬럼 빈 칸, summury 통계는 명시적 행 범위 수식, 드롭다운은 데이터 행에만 — 을 적용한다. 사용 시점: TC를 새로 작성할 때, 기존 TC를 시트로 export할 때, #NAME? 등 시트 서식이 깨졌을 때, 또는 사용자가 "시트로 만들어줘"·"엑셀로 뽑아줘"라고 요청할 때.
---

# TC Sheet Skill

한국 QA 팀의 표준 스프레드시트 포맷(참조: `1A2kYCVhc0hICxErL5M1mwM17Bkx88aCXHf0nKvY9s1s`)에 맞춰 테스트 케이스 워크북을 만들고 검증한다.

## 언제 사용

- TC JSON을 작성·갱신한 직후 (`outputs/testcases/*.json`)
- 사용자가 "시트로 export", "엑셀로 뽑아줘", "워크북 갱신" 등을 요청
- 시트가 `#NAME?`, 빈 칸 노출, 칩셋 잔존 등으로 깨졌을 때
- TC step이 한 셀에 여러 동작이 묶여 있는 걸 발견했을 때 (Step 분해 규칙 적용)

## 시트 골자 (불변 5가지)

이 다섯은 절대 깨면 안 된다. 깨졌다면 export 스크립트나 TC JSON을 고친다.

1. **앱당 1 워크북**. `outputs/sheets/{appname}.xlsx` 단일 파일에 summury 시트 + (screen, platform) 탭들이 모두 들어간다. 화면별 CSV 분리 금지.
2. **레이아웃**: 컬럼 A 비움 / Row 1 비움 / Row 2 헤더 (B~L) / Row 3+ 데이터. 헤더는 연두(#B6D7A8), 가운데 정렬, 굵게.
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
2. **워크북 생성** — `python3 .claude/skills/tc-sheet/scripts/export_workbook.py <appname>` 실행.
3. **시트 검증** — openpyxl로 다시 읽거나 직접 열어서 다음 5가지 확인:
   - summury R10~ 의 수식이 명시적 행 번호 (`B3:B{N}`, `K3:K{N}`)인가
   - K 컬럼 데이터 검증 범위가 `K3:K{last_row}`인가 (빈 행 제외)
   - 모든 result 셀이 비어 있는가
   - priority 셀에 조건부 서식 색이 입혀졌는가
   - summury 환경 블록(R4~R7)·총 합계(R19) 자리가 채워졌는가
4. **재실행** — JSON을 고쳤다면 export를 다시 돌린다. export는 idempotent이므로 안전.

## 금지 사항

- `result` 컬럼에 `"N/A"` 등 기본값 자동 채우기 — QA만 채움.
- summury 수식에 open-ended 범위 (`K3:K`) 사용 — `#NAME?` 발생.
- 한 step에 여러 버튼·동작 묶기 (예: "탭하고 입력하고 생성한다").
- summury 통계 셀에 숫자 직접 입력 — 반드시 수식.
- 화면별로 CSV/XLSX를 따로 만들기 — 앱당 1 파일.
- TC 시트 헤더 위치/문구 변경 — `TC ID, priority, 1 Step ~ 5 Step, pre-condition, 기대결과, result, Jira ticket`로 고정.

## 참고 문서

- [sheet-layout.md](references/sheet-layout.md) — 셀 좌표·색상 hex·수식 패턴 전체 사양
- [step-decomposition.md](references/step-decomposition.md) — Step 분해 사례, 어휘, 5 step 한도 처리법
- [tc-schema-v3.md](references/tc-schema-v3.md) — TC JSON v3 스키마 (시트 컬럼 vs 내부 필드)

## 검증 fixture

이번 세션에서 생성된 `outputs/sheets/goodnotes.xlsx` (6 시트 + summury, 46 TC)가 골자 통과 기준. skill 변경 후에도 동일한 구조·수식이 나와야 한다.
