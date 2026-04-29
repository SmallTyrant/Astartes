#!/usr/bin/env python3
"""TC JSON 스키마 v3 (시트 형식 통일) 검증 hook.

기준 스프레드시트 컬럼: TC ID | priority | 1 Step .. 5 Step | pre-condition | 기대결과 | result | Jira ticket
탭 명명 규칙: {screen}_{platform}  (platform: and|ios|web)

검증 대상 필드:
  필수: tc_id, screen, platform, priority, precondition, steps, expected
  내부: requirement_id, source_refs[], risk_tags[], negative, needs_review (있으면 검증)
  시트 통과: jira_ticket, result (없으면 빈 문자열로 간주)

구 스키마(v2: id/title/category/platforms[]/preconditions[]/steps[].action+expected) 자동 마이그레이션 후 검증.
"""
import json
import os
import sys
from pathlib import Path

REQUIRED_TOP = {"tc_id", "screen", "platform", "priority",
                "precondition", "steps", "expected"}
ALLOWED_PRIORITY = {"high", "mid", "low"}
ALLOWED_PLATFORM = {"and", "ios", "web"}
SECURITY_RISK_TAGS = {"auth", "session", "data", "input",
                      "network", "storage", "payment"}
VAGUE_VERBS = ["확인한다", "본다", "체크한다", "잘 동작한다"]

PRIORITY_LEGACY_MAP = {"P0": "high", "P1": "mid", "P2": "low",
                       "High": "high", "Mid": "mid", "Low": "low",
                       "HIGH": "high", "MID": "mid", "LOW": "low"}
PLATFORM_LEGACY_MAP = {"android": "and", "Android": "and", "AND": "and",
                       "ios": "ios", "iOS": "ios", "IOS": "ios",
                       "web": "web", "Web": "web", "WEB": "web"}


def normalize_legacy(tc: dict) -> tuple[dict, list]:
    """v2 → v3 마이그레이션. 변환된 사본과 마이그레이션 사유(warns)를 반환."""
    tc = dict(tc)
    warns: list[str] = []

    # tc_id ← id (마지막 숫자 추출)
    if "tc_id" not in tc and "id" in tc:
        import re
        m = re.search(r"(\d+)\s*$", str(tc["id"]))
        if m:
            tc["tc_id"] = int(m.group(1))
            warns.append("'id' → 'tc_id' 자동 변환")

    # priority 매핑
    if tc.get("priority") in PRIORITY_LEGACY_MAP:
        tc["priority"] = PRIORITY_LEGACY_MAP[tc["priority"]]
        warns.append("priority(P0/P1/P2) → high/mid/low 변환")

    # platform 단일화: platforms[] 또는 platform 단수
    if "platform" not in tc:
        plats = tc.get("platforms") or []
        if isinstance(plats, str):
            plats = [plats]
        if plats:
            mapped = [PLATFORM_LEGACY_MAP.get(p, p) for p in plats]
            tc["platform"] = mapped[0]
            if len(mapped) > 1:
                warns.append(f"platforms{mapped} → 첫 항목 '{mapped[0]}'만 사용. splitter로 분리 필요.")
    elif tc["platform"] in PLATFORM_LEGACY_MAP:
        tc["platform"] = PLATFORM_LEGACY_MAP[tc["platform"]]

    # precondition: preconditions[] → 단일 문자열
    if "precondition" not in tc and "preconditions" in tc:
        pc = tc["preconditions"]
        if isinstance(pc, list):
            tc["precondition"] = "\n".join(str(x) for x in pc)
        else:
            tc["precondition"] = str(pc or "")
        warns.append("preconditions[] → precondition(단일) 변환")

    # steps: [{action,expected}] → [str], expected는 마지막에 합산
    if "steps" in tc and tc["steps"] and isinstance(tc["steps"][0], dict):
        actions = []
        expecteds = []
        for s in tc["steps"]:
            if "action" in s:
                actions.append(str(s.get("action", "")))
            if s.get("expected"):
                expecteds.append(str(s["expected"]))
        tc["steps"] = actions
        if "expected" not in tc and expecteds:
            tc["expected"] = " / ".join(expecteds)
        warns.append("steps[{action,expected}] → steps[str] + expected(합산) 변환")

    # title 흡수: 없으면 그냥 무시 가능
    tc.setdefault("expected", "")
    tc.setdefault("precondition", "")
    tc.setdefault("jira_ticket", "")
    tc.setdefault("result", "")

    return tc, warns


def validate(tc_in: dict, ctx: str) -> tuple[list, list]:
    errs: list[str] = []
    warns: list[str] = []

    tc, mig_warns = normalize_legacy(tc_in)
    for w in mig_warns:
        warns.append(f"{ctx}: {w}")

    missing = REQUIRED_TOP - tc.keys()
    if missing:
        errs.append(f"{ctx}: 필수 필드 누락 {sorted(missing)}")

    if not isinstance(tc.get("tc_id"), int):
        errs.append(f"{ctx}: tc_id는 정수여야 함 ({tc.get('tc_id')!r})")

    if tc.get("priority") not in ALLOWED_PRIORITY:
        errs.append(f"{ctx}: priority 값 오류 ({tc.get('priority')!r}) — 허용: {sorted(ALLOWED_PRIORITY)}")

    if tc.get("platform") not in ALLOWED_PLATFORM:
        errs.append(f"{ctx}: platform 값 오류 ({tc.get('platform')!r}) — 허용: {sorted(ALLOWED_PLATFORM)}")

    screen = tc.get("screen")
    if not isinstance(screen, str) or not screen.strip():
        errs.append(f"{ctx}: screen 비어있음")

    steps = tc.get("steps")
    if not isinstance(steps, list) or not (1 <= len(steps) <= 5):
        errs.append(f"{ctx}: steps 길이 1~5 필요 (현재 {len(steps) if isinstance(steps, list) else 'non-list'})")
    else:
        for i, s in enumerate(steps):
            if not isinstance(s, str) or not s.strip():
                errs.append(f"{ctx}: steps[{i}] 빈 문자열")

    expected = tc.get("expected", "")
    if not isinstance(expected, str) or not expected.strip():
        errs.append(f"{ctx}: expected 비어있음")
    else:
        for v in VAGUE_VERBS:
            if v in expected:
                errs.append(f"{ctx}: expected에 모호한 표현 '{v}'")

    # 내부 추적성: requirement_id 권장 (없으면 warn)
    if not tc.get("requirement_id"):
        warns.append(f"{ctx}: requirement_id 비어있음 (추적성 약화)")

    src = tc.get("source_refs")
    if src is not None:
        if not isinstance(src, list):
            errs.append(f"{ctx}: source_refs는 배열이어야 함")
        else:
            for i, sr in enumerate(src):
                if not isinstance(sr, dict) or "type" not in sr or "id" not in sr:
                    errs.append(f"{ctx}: source_refs[{i}] type/id 누락")

    # 보안 위험 태그: 있으면 risk_tags에 보안 카테고리 포함되어야 함
    rt = set(tc.get("risk_tags") or [])
    if rt and rt & SECURITY_RISK_TAGS:
        # 보안 TC는 priority high 권장
        if tc.get("priority") != "high":
            warns.append(f"{ctx}: risk_tags={sorted(rt & SECURITY_RISK_TAGS)} 인데 priority={tc.get('priority')!r} (high 권장)")

    return errs, warns


def resolve_path() -> Path | None:
    if len(sys.argv) >= 2 and sys.argv[1]:
        return Path(sys.argv[1])
    if os.environ.get("FILE_PATH"):
        return Path(os.environ["FILE_PATH"])
    if not sys.stdin.isatty():
        try:
            data = json.load(sys.stdin)
            fp = data.get("tool_input", {}).get("file_path") or data.get("file_path")
            if fp:
                return Path(fp)
        except Exception:
            pass
    return None


def main():
    path = resolve_path()
    if path is None or not path.exists() or path.suffix != ".json":
        sys.exit(0)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[validate_tc] {path}: JSON 파싱 실패 - {e}", file=sys.stderr)
        sys.exit(2)

    if isinstance(data, dict) and "testcases" in data:
        tcs = data["testcases"]
    elif isinstance(data, list):
        tcs = data
    else:
        tcs = [data]

    all_errs: list[str] = []
    all_warns: list[str] = []
    for i, tc in enumerate(tcs):
        if isinstance(tc, dict):
            errs, warns = validate(tc, f"{path.name}#{i}")
            all_errs.extend(errs)
            all_warns.extend(warns)

    for w in all_warns:
        print(f"[validate_tc] WARN: {w}", file=sys.stderr)

    if all_errs:
        print(f"[validate_tc] {path} 스키마(v3) 검증 실패:", file=sys.stderr)
        for e in all_errs:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
