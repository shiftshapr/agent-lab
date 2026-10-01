#!/usr/bin/env python3
"""Add minimal Node Register rows for N-* cited but missing from all registers (P1 unknown_node)."""

from __future__ import annotations

import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CANON = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
HEADER = re.compile(r"^\*\*N-(\d+)\*\*", re.MULTILINE)
N_ID = re.compile(r"\bN-(\d+)\b")


def register_ids(text: str) -> set[int]:
    return {int(m.group(1)) for m in HEADER.finditer(text)}


def global_register_ids() -> set[int]:
    out: set[int] = set()
    for p in DRAFTS.glob("episode_*.md"):
        out |= register_ids(p.read_text(encoding="utf-8"))
    return out


def main() -> int:
    known = global_register_ids()
    added = 0
    for path in sorted(DRAFTS.glob("episode_*.md")):
        if not re.match(r"episode_\d{3}\.md$", path.name):
            continue
        text = path.read_text(encoding="utf-8")
        cited = {int(m.group(1)) for m in N_ID.finditer(text)}
        missing = sorted(cited - known)
        if not missing:
            continue
        stub_lines: list[str] = []
        for nid in missing:
            key = f"N-{nid}"
            name = CANON.get(key, {}).get("canonical_name") or f"Node {nid}"
            ntype = CANON.get(key, {}).get("type") or ("person" if nid < 1000 else "topic")
            stub_lines.append(f"**N-{nid}** {name}\n\nNode Type: {ntype}\n\n*Related:*\n")
            known.add(nid)
            added += 1
        if not stub_lines:
            continue
        block = "\n".join(stub_lines) + "\n"
        if "## 4. Node Register" in text:
            text = text.replace("## 4. Node Register\n", "## 4. Node Register\n\n" + block, 1)
        elif "## 5. Claim Register" in text:
            text = text.replace("## 5. Claim Register\n", block + "## 5. Claim Register\n", 1)
        else:
            continue
        path.write_text(text, encoding="utf-8")
    print(f"added register stubs: {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
