#!/usr/bin/env python3
"""Rebuild CKA canonical/nodes.json from all episode drafts (seq 1–20)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"

NODE_HEADER = re.compile(r"^\*\*N-(\d+)\*\*\s+(.+)$", re.MULTILINE)
NODE_TYPE = re.compile(r"^Node Type:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def _json_type(label: str) -> str:
    lab = label.strip().lower()
    if lab in ("person", "investigationtarget"):
        return "person"
    if lab in ("organization", "organisation", "org"):
        return "organization"
    if lab == "place":
        return "place"
    return "topic"


def main() -> int:
    nodes: dict[str, dict] = {}
    for path in sorted(DRAFTS.glob("episode_*.md")):
        m = re.match(r"episode_(\d{3})\.md$", path.name)
        if not m:
            continue
        ep = int(m.group(1))
        if ep == 0:
            continue
        text = path.read_text(encoding="utf-8")
        for hm in NODE_HEADER.finditer(text):
            nid, name = hm.group(1), hm.group(2).strip()
            start = hm.end()
            nxt = NODE_HEADER.search(text, start)
            block = text[start : nxt.start() if nxt else len(text)]
            tm = NODE_TYPE.search(block)
            ntype = _json_type(tm.group(1)) if tm else ("person" if int(nid) < 1000 else "topic")
            ent = nodes.setdefault(
                f"N-{nid}",
                {"canonical_name": name, "type": ntype, "aliases": [], "episodes": []},
            )
            if ep not in ent["episodes"]:
                ent["episodes"].append(ep)
    for ent in nodes.values():
        ent["episodes"] = sorted(ent["episodes"])
    person_max = max(
        (int(k[2:]) for k, v in nodes.items() if v.get("type") == "person"),
        default=175,
    )
    inv_max = max(
        (int(k[2:]) for k, v in nodes.items() if v.get("type") != "person"),
        default=1217,
    )
    out = {
        "version": 1,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "monument": "cka",
        "remap_note": "Batch 1 BoC remap + Batch 2 seq 11–20 extract.",
        "next_person_id": person_max + 1,
        "next_investigation_id": inv_max + 1,
        "nodes": nodes,
    }
    path = CKA / "canonical" / "nodes.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(nodes)} nodes to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
