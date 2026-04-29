#!/usr/bin/env python3
"""TC JSON(v3) → 단일 XLSX 워크북 (앱당 1파일).

레이아웃 (참조 시트 정합):
  - 시트 순서: summury, {screen}_{platform}, ...
  - TC 시트:
    - A 컬럼 비움
    - Row 1 비움
    - Row 2 헤더 (B~L): TC ID | priority | 1 Step | 2 Step | 3 Step | 4 Step | 5 Step | pre-condition | 기대결과 | result | Jira ticket
    - Row 3+ 데이터
    - 헤더 배경: 연두 (#B6D7A8)
    - priority 컬러: high=빨강, mid=노랑, low=초록 (조건부 서식)
    - result: 드롭다운 (Pass/Fail/Block/N/A), 기본값 빈 칸 (QA가 실행 후 채움)
  - summury 시트:
    - B2: 앱명 (또는 "TC 작성 예시")
    - B4:F7 환경 블록 (수행 환경/수행자/테스트 기간)
    - B9:J9 통계 헤더 (회색 #D9D9D9)
    - B10~ 각 (screen_platform) 행, 검증항목/Pass/Fail/Block/N/A/성공율/결함율/수행율 = COUNTA/COUNTIF/수식
    - 마지막 행: 총 합계

사용:
  python3 .claude/skills/astartes-tc/scripts/export_workbook.py [앱명]
  - 앱명 미지정 시 'app' 사용
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule

# 프로젝트 루트: <project>/.claude/skills/astartes-tc/scripts/export_workbook.py
#   parents[0]=scripts/  [1]=astartes-tc/  [2]=skills/  [3]=.claude/  [4]=<project>
ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = ROOT / "outputs" / "testcases"
OUT_DIR = ROOT / "outputs" / "sheets"

ALLOWED_PLATFORM = {"and", "ios", "web"}

TC_HEADER = [
    "TC ID", "priority",
    "1 Step", "2 Step", "3 Step", "4 Step", "5 Step",
    "pre-condition", "기대결과", "result", "Jira ticket",
]
HEADER_START_COL = 2   # B
HEADER_ROW = 2
DATA_START_ROW = 3

GREEN = PatternFill("solid", fgColor="B6D7A8")
GRAY = PatternFill("solid", fgColor="D9D9D9")
RED = PatternFill("solid", fgColor="E06666")
YELLOW = PatternFill("solid", fgColor="FFD966")
LIGHT_GREEN = PatternFill("solid", fgColor="93C47D")
THIN = Side(style="thin", color="999999")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_WRAP = Alignment(horizontal="left", vertical="center", wrap_text=True)
HEADER_FONT = Font(bold=True)
WHITE_BOLD = Font(bold=True, color="FFFFFF")


def load_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "testcases" in data:
        data = data["testcases"]
    if not isinstance(data, list):
        data = [data]
    return [tc for tc in data if isinstance(tc, dict)]


def group_by_tab(tcs: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for tc in tcs:
        screen = (tc.get("screen") or "").strip()
        platform = (tc.get("platform") or "").strip()
        if not screen or platform not in ALLOWED_PLATFORM:
            print(f"[export_workbook] skip: screen={screen!r} platform={platform!r}", file=sys.stderr)
            continue
        groups.setdefault((screen, platform), []).append(tc)
    for lst in groups.values():
        lst.sort(key=lambda t: t.get("tc_id") or 0)
    return groups


def steps_to_cells(steps: list) -> list[str]:
    out = list(steps or [])
    while len(out) < 5:
        out.append("")
    return out[:5]


def add_tc_sheet(wb: Workbook, sheet_name: str, tcs: list[dict]) -> None:
    ws = wb.create_sheet(title=sheet_name[:31])  # excel 시트명 31자 제한

    # 컬럼 너비
    widths = {1: 3, 2: 7, 3: 11, 4: 28, 5: 28, 6: 28, 7: 28, 8: 28, 9: 24, 10: 32, 11: 9, 12: 14}
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    # 헤더 (Row 2, B~L)
    for i, label in enumerate(TC_HEADER):
        cell = ws.cell(row=HEADER_ROW, column=HEADER_START_COL + i, value=label)
        cell.fill = GREEN
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER

    # 데이터
    for idx, tc in enumerate(tcs):
        row = DATA_START_ROW + idx
        steps = steps_to_cells(tc.get("steps") or [])
        values = [
            tc.get("tc_id", idx + 1),
            tc.get("priority", ""),
            steps[0], steps[1], steps[2], steps[3], steps[4],
            tc.get("precondition", "") or "",
            tc.get("expected", "") or "",
            tc.get("result", "") or "",
            tc.get("jira_ticket", "") or "",
        ]
        for j, val in enumerate(values):
            cell = ws.cell(row=row, column=HEADER_START_COL + j, value=val)
            cell.border = BORDER
            if j == 0 or j == 1 or j == 9:
                cell.alignment = CENTER
            else:
                cell.alignment = LEFT_WRAP

    last_row = DATA_START_ROW + max(len(tcs), 1) - 1

    # priority 조건부 서식 (C 컬럼)
    prio_range = f"C{DATA_START_ROW}:C{last_row}"
    ws.conditional_formatting.add(prio_range, CellIsRule(operator="equal", formula=['"high"'], fill=RED, font=WHITE_BOLD))
    ws.conditional_formatting.add(prio_range, CellIsRule(operator="equal", formula=['"mid"'], fill=YELLOW))
    ws.conditional_formatting.add(prio_range, CellIsRule(operator="equal", formula=['"low"'], fill=LIGHT_GREEN))

    # result 드롭다운 (K 컬럼) — 실제 TC 행에만 적용 (빈 행에 칩셋 노출 방지)
    if tcs:
        dv = DataValidation(type="list", formula1='"Pass,Fail,Block,N/A"', allow_blank=True, showDropDown=False)
        dv.add(f"K{DATA_START_ROW}:K{last_row}")
        ws.add_data_validation(dv)

    # 행 높이
    ws.row_dimensions[HEADER_ROW].height = 28
    for r in range(DATA_START_ROW, last_row + 1):
        ws.row_dimensions[r].height = 60


def add_summury_sheet(wb: Workbook, app_name: str, tab_data: list[tuple[str, int]]) -> None:
    ws = wb.create_sheet(title="summury", index=0)

    widths = {1: 3, 2: 22, 3: 12, 4: 8, 5: 8, 6: 8, 7: 8, 8: 9, 9: 9, 10: 9}
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    # 타이틀
    title = ws.cell(row=2, column=2, value=f"{app_name} TC")
    title.font = Font(bold=True, size=14)

    # 환경 블록 (Row 4~7)
    env_header = [("수행 환경", "수행자", "테스트 기간", "")]
    env_rows = [
        ("Android", "N/A", "version", "N/A"),
        ("iOS", "아이폰 17 pro", "version", "26.4.1"),
        ("OS", "Window11", "version", "11h2"),
    ]
    # row 4 헤더
    for j, label in enumerate(["수행 환경", "수행자", "테스트 기간", ""]):
        c = ws.cell(row=4, column=2 + j, value=label if label else None)
        if label:
            c.fill = PatternFill("solid", fgColor="00FF00")
            c.font = HEADER_FONT
            c.alignment = CENTER
            c.border = BORDER
    # row 5~7 값
    for i, (env, who, _ver_label, ver) in enumerate(env_rows):
        r = 5 + i
        c1 = ws.cell(row=r, column=2, value=env); c1.fill = PatternFill("solid", fgColor="00FF00"); c1.font = HEADER_FONT; c1.alignment = CENTER; c1.border = BORDER
        c2 = ws.cell(row=r, column=3, value=who); c2.alignment = CENTER; c2.border = BORDER
        c3 = ws.cell(row=r, column=4, value="version"); c3.fill = PatternFill("solid", fgColor="00FF00"); c3.font = HEADER_FONT; c3.alignment = CENTER; c3.border = BORDER
        c4 = ws.cell(row=r, column=5, value=ver); c4.alignment = CENTER; c4.border = BORDER

    # 통계 헤더 (Row 9)
    stat_header = ["구분", "검증 항목", "Pass", "Fail", "Block", "N/A", "성공율", "결함율", "수행율"]
    for j, label in enumerate(stat_header):
        c = ws.cell(row=9, column=2 + j, value=label)
        c.fill = GRAY
        c.font = HEADER_FONT
        c.alignment = CENTER
        c.border = BORDER

    # 통계 데이터: 각 (screen_platform) 시트별로 COUNTA/COUNTIF
    pct = "0.00%"
    fixed_rows = 9   # 빈 슬롯 9개로 고정 (참조 예시 row 10~18)
    start = 10
    for i in range(fixed_rows):
        r = start + i
        # 모든 셀에 테두리
        for col in range(2, 11):
            ws.cell(row=r, column=col).border = BORDER
            ws.cell(row=r, column=col).alignment = CENTER

        if i < len(tab_data):
            tab, count = tab_data[i]
            esc = tab.replace("'", "''")
            last = DATA_START_ROW + count - 1   # 명시적 마지막 행
            ref_b = f"'{esc}'!B{DATA_START_ROW}:B{last}"   # TC ID 컬럼
            ref_k = f"'{esc}'!K{DATA_START_ROW}:K{last}"   # result 컬럼

            ws.cell(row=r, column=2, value=tab)
            ws.cell(row=r, column=3, value=f"=COUNTA({ref_b})")            # 검증 항목
            ws.cell(row=r, column=4, value=f'=COUNTIF({ref_k},"Pass")')   # Pass
            ws.cell(row=r, column=5, value=f'=COUNTIF({ref_k},"Fail")')   # Fail
            ws.cell(row=r, column=6, value=f'=COUNTIF({ref_k},"Block")')  # Block
            ws.cell(row=r, column=7, value=f'=COUNTIF({ref_k},"N/A")')    # N/A
            # 성공율 = Pass / 검증항목
            ws.cell(row=r, column=8, value=f"=IFERROR(D{r}/C{r},0)").number_format = pct
            # 결함율 = Fail / 검증항목
            ws.cell(row=r, column=9, value=f"=IFERROR(E{r}/C{r},0)").number_format = pct
            # 수행율 = (Pass+Fail+Block) / 검증항목
            ws.cell(row=r, column=10, value=f"=IFERROR((D{r}+E{r}+F{r})/C{r},0)").number_format = pct

    # 총 합계 (Row 19)
    total_r = start + fixed_rows
    last_data_r = start + fixed_rows - 1
    c = ws.cell(row=total_r, column=2, value="총 합계"); c.fill = GRAY; c.font = HEADER_FONT; c.alignment = CENTER; c.border = BORDER
    for col_idx, formula_col in [(3, "C"), (4, "D"), (5, "E"), (6, "F"), (7, "G")]:
        cc = ws.cell(row=total_r, column=col_idx, value=f"=SUM({formula_col}{start}:{formula_col}{last_data_r})")
        cc.fill = GRAY; cc.font = HEADER_FONT; cc.alignment = CENTER; cc.border = BORDER
    # 합계 비율
    cc = ws.cell(row=total_r, column=8, value=f"=IFERROR(D{total_r}/C{total_r},0)"); cc.number_format = pct; cc.fill = GRAY; cc.font = HEADER_FONT; cc.alignment = CENTER; cc.border = BORDER
    cc = ws.cell(row=total_r, column=9, value=f"=IFERROR(E{total_r}/C{total_r},0)"); cc.number_format = pct; cc.fill = GRAY; cc.font = HEADER_FONT; cc.alignment = CENTER; cc.border = BORDER
    cc = ws.cell(row=total_r, column=10, value=f"=IFERROR((D{total_r}+E{total_r}+F{total_r})/C{total_r},0)"); cc.number_format = pct; cc.fill = GRAY; cc.font = HEADER_FONT; cc.alignment = CENTER; cc.border = BORDER


def main(argv: list[str]) -> int:
    app_name = argv[1] if len(argv) > 1 else "app"
    if not SRC_DIR.exists():
        print(f"[export_workbook] {SRC_DIR} 없음", file=sys.stderr)
        return 1

    sources = sorted(SRC_DIR.glob("*.json"))
    if not sources:
        print("[export_workbook] outputs/testcases/*.json 없음", file=sys.stderr)
        return 1

    all_tcs: list[dict] = []
    for s in sources:
        all_tcs.extend(load_json(s))

    groups = group_by_tab(all_tcs)
    if not groups:
        print("[export_workbook] 유효한 (screen, platform) 그룹 없음", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{app_name}.xlsx"

    wb = Workbook()
    # 기본 시트 제거
    default = wb.active
    wb.remove(default)

    # 시트 이름·TC개수 (참조 시트와 동일 패턴: "{screen}_{platform}")
    tab_data: list[tuple[str, int]] = []
    for (screen, platform), tcs in sorted(groups.items()):
        sheet_name = f"{screen}_{platform}"
        add_tc_sheet(wb, sheet_name, tcs)
        tab_data.append((sheet_name, len(tcs)))

    # summury 시트는 마지막에 추가하되 index=0으로 맨 앞 배치
    add_summury_sheet(wb, app_name, tab_data)

    wb.save(out_path)
    rel = out_path.relative_to(ROOT)
    total = sum(len(v) for v in groups.values())
    print(f"[export_workbook] wrote {rel}  ({len(tab_data)} sheets, {total} TC)")
    for name, count in tab_data:
        print(f"  - {name}  ({count} TC)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
