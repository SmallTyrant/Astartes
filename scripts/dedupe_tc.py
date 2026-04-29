#!/usr/bin/env python3
"""
TC 중복 검출 스크립트.

검출 대상:
- id 중복
- title 유사 중복 (정규화 후 동일 또는 SequenceMatcher ratio >= 0.9)
- 동일 steps 중복 (action+expected 시퀀스가 동일)
- requirement_id + title 중복
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TC_DIR = ROOT / "outputs" / "testcases"
DEFAULT_INPUTS = [
    TC_DIR / "testcases.ios.final.json",
    TC_DIR / "testcases.android.final.json",
    TC_DIR / "testcases.web.final.json",
]
LEGACY_FINAL = TC_DIR / "testcases.final.json"
REVIEWED_JSON = TC_DIR / "testcases.reviewed.json"

TITLE_SIMILARITY_THRESHOLD = 0.9
PLATFORM_SUFFIX_RE = re.compile(r"-(?:ios|and|web)$")
WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\"'`.,!?()\[\]{}<>~_\-/:;]")


def load_testcases(path: Path) -> list[dict]:
    if not path.exists():
        print(f"[ERROR] 파일이 없습니다: {path}", file=sys.stderr)
        sys.exit(1)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "testcases" in data:
        return data["testcases"]
    if isinstance(data, list):
        return data
    print(f"[ERROR] TC JSON 구조를 인식할 수 없습니다: {path}", file=sys.stderr)
    sys.exit(1)


def load_default_inputs() -> tuple[list[dict], list[Path]]:
    """기본 입력으로 플랫폼별 final 3종 합집합. 없으면 legacy → reviewed 폴백."""
    used: list[Path] = []
    found: list[dict] = []
    for p in DEFAULT_INPUTS:
        if p.exists():
            found.extend(load_testcases(p))
            used.append(p)
    if found:
        return found, used
    for fb in (LEGACY_FINAL, REVIEWED_JSON):
        if fb.exists():
            return load_testcases(fb), [fb]
    print(f"[ERROR] 기본 입력 없음. 인자로 경로를 지정하세요.", file=sys.stderr)
    sys.exit(1)


def base_id(tc_id: str) -> str:
    """플랫폼 suffix(-ios/-and/-web) 제거. 동일 base_id를 가지면 splitter 산출 동일 케이스로 간주."""
    if not tc_id:
        return tc_id
    return PLATFORM_SUFFIX_RE.sub("", tc_id)


def normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.lower()
    t = PUNCT_RE.sub(" ", t)
    t = WHITESPACE_RE.sub(" ", t).strip()
    return t


def steps_signature(steps: list[dict]) -> tuple:
    sig = []
    for s in steps or []:
        action = WHITESPACE_RE.sub(" ", (s.get("action") or "").strip().lower())
        expected = WHITESPACE_RE.sub(" ", (s.get("expected") or "").strip().lower())
        sig.append((action, expected))
    return tuple(sig)


def find_id_duplicates(testcases: list[dict], strip_platform_suffix: bool = False) -> dict[str, list[int]]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for idx, tc in enumerate(testcases):
        tc_id = tc.get("id")
        if tc_id:
            key = base_id(tc_id) if strip_platform_suffix else tc_id
            buckets[key].append(idx)
    return {k: v for k, v in buckets.items() if len(v) > 1}


def find_steps_duplicates(testcases: list[dict]) -> list[list[int]]:
    buckets: dict[tuple, list[int]] = defaultdict(list)
    for idx, tc in enumerate(testcases):
        sig = steps_signature(tc.get("steps", []))
        if sig:
            buckets[sig].append(idx)
    return [v for v in buckets.values() if len(v) > 1]


def find_req_title_duplicates(testcases: list[dict]) -> dict[tuple[str, str], list[int]]:
    buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for idx, tc in enumerate(testcases):
        rid = tc.get("requirement_id")
        title_norm = normalize_title(tc.get("title", ""))
        if rid and title_norm:
            buckets[(rid, title_norm)].append(idx)
    return {k: v for k, v in buckets.items() if len(v) > 1}


def find_title_similar_pairs(testcases: list[dict]) -> list[tuple[int, int, float]]:
    titles = [normalize_title(tc.get("title", "")) for tc in testcases]
    pairs: list[tuple[int, int, float]] = []
    for i in range(len(titles)):
        if not titles[i]:
            continue
        for j in range(i + 1, len(titles)):
            if not titles[j]:
                continue
            if titles[i] == titles[j]:
                pairs.append((i, j, 1.0))
                continue
            ratio = SequenceMatcher(None, titles[i], titles[j]).ratio()
            if ratio >= TITLE_SIMILARITY_THRESHOLD:
                pairs.append((i, j, ratio))
    return pairs


def fmt(tc: dict) -> str:
    return f"{tc.get('id', '<no-id>')} | {tc.get('title', '')[:60]}"


def main() -> int:
    args = sys.argv[1:]
    strip_suffix = False
    if "--ignore-platform-suffix" in args:
        strip_suffix = True
        args.remove("--ignore-platform-suffix")

    if args:
        input_path = Path(args[0])
        testcases = load_testcases(input_path)
        print(f"[INFO] 검사 대상: {input_path} ({len(testcases)}개 TC)")
    else:
        testcases, used = load_default_inputs()
        labels = ", ".join(p.name for p in used)
        print(f"[INFO] 검사 대상 ({len(testcases)}개 TC) 합집합: {labels}")
        if strip_suffix:
            print("[INFO] --ignore-platform-suffix: base_id로 비교 (splitter 산출 동일 케이스가 중복으로 잡힘)")

    id_dups = find_id_duplicates(testcases, strip_platform_suffix=strip_suffix)
    steps_dups = find_steps_duplicates(testcases)
    req_title_dups = find_req_title_duplicates(testcases)
    title_similar = find_title_similar_pairs(testcases)

    exit_code = 0

    if id_dups:
        exit_code = 1
        print(f"\n[FAIL] id 중복 {len(id_dups)}건:")
        for tc_id, idxs in id_dups.items():
            print(f"  - id={tc_id} → indices={idxs}")
            for i in idxs:
                print(f"      · {fmt(testcases[i])}")

    if steps_dups:
        exit_code = 1
        print(f"\n[FAIL] 동일 steps 중복 {len(steps_dups)}건:")
        for group in steps_dups:
            print(f"  - indices={group}")
            for i in group:
                print(f"      · {fmt(testcases[i])}")

    if req_title_dups:
        exit_code = 1
        print(f"\n[FAIL] requirement_id+title 중복 {len(req_title_dups)}건:")
        for (rid, title), idxs in req_title_dups.items():
            print(f"  - req={rid} title='{title[:50]}' indices={idxs}")
            for i in idxs:
                print(f"      · {fmt(testcases[i])}")

    if title_similar:
        exit_code = 1
        print(f"\n[FAIL] title 유사 중복 {len(title_similar)}건 (threshold={TITLE_SIMILARITY_THRESHOLD}):")
        for i, j, ratio in title_similar:
            print(f"  - ratio={ratio:.2f}")
            print(f"      · {fmt(testcases[i])}")
            print(f"      · {fmt(testcases[j])}")

    if exit_code == 0:
        print("[OK] 중복 없음")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
