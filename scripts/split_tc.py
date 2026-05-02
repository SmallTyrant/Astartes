#!/usr/bin/env python3
"""
split_tc.py — tc-reviewed.json을 (screen, platform) 탭 단위 파일로 분기.
LLM tc-platform-splitter 에이전트를 완전 대체하는 스크립트.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 표현 치환 테이블
# ---------------------------------------------------------------------------
WEB_REPLACEMENTS = [
    ("딥링크", "URL"),
    ("deep link", "URL"),
    ("앱 재진입", "탭 활성화"),
    ("포그라운드 복귀", "탭 활성화"),
    ("백그라운드 진입", "탭 비활성화 (visibility hidden)"),
    ("생체 인증", "WebAuthn 또는 OTP"),
    ("푸시 알림", "브라우저 알림"),
    ("Pull to refresh", "새로고침 (F5)"),
]

MOBILE_REPLACEMENTS = [
    ("URL을 입력한다", "딥링크를 연다"),
    ("URL을 입력하면", "딥링크를 열면"),
    ("탭 비활성화", "백그라운드 진입"),
    ("탭 활성화", "포그라운드 복귀"),
    ("WebAuthn", "생체 인증"),
]


def apply_replacements(text: str, replacements: list[tuple[str, str]]) -> str:
    for src, dst in replacements:
        text = text.replace(src, dst)
    return text


def transform_text(text: str, platform: str) -> str:
    if platform == "web":
        return apply_replacements(text, WEB_REPLACEMENTS)
    else:
        return apply_replacements(text, MOBILE_REPLACEMENTS)


def normalize_platform(raw: str) -> str:
    """'android' → 'and', 소문자 통일."""
    raw = raw.strip().lower()
    if raw == "android":
        return "and"
    return raw


def screen_to_slug(screen: str) -> str:
    """공백 → '_', 특수문자 제거."""
    slug = screen.replace(" ", "_")
    slug = re.sub(r"[^\w가-힣]", "", slug)
    return slug or "미분류"


def determine_platforms(tc: dict, target_platforms: list[str]) -> list[str]:
    """TC에서 적용 플랫폼 목록 결정."""
    if "platform" in tc and tc["platform"]:
        p = normalize_platform(str(tc["platform"]))
        if p in target_platforms:
            return [p]
        return []
    if "platforms" in tc and tc["platforms"]:
        result = []
        for raw in tc["platforms"]:
            p = normalize_platform(str(raw))
            if p in target_platforms:
                result.append(p)
        return list(dict.fromkeys(result))  # dedupe, preserve order
    # 플랫폼 정보 없음 → target_platforms 전체 복제
    return list(target_platforms)


def transform_tc(tc: dict, platform: str) -> dict:
    """TC를 플랫폼에 맞게 표현 치환 후 반환 (원본 변경 없음)."""
    out = dict(tc)

    # steps 치환
    steps = list(out.get("steps", []))
    new_steps = []
    for step in steps:
        if isinstance(step, str):
            new_steps.append(transform_text(step, platform))
        else:
            new_steps.append(step)

    # expected 치환
    expected = out.get("expected", "")
    if isinstance(expected, str):
        expected = transform_text(expected, platform)

    # steps 길이 5 초과 절단
    needs_review = out.get("needs_review", False)
    if len(new_steps) > 5:
        new_steps = new_steps[:5]
        needs_review = True

    out["steps"] = new_steps
    out["expected"] = expected
    out["platform"] = platform
    if needs_review:
        out["needs_review"] = True

    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="tc-reviewed.json을 (screen, platform) 탭 단위 파일로 분기"
    )
    parser.add_argument(
        "--target-platforms",
        default="ios,android,web",
        help="대상 플랫폼 목록 (쉼표 구분). 기본값: ios,android,web",
    )
    parser.add_argument(
        "--input",
        default="outputs/intermediate/tc-reviewed.json",
        help="입력 파일 경로. 기본값: outputs/intermediate/tc-reviewed.json",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/testcases/",
        help="출력 디렉터리. 기본값: outputs/testcases/",
    )
    args = parser.parse_args()

    # 플랫폼 정규화
    target_platforms = [
        normalize_platform(p) for p in args.target_platforms.split(",") if p.strip()
    ]

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(
            f"오류: 입력 파일을 찾을 수 없습니다: {input_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with input_path.open(encoding="utf-8") as f:
            tc_list = json.load(f)
    except json.JSONDecodeError as e:
        print(f"오류: JSON 파싱 실패 ({input_path}): {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(tc_list, list):
        print("오류: 입력 JSON은 배열이어야 합니다.", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # (screen_slug, platform) → [tc, ...]
    buckets: dict[tuple[str, str], list[dict]] = {}

    for tc in tc_list:
        screen = tc.get("screen") or "미분류"
        slug = screen_to_slug(screen)
        platforms = determine_platforms(tc, target_platforms)

        for platform in platforms:
            key = (slug, platform)
            if key not in buckets:
                buckets[key] = []
            buckets[key].append(transform_tc(tc, platform))

    # tc_id 재부여 및 파일 저장
    files_created = 0
    total_tcs = 0

    for (slug, platform), tcs in sorted(buckets.items()):
        for idx, tc in enumerate(tcs, start=1):
            tc["tc_id"] = idx

        filename = f"{slug}_{platform}.json"
        out_path = output_dir / filename
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(tcs, f, ensure_ascii=False, indent=2)

        files_created += 1
        total_tcs += len(tcs)

    print(f"split: {files_created}개 파일 생성 ({total_tcs}개 TC)")


if __name__ == "__main__":
    main()
