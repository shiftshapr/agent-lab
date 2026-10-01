#!/usr/bin/env python3
"""Add Node Register rows in catch-up drafts when claims cite N-* absent from global register."""

from __future__ import annotations

import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CANON = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
FROM_EP = 21
HEADER = re.compile(r"^\*\*N-(\d+)\*\*", re.MULTILINE)


def global_register_ids() -> set[int]:
    out: set[int] = set()
    for p in DRAFTS.glob("episode_*.md"):
        out |= {int(m.group(1)) for m in HEADER.finditer(p.read_text(encoding="utf-8"))}
    return out


def cited_in_claims(text: str) -> set[int]:
    out: set[int] = set()
    for m in re.finditer(r"^\*\*C-\d+\*\*", text, re.M):
        start = m.start()
        block = text[start : start + 1200]
        for nid in re.findall(r"\bN-(\d+)\b", block):
            out.add(int(nid))
    for m in re.finditer(r"^\*Related:.*$", text, re.M):
        for nid in re.findall(r"\bN-(\d+)\b", m.group(0)):
            out.add(int(nid))
    for m in re.finditer(r"^Related Nodes:.*$", text, re.M):
        for nid in re.findall(r"\bN-(\d+)\b", m.group(0)):
            out.add(int(nid))
    return out


def main() -> int:
    known = global_register_ids()
    added = 0
    for path in sorted(DRAFTS.glob("episode_*.md")):
        m = re.match(r"episode_(\d{3})\.md$", path.name)
        if not m or int(m.group(1)) < FROM_EP:
            continue
        text = path.read_text(encoding="utf-8")
        need = sorted(cited_in_claims(text) - known)
        if not need:
            continue
        stubs: list[str] = []
        for nid in need:
            key = f"N-{nid}"
            meta = CANON.get(key)
            if not meta:
                continue
            name = meta["canonical_name"]
            ntype = meta.get("type") or ("person" if nid < 1000 else "topic")
            stubs.append(f"**N-{nid}** {name}\n\nNode Type: {ntype}\n\n*Related:*\n")
            known.add(nid)
            added += 1
        if not stubs:
            continue
        block = "\n".join(stubs) + "\n"
        if "## 4. Node Register" in text:
            text = text.replace("## 4. Node Register\n", "## 4. Node Register\n\n" + block, 1)
            path.write_text(text, encoding="utf-8")
    print(f"added: {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
