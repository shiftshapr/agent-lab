#!/usr/bin/env python3
"""Reassign mistaken N-1 / N-2 / N-7 register rows in catch-up drafts (keep core ids sacred)."""

from __future__ import annotations

import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
FROM_EP = 21
CORE: dict[int, str] = {1: "charlie kirk", 2: "erika kirk", 7: "candace owens"}
HEADER = re.compile(r"^\*\*N-(\d+)\*\*\s+(.+)$", re.MULTILINE)


def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _max_person_id() -> int:
    mx = 285
    for path in DRAFTS.glob("episode_*.md"):
        for m in re.finditer(r"\bN-(\d+)\b", path.read_text(encoding="utf-8")):
            n = int(m.group(1))
            if n < 1000:
                mx = max(mx, n)
    return mx


def main() -> int:
    next_id = _max_person_id() + 1
    total = 0
    for path in sorted(DRAFTS.glob("episode_*.md")):
        m = re.match(r"episode_(\d{3})\.md$", path.name)
        if not m or int(m.group(1)) < FROM_EP:
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        for hm in HEADER.finditer(text):
            nid = int(hm.group(1))
            if nid not in CORE:
                continue
            name = _norm(hm.group(2))
            if name == CORE[nid]:
                continue
            new_id = next_id
            next_id += 1
            old = f"N-{nid}"
            new = f"N-{new_id}"
            text = re.sub(rf"\*\*{old}\*\*", f"**{new}**", text)
            text = re.sub(rf"\b{re.escape(old)}\b", new, text)
            total += 1
            print(f"{path.name}: {old} ({hm.group(2).strip()}) -> {new}")
        if text != orig:
            path.write_text(text, encoding="utf-8")
    print(f"collisions fixed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
