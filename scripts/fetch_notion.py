#!/usr/bin/env python3
"""
Notion API fetcher (페이지 + 블록 자식 재귀).

사용:
  python3 scripts/fetch_notion.py <page-url-or-id> [--out inputs/notion/raw]

환경변수: NOTION_TOKEN
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
    print("[fetch_notion] 'requests' 패키지가 필요합니다.", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "inputs" / "notion" / "raw"
API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
ID_RE = re.compile(r"([0-9a-fA-F]{32})|([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})")


def extract_id(source: str) -> str:
    m = ID_RE.search(source)
    if not m:
        raise ValueError(f"Notion ID를 찾을 수 없음: {source!r}")
    return (m.group(1) or m.group(2)).replace("-", "")


def get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
    }


def fetch_page(page_id: str, token: str) -> dict:
    resp = requests.get(f"{API_BASE}/pages/{page_id}", headers=get_headers(token), timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_blocks(block_id: str, token: str) -> list[dict]:
    blocks: list[dict] = []
    cursor: str | None = None
    while True:
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        resp = requests.get(
            f"{API_BASE}/blocks/{block_id}/children",
            headers=get_headers(token),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        for block in data.get("results", []):
            blocks.append(block)
            if block.get("has_children"):
                block["_children"] = fetch_blocks(block["id"], token)
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return blocks


def plain_text(rich_text: list[dict]) -> str:
    return "".join(rt.get("plain_text", "") for rt in rich_text or [])


def normalize_blocks(blocks: list[dict], parent: str | None = None) -> list[dict]:
    flat: list[dict] = []
    for block in blocks:
        block_type = block.get("type", "unknown")
        body = block.get(block_type, {}) or {}
        text = plain_text(body.get("rich_text", []))
        flat.append({
            "block_id": block.get("id"),
            "type": block_type,
            "plain_text": text,
            "parent": parent,
        })
        children = block.get("_children")
        if children:
            flat.extend(normalize_blocks(children, parent=block.get("id")))
    return flat


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Notion 페이지 URL 또는 ID")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("[fetch_notion] NOTION_TOKEN 환경변수 필요", file=sys.stderr)
        return 2

    try:
        page_id = extract_id(args.source)
    except ValueError as e:
        print(f"[fetch_notion] {e}", file=sys.stderr)
        return 1

    try:
        page = fetch_page(page_id, token)
        blocks = fetch_blocks(page_id, token)
    except requests.HTTPError as e:
        print(f"[fetch_notion] API 오류: {e}", file=sys.stderr)
        return 1

    normalized = {
        "page_id": page_id,
        "blocks": normalize_blocks(blocks),
    }

    payload = {
        "source_type": "notion",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "input_uri": args.source,
        "raw": {"page": page, "blocks": blocks},
        "normalized": normalized,
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(args.source.encode("utf-8")).hexdigest()[:12]
    out_path = out_dir / f"{digest}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fetch_notion] saved {out_path} (blocks={len(normalized['blocks'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
