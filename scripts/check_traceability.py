#!/usr/bin/env python3
"""
TC 추적성 검증 스크립트.

기능:
- outputs/testcases/testcases.final.json 읽기
- requirement_id 누락 TC 검출
- requirement에 매핑된 TC가 0개인 항목 검출
- outputs/traceability.csv 생성
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TC_DIR = ROOT / "outputs" / "testcases"
FINAL_FILES = [
    TC_DIR / "testcases.ios.final.json",
    TC_DIR / "testcases.android.final.json",
    TC_DIR / "testcases.web.final.json",
]
LEGACY_FINAL = TC_DIR / "testcases.final.json"
REVIEWED_JSON = TC_DIR / "testcases.reviewed.json"
REQUIREMENTS_JSON = ROOT / "outputs" / "intermediate" / "requirements.json"
TRACEABILITY_CSV = ROOT / "outputs" / "traceability.csv"


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_testcases_file(path: Path) -> list[dict]:
    data = load_json(path)
    if isinstance(data, dict) and "testcases" in data:
        return data["testcases"]
    if isinstance(data, list):
        return data
    print(f"[ERROR] TC JSON 구조를 인식할 수 없습니다: {path}", file=sys.stderr)
    sys.exit(1)


def load_all_testcases() -> list[dict]:
    """플랫폼별 final 3종 합집합. 없으면 legacy testcases.final.json → reviewed.json 순 폴백."""
    found: list[dict] = []
    for path in FINAL_FILES:
        if path.exists():
            found.extend(load_testcases_file(path))
    if found:
        return found
    if LEGACY_FINAL.exists():
        return load_testcases_file(LEGACY_FINAL)
    if REVIEWED_JSON.exists():
        print(f"[WARN] platform별 final 없음, {REVIEWED_JSON.name} 사용", file=sys.stderr)
        return load_testcases_file(REVIEWED_JSON)
    print(f"[ERROR] TC 파일이 없습니다: {[str(p) for p in FINAL_FILES]}", file=sys.stderr)
    sys.exit(1)


def load_requirement_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = load_json(path)
    items = data.get("requirements", data) if isinstance(data, dict) else data
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict) and "id" in item:
            ids.append(item["id"])
    return ids


def main() -> int:
    testcases = load_all_testcases()
    declared_req_ids = load_requirement_ids(REQUIREMENTS_JSON)

    missing_req: list[str] = []
    req_to_tcs: dict[str, list[str]] = defaultdict(list)

    for tc in testcases:
        tc_id = tc.get("id", "<no-id>")
        req_id = tc.get("requirement_id")
        if not req_id:
            missing_req.append(tc_id)
            continue
        req_to_tcs[req_id].append(tc_id)

    orphan_reqs = [rid for rid in declared_req_ids if rid not in req_to_tcs]

    TRACEABILITY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with TRACEABILITY_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["requirement_id", "tc_count", "tc_ids"])
        all_req_ids = sorted(set(declared_req_ids) | set(req_to_tcs.keys()))
        for rid in all_req_ids:
            tc_ids = req_to_tcs.get(rid, [])
            writer.writerow([rid, len(tc_ids), ";".join(tc_ids)])

    print(f"[OK] traceability.csv 생성: {TRACEABILITY_CSV}")
    print(f"  - 전체 TC: {len(testcases)}개")
    print(f"  - 매핑된 requirement: {len(req_to_tcs)}개")

    exit_code = 0
    if missing_req:
        print(f"[FAIL] requirement_id 누락 TC {len(missing_req)}건:", file=sys.stderr)
        for tc_id in missing_req:
            print(f"  - {tc_id}", file=sys.stderr)
        exit_code = 1

    if orphan_reqs:
        print(f"[FAIL] TC가 0개인 requirement {len(orphan_reqs)}건:", file=sys.stderr)
        for rid in orphan_reqs:
            print(f"  - {rid}", file=sys.stderr)
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
