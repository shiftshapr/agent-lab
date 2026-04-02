#!/usr/bin/env python3
"""
Extract text from PDF to knowledge base.

Usage:
  python scripts/ingest-pdf.py path/to/file.pdf
  python scripts/ingest-pdf.py path/to/file.pdf --output knowledge/custom_name.md

Output: knowledge/docs/filename.md (or custom path)
Add to shiftshapr_context.json knowledge_sources: ["docs/filename.md"]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = AGENT_LAB_ROOT / "knowledge"
DOCS_DIR = KNOWLEDGE_DIR / "docs"


def extract_pdf(path: Path) -> str:
    """Extract text from PDF. Tries pymupdf, then pypdf."""
    try:
        import pymupdf
        doc = pymupdf.open(path)
        text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n\n".join(p.extract_text() or "" for p in reader.pages).strip()
    except ImportError:
        print("Install pymupdf or pypdf: uv add pymupdf", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract PDF to knowledge base")
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    parser.add_argument("--output", "-o", type=Path, help="Output path (default: knowledge/docs/filename.md)")
    args = parser.parse_args()

    path = args.pdf.resolve()
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    text = extract_pdf(path)
    if not text:
        print("No text extracted.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out = Path(args.output)
        if not out.is_absolute():
            out = AGENT_LAB_ROOT / out
    else:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        out = DOCS_DIR / f"{path.stem}.md"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"# {path.stem}\n\n{text}", encoding="utf-8")
    rel = out.relative_to(KNOWLEDGE_DIR)
    print(f"Wrote {out} ({len(text)} chars)")
    print(f"Add to knowledge_sources: \"{rel}\"")


if __name__ == "__main__":
    main()
