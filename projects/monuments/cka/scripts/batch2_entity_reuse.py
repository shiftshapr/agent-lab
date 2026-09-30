#!/usr/bin/env python3
"""Remap well-known duplicate names in batch-2 drafts to existing CKA N-* ids."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"

NODE_HEADER = re.compile(r"^\*\*N-(\d+)\*\*\s+(.+)$", re.MULTILINE)

# Normalized name -> existing N-* (from CKA seq 1–10 register)
EXPLICIT_REUSE: dict[str, int] = {
    "charlie kirk": 1,
    "erika kirk": 2,
    "candace owens": 7,
    "tyler robinson": 69,
    "phil lyman": 92,
    "tyler bowyer": 85,
    "josh hammer": 42,
    "justin strife": 43,
    "erika kirk (née frantzey)": 2,
}


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _remove_register_block(text: str, nid: int) -> str:
    pat = re.compile(
        rf"^\*\*N-{nid}\*\*[^\n]*\n(?:.*?\n)*?(?=^\*\*N-\d+\*\*|\n## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    return pat.sub("", text, count=1)


def remap_draft(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    replacements: dict[int, int] = {}
    for hm in NODE_HEADER.finditer(text):
        nid = int(hm.group(1))
        name = _norm(hm.group(2))
        existing = EXPLICIT_REUSE.get(name)
        if existing and existing != nid:
            replacements[nid] = existing
    if not replacements:
        return 0
    for old_id in sorted(replacements.keys(), reverse=True):
        text = _remove_register_block(text, old_id)
    for old_id, new_id in sorted(replacements.items(), key=lambda kv: kv[0], reverse=True):
        text = re.sub(rf"\bN-{old_id}\b", f"N-{new_id}", text)
    path.write_text(text, encoding="utf-8")
    return len(replacements)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-ep", type=int, default=11)
    args = ap.parse_args()
    total = 0
    for path in sorted(DRAFTS.glob("episode_*.md")):
        if not re.match(r"episode_\d{3}\.md$", path.name):
            continue
        ep = int(re.search(r"episode_(\d+)", path.name).group(1))
        if ep < args.from_ep:
            continue
        n = remap_draft(path)
        if n:
            print(f"{path.name}: {n} remap(s)")
            total += n
    print(f"Total remaps: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
