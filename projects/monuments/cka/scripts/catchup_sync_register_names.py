#!/usr/bin/env python3
"""Align draft register headers with canonical/nodes.json names (fix remap_sync)."""

from __future__ import annotations

import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CANON = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
HEADER = re.compile(r"^(\*\*N-(\d+)\*\*)\s+(.+)$", re.MULTILINE)


def main() -> int:
    fixed = 0
    for path in sorted(DRAFTS.glob("episode_*.md")):
        if not re.match(r"episode_\d{3}\.md$", path.name):
            continue
        text = path.read_text(encoding="utf-8")
        orig = text

        def repl(m: re.Match[str]) -> str:
            nonlocal fixed
            nid = int(m.group(2))
            key = f"N-{nid}"
            ent = CANON.get(key)
            if not ent:
                return m.group(0)
            canon = ent["canonical_name"].strip()
            if m.group(3).strip() == canon:
                return m.group(0)
            fixed += 1
            return f"{m.group(1)} {canon}"

        text = HEADER.sub(repl, text)
        if text != orig:
            path.write_text(text, encoding="utf-8")
    print(f"register headers aligned: {fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
