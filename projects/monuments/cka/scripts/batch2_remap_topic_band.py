#!/usr/bin/env python3
"""Assign batch-2 Topic/Org/Place nodes to dense N-1207+ (never reuse batch-1 ids)."""

from __future__ import annotations

import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
START = 1207

NODE_HEADER = re.compile(r"^\*\*N-(\d+)\*\*\s+(.+)$", re.MULTILINE)
NODE_TYPE = re.compile(r"^Node Type:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
TOPIC_TYPES = frozenset({"topic", "organization", "organisation", "org", "place"})


def _batch1_topic_ids() -> set[int]:
    out: set[int] = set()
    for path in DRAFTS.glob("episode_*.md"):
        m = re.match(r"episode_(\d{3})\.md$", path.name)
        if not m or int(m.group(1)) > 10:
            continue
        for hm in NODE_HEADER.finditer(path.read_text(encoding="utf-8")):
            nid = int(hm.group(1))
            if nid >= 1000:
                out.add(nid)
    return out


def _collect_batch2_topics() -> list[tuple[int, int, int]]:
    """(episode, old_nid, order_in_file) for every topic-class register in ep>=11."""
    rows: list[tuple[int, int, int]] = []
    for path in sorted(DRAFTS.glob("episode_*.md")):
        m = re.match(r"episode_(\d{3})\.md$", path.name)
        if not m or int(m.group(1)) < 11:
            continue
        ep = int(m.group(1))
        text = path.read_text(encoding="utf-8")
        order = 0
        for hm in NODE_HEADER.finditer(text):
            nid = int(hm.group(1))
            start = hm.end()
            nxt = NODE_HEADER.search(text, start)
            block = text[start : nxt.start() if nxt else len(text)]
            tm = NODE_TYPE.search(block)
            ntype = tm.group(1).strip().lower() if tm else ""
            if nid >= 1000 or ntype in TOPIC_TYPES:
                rows.append((ep, nid, order))
                order += 1
    return rows


def main() -> int:
    reserved = _batch1_topic_ids()
    rows = _collect_batch2_topics()
    seen_old: set[int] = set()
    mapping: dict[int, int] = {}
    next_id = START
    for _ep, old, _ord in sorted(rows, key=lambda r: (r[0], r[2], r[1])):
        if old in seen_old:
            continue
        seen_old.add(old)
        if old >= START and old not in reserved:
            continue
        while next_id in reserved or next_id in mapping.values():
            next_id += 1
        if old != next_id:
            mapping[old] = next_id
        next_id += 1
    if not mapping:
        print("Topic band OK")
        return 0
    batch_paths = [
        p
        for p in sorted(DRAFTS.glob("episode_*.md"))
        if re.match(r"episode_\d{3}\.md$", p.name) and int(re.search(r"episode_(\d+)", p.name).group(1)) >= 11
    ]
    for path in batch_paths:
        text = path.read_text(encoding="utf-8")
        orig = text
        for old, new in sorted(mapping.items(), key=lambda kv: kv[0], reverse=True):
            text = re.sub(rf"\bN-{old}\b", f"N-{new}", text)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            print(f"remapped topics in {path.name}")
    print(f"Topic remaps: {len(mapping)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
