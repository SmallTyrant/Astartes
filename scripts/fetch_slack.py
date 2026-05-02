#!/usr/bin/env python3
"""
Slack Web API fetcher (스레드 또는 채널 메시지).

사용:
  python3 scripts/fetch_slack.py <slack-url> [--out inputs/slack/raw]

환경변수: SLACK_TOKEN (xoxb-* 또는 xoxp-*)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("[fetch_slack] 'requests' 패키지가 필요합니다.", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "inputs" / "slack" / "raw"
API_BASE = "https://slack.com/api"
ARCHIVE_RE = re.compile(r"slack\.com/archives/([A-Z0-9]+)/p(\d+)(?:\?thread_ts=([\d.]+))?")


def parse_url(url: str) -> tuple[str, str | None, str | None]:
    """returns (channel_id, message_ts, thread_ts)"""
    m = ARCHIVE_RE.search(url)
    if not m:
        raise ValueError(f"Slack URL 파싱 실패: {url!r}")
    channel = m.group(1)
    ts_raw = m.group(2)
    thread_ts = m.group(3)
    ts = f"{ts_raw[:-6]}.{ts_raw[-6:]}" if ts_raw else None
    return channel, ts, thread_ts


def call(method: str, token: str, params: dict) -> dict:
    resp = requests.get(
        f"{API_BASE}/{method}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error in {method}: {data.get('error')}")
    return data


def fetch_thread(channel: str, ts: str, token: str) -> list[dict]:
    messages: list[dict] = []
    cursor: str | None = None
    while True:
        params = {"channel": channel, "ts": ts, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = call("conversations.replies", token, params)
        messages.extend(data.get("messages", []))
        meta = data.get("response_metadata") or {}
        cursor = meta.get("next_cursor")
        if not cursor:
            break
    return messages


def normalize(messages: list[dict]) -> list[dict]:
    return [
        {
            "ts": m.get("ts"),
            "user": m.get("user") or m.get("bot_id"),
            "text": m.get("text", ""),
            "thread_ts": m.get("thread_ts"),
        }
        for m in messages
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Slack 메시지/스레드 archive URL")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    token = os.environ.get("SLACK_TOKEN")
    if not token:
        print("[fetch_slack] SLACK_TOKEN 환경변수 필요", file=sys.stderr)
        return 2

    try:
        channel, ts, thread_ts = parse_url(args.source)
    except ValueError as e:
        print(f"[fetch_slack] {e}", file=sys.stderr)
        return 1

    target_ts = thread_ts or ts
    if not target_ts:
        print("[fetch_slack] 메시지 ts 추출 실패", file=sys.stderr)
        return 1

    try:
        messages = fetch_thread(channel, target_ts, token)
    except (requests.HTTPError, RuntimeError) as e:
        print(f"[fetch_slack] API 오류: {e}", file=sys.stderr)
        return 1

    payload = {
        "source_type": "slack",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "input_uri": args.source,
        "channel": channel,
        "thread_ts": target_ts,
        "raw": messages,
        "normalized": normalize(messages),
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(args.source.encode("utf-8")).hexdigest()[:12]
    out_path = out_dir / f"{digest}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fetch_slack] saved {out_path} (messages={len(messages)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
