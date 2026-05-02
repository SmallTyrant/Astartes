# Sheet Layout 사양

기준 워크북: 한국 QA 표준 포맷 (Google Sheets `1A2kYCVhc0hICxErL5M1mwM17Bkx88aCXHf0nKvY9s1s`).
이 문서는 `scripts/export_workbook.py`가 출력해야 하는 **셀 좌표·색상·수식**의 단일 사양이다.

## 워크북 구조

- 파일 1개: `outputs/sheets/{appname}.xlsx`
- 시트 순서:
  1. `summury` (index 0, 항상 첫 시트)
  2. `{screen}_{platform}` ... 가나다 순으로 정렬된 (screen, platform) 조합

`{platform}` 은 `ios | and | web` (Android는 `and`, 시트 탭 접미사와 동일).
시트 이름은 Excel 31자 제한을 준수하기 위해 `[:31]` 슬라이스.

---

## TC 시트 (`{screen}_{platform}`)

### 컬럼 / 행 좌표

| 좌표 | 내용 | 비고 |
| ---- | ---- | ---- |
| A   | 비움 | column width = 3 (시각적 여백) |
| Row 1 | 비움 | 시각적 여백 |
| Row 2 (B~L) | 헤더 | 위치 고정 |
| Row 3+ | 데이터 | TC 1건당 1행 |

### 헤더 (Row 2, B2~L2)

```
B: TC ID
C: priority
D: 1 Step
E: 2 Step
F: 3 Step
G: 4 Step
H: 5 Step
I: pre-condition
J: 기대결과
K: result
L: Jira ticket
```

- 배경색: 연두 `#B6D7A8`
- 폰트: bold
- 정렬: center (vertical/horizontal), `wrap_text=True`
- 행 높이: 28
- 테두리: thin `#999999`

### 컬럼 너비

```python
{1: 3, 2: 7, 3: 11, 4: 28, 5: 28, 6: 28, 7: 28, 8: 28, 9: 24, 10: 32, 11: 9, 12: 14}
```

### 데이터 행 서식

- 행 높이: 60
- 테두리: thin `#999999`
- 정렬: TC ID(B)·priority(C)·result(K) 컬럼은 center, 나머지는 left + wrap_text

### priority 조건부 서식 (C 컬럼)

범위: `C{DATA_START_ROW}:C{last_row}` (= `C3:C{N+2}`, 데이터 행에만)

| 값     | 배경색             | 폰트                 |
| ------ | ------------------ | -------------------- |
| `high` | 빨강 `#E06666`     | 흰색 bold (`#FFFFFF`) |
| `mid`  | 노랑 `#FFD966`     | 기본                 |
| `low`  | 초록 `#93C47D`     | 기본                 |

`CellIsRule(operator="equal", formula=['"high"'], ...)` 형태.

### result 드롭다운 (K 컬럼)

- DataValidation: `type="list"`, `formula1='"Pass,Fail,Block,N/A"'`, `allow_blank=True`, `showDropDown=False`
- **범위**: `K{DATA_START_ROW}:K{last_row}` (실제 TC 행에만)
- **빈 행에는 절대 적용 금지** — `last_row + 100` 같은 패딩 금지
- **셀 값은 빈 문자열로 둔다** (`tc.get("result", "") or ""`). 자동으로 `N/A` 등 어떤 값도 채우지 않는다.

---

## summury 시트 (index 0)

### 환경 블록

| 좌표 | 내용 | 비고 |
| ---- | ---- | ---- |
| B2 | `{app_name} TC` | bold, size 14 |
| B4:E4 | `수행 환경 / 수행자 / 테스트 기간 / (빈 셀)` | 헤더, 배경 `#00FF00` (또는 GREEN), bold, center |
| B5:E5 | `Android / N/A / version / N/A` | 행별로 환경/수행자/version 라벨/version 값 |
| B6:E6 | `iOS / 아이폰 17 pro / version / 26.4.1` | 기본값(상황 따라 수정) |
| B7:E7 | `OS / Window11 / version / 11h2` | 기본값 |

B/D 컬럼(환경명, "version" 라벨)은 GREEN 배경 + bold + center.
C/E 컬럼(수행자, version 값)은 일반 셀 + center.

### 통계 헤더 (Row 9, B9~J9)

```
B: 구분
C: 검증 항목
D: Pass
E: Fail
F: Block
G: N/A
H: 성공율
I: 결함율
J: 수행율
```

배경: 회색 `#D9D9D9`, bold, center, 테두리.

### 통계 데이터 (Row 10~)

각 (screen_platform) 시트마다 1행. **9 슬롯 고정** (`fixed_rows = 9`, Row 10~18).
9개를 초과하는 시트는 시트 추가/축소 시 코드를 함께 손봐야 한다.

각 행 `r`의 셀:

```python
ref_b = f"'{tab}'!B{DATA_START_ROW}:B{last}"   # B 컬럼(TC ID)
ref_k = f"'{tab}'!K{DATA_START_ROW}:K{last}"   # K 컬럼(result)
# last = DATA_START_ROW + count - 1 (해당 탭의 명시적 마지막 행)

B{r}: {tab}                                    # 시트명
C{r}: =COUNTA(ref_b)                           # 검증 항목
D{r}: =COUNTIF(ref_k,"Pass")                   # Pass
E{r}: =COUNTIF(ref_k,"Fail")                   # Fail
F{r}: =COUNTIF(ref_k,"Block")                  # Block
G{r}: =COUNTIF(ref_k,"N/A")                    # N/A
H{r}: =IFERROR(D{r}/C{r},0)                    # 성공율 — number_format "0.00%"
I{r}: =IFERROR(E{r}/C{r},0)                    # 결함율 — number_format "0.00%"
J{r}: =IFERROR((D{r}+E{r}+F{r})/C{r},0)        # 수행율 — number_format "0.00%"
```

**필수 규칙**:

- `ref_b`, `ref_k`는 **명시적 마지막 행**을 포함한다. open-ended (`'tab'!K3:K`) 금지 — Excel/Sheets에서 `#NAME?` 발생.
- 시트명에 작은따옴표가 들어가면 `'` → `''` 로 escape. (`tab.replace("'", "''")`)
- 빈 슬롯(시트가 없는 행)은 셀 값을 비우되 테두리·alignment(center)는 유지한다.

### 총 합계 (Row 19)

```python
B19: 총 합계                            # 회색 배경, bold, center
C19: =SUM(C10:C18)
D19: =SUM(D10:D18)
E19: =SUM(E10:E18)
F19: =SUM(F10:F18)
G19: =SUM(G10:G18)
H19: =IFERROR(D19/C19,0)               # 0.00%
I19: =IFERROR(E19/C19,0)               # 0.00%
J19: =IFERROR((D19+E19+F19)/C19,0)     # 0.00%
```

### 컬럼 너비 (summury)

```python
{1: 3, 2: 22, 3: 12, 4: 8, 5: 8, 6: 8, 7: 8, 8: 9, 9: 9, 10: 9}
```

---

## 색상 hex 정리

| 이름        | hex       | 용도                       |
| ----------- | --------- | -------------------------- |
| GREEN       | `B6D7A8`  | TC 시트 헤더, summury 환경 |
| GRAY        | `D9D9D9`  | summury 통계 헤더·총 합계  |
| RED         | `E06666`  | priority=high              |
| YELLOW      | `FFD966`  | priority=mid               |
| LIGHT_GREEN | `93C47D`  | priority=low               |
| WHITE_BOLD  | `FFFFFF`  | high 폰트                  |
| THIN border | `999999`  | 모든 데이터 셀             |
| `00FF00`    | env block | summury 환경 헤더          |

---

## 검증 체크리스트

1. 모든 TC 시트의 헤더 = `TC ID, priority, 1 Step, ..., 5 Step, pre-condition, 기대결과, result, Jira ticket` 순서.
2. 모든 K 컬럼 데이터 검증 범위가 `K3:K{last_row}` (빈 행 미포함).
3. 모든 result 셀 값이 비어 있는가 (None / "").
4. summury C10:G18 수식이 `COUNTA / COUNTIF` + 명시적 행 번호.
5. summury 합계 행(Row 19)가 채워졌고 비율이 `0.00%`.
6. priority 조건부 서식 색이 high/mid/low에 적용됨.

위반 항목이 있으면 export 스크립트를 고친 뒤 `python3 .claude/skills/astartes-tc/scripts/export_workbook.py {appname}` 재실행.
