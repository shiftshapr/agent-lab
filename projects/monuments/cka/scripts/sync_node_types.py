#!/usr/bin/env python3
"""Sync typed-node metadata (ROADMAP 3.1) from canonical/nodes.json into the inscriptions.

For every non-person node object (N-10000+) in inscription/episode_*.json, sets @type and type from the node's
canonical type, and copies schema_org, wikidata_class, event_time, place and parent when present. Idempotent.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/sync_node_types.py
"""

from __future__ import annotations

import json
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
JSONLD = {"event": "Event", "thing": "Thing", "organization": "Organization", "place": "Place",
          "investigation_question": "InvestigationQuestion", "topic": "Topic"}
EXTRA = ("schema_org", "wikidata_class", "event_time", "place", "parent")


def main() -> int:
    nodes = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
    changed = 0
    for p in sorted((CKA / "inscription").glob("episode_*.json")):
        raw = p.read_text(encoding="utf-8")
        d = json.loads(raw)
        dirty = False
        for n in d.get("nodes", []):
            nid = n.get("@id", "")
            if not nid.startswith("N-") or int(nid[2:]) < 10000 or nid not in nodes:
                continue
            c = nodes[nid]
            want = {"@type": JSONLD.get(c.get("type"), "Topic"), "type": c.get("type", "topic")}
            want.update({k: c[k] for k in EXTRA if c.get(k)})
            for k in EXTRA:
                if k not in want and k in n:
                    del n[k]
                    dirty = True
            for k, v in want.items():
                if n.get(k) != v:
                    n[k] = v
                    dirty = True
        if dirty:
            p.write_text(json.dumps(d, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
            changed += 1
    print(f"node types synced into {changed} inscription files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
