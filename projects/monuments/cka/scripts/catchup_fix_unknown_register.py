#!/usr/bin/env python3
"""Insert Node Register rows for cited N-* missing monument-wide (catch-up drafts ep>=21)."""

from __future__ import annotations

import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CANON = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
FROM_EP = 21
HEADER = re.compile(r"^\*\*N-(\d+)\*\*", re.MULTILINE)
N_ID = re.compile(r"\bN-(\d+)\b")
REGISTER_HEAD = re.compile(
    r"^(#+\s*(?:IV\.|4\.|)\s*Node Register)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def global_register_ids() -> set[int]:
    out: set[int] = set()
    for p in DRAFTS.glob("episode_*.md"):
        out |= {int(m.group(1)) for m in HEADER.finditer(p.read_text(encoding="utf-8"))}
    return out


def infer_name(nid: int, text: str) -> tuple[str, str]:
    key = f"N-{nid}"
    if key in CANON:
        meta = CANON[key]
        return meta["canonical_name"], meta.get("type") or ("person" if nid < 1000 else "topic")

    pat = re.compile(
        rf"(?ms)(^\*\*C-\d+\*\*[^\n]*\n.*?Related Nodes:.*?\bN-{nid}\b.*?)(?=^\*\*C-|\Z)"
    )
    m = pat.search(text)
    if m:
        block = m.group(1)
        title_m = re.search(r"^\*\*C-\d+\*\*\s*(.+)$", block, re.M)
        if title_m:
            title = title_m.group(1).strip()
            if len(title) > 8:
                return title[:120], "topic" if nid >= 1000 else "person"
        claim_m = re.search(r"^Claim:\s*(.+)$", block, re.M)
        if claim_m:
            snippet = claim_m.group(1).strip()[:100]
            return snippet, "topic" if nid >= 1000 else "person"

    pat_a = re.compile(
        rf"(?ms)(^\*\*A-\d+(?:\.\d+)?\*\*[^\n]*\n.*?)(\*Related:.*?\bN-{nid}\b.*?)(?=^\*\*A-|\Z)"
    )
    m = pat_a.search(text)
    if m:
        title_m = re.search(r"^\*\*A-\d+(?:\.\d+)?\*\*\s*(.+)$", m.group(1), re.M)
        if title_m:
            return title_m.group(1).strip()[:120], "topic" if nid >= 1000 else "person"

    return f"Node {nid}", "topic" if nid >= 1000 else "person"


def insert_register_block(text: str, block: str) -> str | None:
    m = REGISTER_HEAD.search(text)
    if not m:
        return None
    pos = m.end()
    if pos < len(text) and text[pos] == "\n":
        pos += 1
    return text[:pos] + "\n" + block + text[pos:]


def main() -> int:
    known = global_register_ids()
    added = 0
    for path in sorted(DRAFTS.glob("episode_*.md")):
        em = re.match(r"episode_(\d{3})\.md$", path.name)
        if not em or int(em.group(1)) < FROM_EP:
            continue
        text = path.read_text(encoding="utf-8")
        cited = {int(m.group(1)) for m in N_ID.finditer(text)}
        missing = sorted(cited - known)
        if not missing:
            continue
        stubs: list[str] = []
        for nid in missing:
            name, ntype = infer_name(nid, text)
            stubs.append(f"**N-{nid}** {name}\n\nNode Type: {ntype}\n\n*Related:*\n")
            known.add(nid)
            added += 1
        block = "\n".join(stubs) + "\n"
        new_text = insert_register_block(text, block)
        if new_text is None:
            continue
        path.write_text(new_text, encoding="utf-8")
    print(f"register rows added: {added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
