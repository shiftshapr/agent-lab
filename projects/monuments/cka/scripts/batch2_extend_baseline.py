#!/usr/bin/env python3
"""Extend preflight_ledger_baseline person_node_ids with batch-2 register ids (density gate)."""

from __future__ import annotations

import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
CFG = CKA / "config" / "preflight_ledger_baseline.json"
DRAFTS = CKA / "drafts"


def main() -> int:
    data = json.loads(CFG.read_text(encoding="utf-8"))
    person = {int(x) for x in data.get("person_node_ids") or []}
    for path in DRAFTS.glob("episode_*.md"):
        if not re.match(r"episode_\d{3}\.md$", path.name):
            continue
        ep = int(re.search(r"episode_(\d+)", path.name).group(1))
        if ep < 11:
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\bN-(\d+)\b", text):
            nid = int(m.group(1))
            if nid < 1000:
                person.add(nid)
    if person:
        hi = max(n for n in person if n < 1000)
        person.update(range(1, hi + 1))
    data["person_node_ids"] = sorted(person)
    data["description"] = (
        "N-ids for CKA dia_preflight band density (BoC eps 1–8 baseline + batch-2 person register)."
    )
    CFG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"baseline person ids: {len(data['person_node_ids'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
