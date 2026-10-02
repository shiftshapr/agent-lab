#!/usr/bin/env python3
"""Scrub American Financing / promo ad blocks from CKA catch-up transcripts (seq 21–156)."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
CORR = CKA / "transcripts_corrected"
INS = CKA / "inscription"


def _load_strip():
    spec = importlib.util.spec_from_file_location(
        "hostile_fix_batch1", CKA / "scripts" / "hostile_fix_batch1.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod._strip_ads_text


def scrub_episode(ep: int, strip_fn) -> int:
    removed = 0
    for path in sorted(CORR.glob(f"episode_{ep:03d}_*")):
        if path.suffix not in (".md", ".txt"):
            continue
        raw = path.read_text(encoding="utf-8")
        if path.suffix == ".md" and raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
                new_body, n = strip_fn(body)
                removed += n
                updated = f"---{parts[1]}---{new_body}"
                if not updated.endswith("\n"):
                    updated += "\n"
            else:
                updated, n = strip_fn(raw)
                removed += n
        else:
            updated, n = strip_fn(raw)
            removed += n
        if updated != raw:
            path.write_text(updated, encoding="utf-8")
    ins_path = INS / f"episode_{ep:03d}_transcript.txt"
    if ins_path.is_file():
        raw = ins_path.read_text(encoding="utf-8")
        updated, n = strip_fn(raw)
        removed += n
        if updated != raw:
            ins_path.write_text(updated, encoding="utf-8")
    return removed


def main() -> int:
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 21
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else 156
    strip_fn = _load_strip()
    total = 0
    for ep in range(lo, hi + 1):
        total += scrub_episode(ep, strip_fn)
    print(f"Scrubbed seq {lo}–{hi}: ~{total} ad lines removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
