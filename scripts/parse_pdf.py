#!/usr/bin/env python3
"""
PDF 텍스트/테이블 추출.

사용:
  python3 scripts/parse_pdf.py <pdf-path> [--out inputs/pdf/raw]

의존: pdfplumber (또는 fallback: pypdf)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "inputs" / "pdf" / "raw"


def extract_with_pdfplumber(path: Path) -> dict:
    import pdfplumber  # type: ignore

    pages_out: list[dict] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []
            pages_out.append({
                "page_no": page_no,
                "text": text,
                "tables": tables,
            })
    return {"pages": pages_out, "engine": "pdfplumber"}


def extract_with_pypdf(path: Path) -> dict:
    from pypdf import PdfReader  # type: ignore

    reader = PdfReader(str(path))
    pages_out: list[dict] = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages_out.append({"page_no": page_no, "text": text, "tables": []})
    return {"pages": pages_out, "engine": "pypdf"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="PDF 파일 경로")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    pdf_path = Path(args.source).expanduser().resolve()
    if not pdf_path.exists():
        print(f"[parse_pdf] 파일 없음: {pdf_path}", file=sys.stderr)
        return 1

    try:
        normalized = extract_with_pdfplumber(pdf_path)
    except ImportError:
        try:
            normalized = extract_with_pypdf(pdf_path)
        except ImportError:
            print("[parse_pdf] pdfplumber 또는 pypdf 설치 필요. pip install -r scripts/requirements.txt", file=sys.stderr)
            return 2

    payload = {
        "source_type": "pdf",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "input_uri": str(pdf_path),
        "raw": None,
        "normalized": normalized,
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(str(pdf_path).encode("utf-8")).hexdigest()[:12]
    out_path = out_dir / f"{digest}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[parse_pdf] saved {out_path} (pages={len(normalized['pages'])}, engine={normalized['engine']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
