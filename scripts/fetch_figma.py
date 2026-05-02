#!/usr/bin/env python3
"""
Figma REST API fetcher.

사용:
  python3 scripts/fetch_figma.py <figma-url-or-key> [--out inputs/figma/raw]

환경변수: FIGMA_TOKEN
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
    print("[fetch_figma] 'requests' 패키지가 필요합니다. pip install -r scripts/requirements.txt", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "inputs" / "figma" / "raw"
FIGMA_URL_RE = re.compile(r"figma\.com/(?:file|design)/([A-Za-z0-9]+)")


def extract_file_key(arg: str) -> str:
    m = FIGMA_URL_RE.search(arg)
    return m.group(1) if m else arg.strip()


def fetch_file(file_key: str, token: str) -> dict:
    url = f"https://api.figma.com/v1/files/{file_key}"
    resp = requests.get(url, headers={"X-Figma-Token": token}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def normalize(raw: dict) -> dict:
    frames: list[dict] = []

    def walk(node: dict, parent_frame: str | None = None):
        node_type = node.get("type")
        name = node.get("name", "")
        if node_type in ("FRAME", "COMPONENT", "SECTION"):
            text_layers: list[str] = []
            collect_text(node, text_layers)
            frames.append({
                "id": node.get("id"),
                "name": name,
                "type": node_type,
                "absolute_bbox": node.get("absoluteBoundingBox"),
                "text_layers": text_layers,
            })
            parent_frame = name
        for child in node.get("children", []) or []:
            walk(child, parent_frame)

    def collect_text(node: dict, sink: list[str]):
        if node.get("type") == "TEXT":
            chars = node.get("characters")
            if chars:
                sink.append(chars)
        for child in node.get("children", []) or []:
            collect_text(child, sink)

    document = raw.get("document", {})
    walk(document)
    return {
        "name": raw.get("name"),
        "last_modified": raw.get("lastModified"),
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Figma file URL 또는 file key")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    token = os.environ.get("FIGMA_TOKEN")
    if not token:
        print("[fetch_figma] FIGMA_TOKEN 환경변수 필요", file=sys.stderr)
        return 2

    file_key = extract_file_key(args.source)
    try:
        raw = fetch_file(file_key, token)
    except requests.HTTPError as e:
        print(f"[fetch_figma] API 오류: {e}", file=sys.stderr)
        return 1

    normalized = normalize(raw)
    payload = {
        "source_type": "figma",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "input_uri": args.source,
        "file_key": file_key,
        "raw": raw,
        "normalized": normalized,
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(args.source.encode("utf-8")).hexdigest()[:12]
    out_path = out_dir / f"{digest}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fetch_figma] saved {out_path} (frames={len(normalized['frames'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
