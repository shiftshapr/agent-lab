#!/usr/bin/env python3
"""Extend preflight_ledger_baseline for CKA catch-up (person + topic density gates)."""

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
    topic = {int(x) for x in data.get("topic_node_ids") or []}
    for path in DRAFTS.glob("episode_*.md"):
        if not re.match(r"episode_\d{3}\.md$", path.name):
            continue
        ep = int(re.search(r"episode_(\d+)", path.name).group(1))
        if ep < 11:
            continue
        for m in re.finditer(r"\bN-(\d+)\b", path.read_text(encoding="utf-8")):
            nid = int(m.group(1))
            if nid < 1000:
                person.add(nid)
            else:
                topic.add(nid)
    if person:
        hi = max(n for n in person if n < 1000)
        person.update(range(1, hi + 1))
    if topic:
        lo, hi = min(topic), max(topic)
        topic.update(range(lo, hi + 1))
    data["person_node_ids"] = sorted(person)
    data["topic_node_ids"] = sorted(topic)
    data["description"] = (
        "N-ids for CKA dia_preflight band density (Batch 1–2 + catch-up seq 21–156 register scan)."
    )
    CFG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"baseline person={len(data['person_node_ids'])} topic={len(data['topic_node_ids'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
