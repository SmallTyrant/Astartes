#!/usr/bin/env python3
"""
normalize_tc.py — tc-{functional,security,negative}.json을 v3 스키마로 정규화.
LLM tc-normalizer 에이전트를 완전 대체하는 스크립트.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
DEFAULT_INPUTS = (
    "outputs/intermediate/tc-functional.json,"
    "outputs/intermediate/tc-security.json,"
    "outputs/intermediate/tc-negative.json"
)
DEFAULT_OUTPUT = "outputs/intermediate/tc-reviewed.json"

VALID_PLATFORMS = {"and", "ios", "web"}
PRIORITY_MAP = {
    "p0": "high",
    "p1": "mid",
    "p2": "low",
    "high": "high",
    "mid": "mid",
    "low": "low",
}
AMBIGUOUS_VERBS = ["확인한다", "본다", "체크한다", "잘 동작한다"]


# ---------------------------------------------------------------------------
# 정규화 헬퍼
# ---------------------------------------------------------------------------

def normalize_platform(raw) -> tuple[str, bool]:
    """(정규화된_플랫폼, needs_review) 반환."""
    if not raw:
        return "web", True
    s = str(raw).strip().lower()
    if s == "android":
        return "and", False
    if s in VALID_PLATFORMS:
        return s, False
    return "web", True


def normalize_priority(raw) -> str:
    if not raw:
        return "mid"
    key = str(raw).strip().lower()
    return PRIORITY_MAP.get(key, "mid")


def normalize_precondition(tc: dict) -> str:
    # 구 preconditions[] 처리
    if "preconditions" in tc and isinstance(tc["preconditions"], list):
        return "\n".join(str(x) for x in tc["preconditions"])
    return str(tc.get("precondition") or "")


def normalize_steps_and_expected(tc: dict) -> tuple[list[str], str, bool]:
    """(steps, expected, needs_review) 반환."""
    needs_review = False
    raw_steps = tc.get("steps", [])
    raw_expected = str(tc.get("expected") or "")

    steps: list[str] = []
    collected_expected_parts: list[str] = []

    # 구 [{action, expected}] 형태
    if raw_steps and isinstance(raw_steps[0], dict):
        for item in raw_steps:
            action = str(item.get("action") or "")
            exp = str(item.get("expected") or "")
            if action:
                steps.append(action)
            if exp:
                collected_expected_parts.append(exp)
        if collected_expected_parts and not raw_expected:
            raw_expected = " / ".join(collected_expected_parts)
    else:
        steps = [str(s) for s in raw_steps if s]

    # steps 5개 초과 절단
    if len(steps) > 5:
        extra = steps[5:]
        steps = steps[:5]
        suffix = " / ".join(extra)
        if raw_expected:
            raw_expected = raw_expected + " / " + suffix
        else:
            raw_expected = suffix
        needs_review = True

    # expected 비어있으면 마지막 step에서 복사
    if not raw_expected and steps:
        raw_expected = steps[-1]
        needs_review = True

    # 모호한 동사 검사
    if any(v in raw_expected for v in AMBIGUOUS_VERBS):
        needs_review = True
    for step in steps:
        if any(v in step for v in AMBIGUOUS_VERBS):
            needs_review = True

    return steps, raw_expected, needs_review


def extract_last_int(s: str) -> int | None:
    """문자열에서 마지막 숫자 그룹 추출. 예: 'TC-LOGIN-001' → 1"""
    matches = re.findall(r"\d+", s)
    if matches:
        return int(matches[-1])
    return None


def normalize_tc_id(tc: dict, screen: str, platform: str, counter: dict) -> int:
    """(screen, platform) 그룹 안에서 tc_id를 결정."""
    group_key = (screen, platform)
    raw = tc.get("tc_id")

    if raw is None or raw == "":
        # 구 id 필드 확인
        old_id = tc.get("id")
        if old_id:
            extracted = extract_last_int(str(old_id))
            if extracted is not None:
                counter[group_key] = max(counter.get(group_key, 0), extracted)
                return extracted

        # 자동 채번
        counter[group_key] = counter.get(group_key, 0) + 1
        return counter[group_key]

    # 기존 값 사용 (정수 변환 시도)
    if isinstance(raw, int):
        counter[group_key] = max(counter.get(group_key, 0), raw)
        return raw
    extracted = extract_last_int(str(raw))
    if extracted is not None:
        counter[group_key] = max(counter.get(group_key, 0), extracted)
        return extracted

    counter[group_key] = counter.get(group_key, 0) + 1
    return counter[group_key]


def infer_risk_tags(tc: dict, source_filename: str) -> list[str]:
    existing = tc.get("risk_tags")
    if existing:
        return existing
    name = source_filename.lower()
    if "security" in name:
        return ["auth"]
    if "negative" in name:
        return ["network"]
    return []


FIELDS_TO_REMOVE = {"id", "title", "category", "platforms", "preconditions", "masvs_refs"}


def normalize_single_tc(tc: dict, source_filename: str, id_counter: dict) -> dict:
    """단일 TC를 v3 스키마로 정규화."""
    out: dict = {}
    needs_review = bool(tc.get("needs_review", False))

    # screen
    screen = str(tc.get("screen") or "").strip()
    if not screen:
        screen = "미분류"
        needs_review = True
    out["screen"] = screen

    # platform
    platform, p_flag = normalize_platform(tc.get("platform"))
    if p_flag:
        needs_review = True
    out["platform"] = platform

    # tc_id
    out["tc_id"] = normalize_tc_id(tc, screen, platform, id_counter)

    # priority
    out["priority"] = normalize_priority(tc.get("priority"))

    # precondition
    out["precondition"] = normalize_precondition(tc)

    # steps + expected
    steps, expected, se_flag = normalize_steps_and_expected(tc)
    if se_flag:
        needs_review = True
    out["steps"] = steps
    out["expected"] = expected

    # jira_ticket, result
    out["jira_ticket"] = ""
    out["result"] = ""

    # 내부 필드 보존
    out["requirement_id"] = tc.get("requirement_id", "")
    out["negative"] = tc.get("negative", False)

    # source_refs
    source_refs = tc.get("source_refs")
    if not source_refs:
        source_refs = [{"type": "prd", "id": "unknown"}]
        needs_review = True
    out["source_refs"] = source_refs

    # risk_tags
    out["risk_tags"] = infer_risk_tags(tc, source_filename)

    # needs_review
    out["needs_review"] = needs_review

    return out


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def load_json_file(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "testcases" in data:
        return data["testcases"]
    return [data]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TC JSON을 v3 스키마로 정규화하여 tc-reviewed.json에 저장"
    )
    parser.add_argument(
        "--inputs",
        default=DEFAULT_INPUTS,
        help="입력 파일 경로 목록 (쉼표 구분)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"출력 파일 경로. 기본값: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--mode",
        choices=["replace", "merge"],
        default="replace",
        help="replace: 전체 덮어쓰기 (기본값), merge: 기존 파일에 append",
    )
    args = parser.parse_args()

    input_paths = [Path(p.strip()) for p in args.inputs.split(",") if p.strip()]
    output_path = Path(args.output)

    # merge 모드: 기존 출력 파일 로드
    existing_tcs: list[dict] = []
    existing_keys: set[tuple] = set()
    if args.mode == "merge" and output_path.exists():
        try:
            existing_tcs = load_json_file(output_path)
            for tc in existing_tcs:
                key = (
                    tc.get("screen", ""),
                    tc.get("platform", ""),
                    tc.get("tc_id"),
                )
                existing_keys.add(key)
        except (json.JSONDecodeError, OSError) as e:
            print(
                f"경고: 기존 출력 파일 로드 실패 ({output_path}): {e}",
                file=sys.stderr,
            )

    id_counter: dict[tuple, int] = {}
    all_normalized: list[dict] = []
    total_needs_review = 0

    for input_path in input_paths:
        if not input_path.exists():
            print(
                f"경고: 입력 파일 없음, 건너뜀: {input_path}",
                file=sys.stderr,
            )
            continue

        try:
            raw_list = load_json_file(input_path)
        except json.JSONDecodeError as e:
            print(
                f"오류: JSON 파싱 실패 ({input_path}): {e}",
                file=sys.stderr,
            )
            sys.exit(1)

        fname = input_path.name
        for tc in raw_list:
            normalized = normalize_single_tc(tc, fname, id_counter)

            if args.mode == "merge":
                key = (
                    normalized.get("screen", ""),
                    normalized.get("platform", ""),
                    normalized.get("tc_id"),
                )
                if key in existing_keys:
                    print(
                        f"충돌 skip: screen={key[0]}, platform={key[1]}, tc_id={key[2]}",
                        file=sys.stderr,
                    )
                    continue
                existing_keys.add(key)

            all_normalized.append(normalized)
            if normalized.get("needs_review"):
                total_needs_review += 1

    # merge 모드면 기존 TC 앞에 붙임
    final_list = existing_tcs + all_normalized if args.mode == "merge" else all_normalized

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)

    print(
        f"normalized: {len(all_normalized)}개 TC (needs_review: {total_needs_review}개)"
    )


if __name__ == "__main__":
    main()
