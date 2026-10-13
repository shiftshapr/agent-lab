#!/usr/bin/env python3
"""One-time CKA node id compaction (Daveed, 2026-10-13). Runs once, on the pre-2026-10-13 tree.

- No tombstones: config/retired_node_ids.json, config/person_band_snapshot.json, the person_band_lock gate
  config and every node's retired_ids are deleted. A merged or retired id is simply not a node.
- Persons get N-1..N-9999 and topic/org/place get N-10000+ (node_bands in config/preflight_gates.json).
- Ids are compacted with no holes: active persons -> N-1..N-<p>, active topic/org/place -> N-10000..,
  each band keeping its current id order (a monotone map, so every intro/hole/tip order relation holds).
- Rewrites N-ids in drafts, inscription, canonical, config, companion and scripts/hostile_hard_gates.py.
  Ids that are no longer nodes are dropped from the episode_000 baseline ledger line; anywhere else they
  are reported. Audits are not rewritten: they keep the ids of their time, translated by
  audits/id_compaction_2026-10-13/id_map.csv. Transcripts are not touched.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/compact_node_ids.py [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
MONUMENTS = CKA.parent
OUT_DIR = CKA / "audits" / "id_compaction_2026-10-13"
INCLUDE_DIRS = ["drafts", "inscription", "canonical", "config", "companion"]
INCLUDE_FILES = [MONUMENTS / "scripts" / "hostile_hard_gates.py"]
TEXT_SUFFIXES = {".md", ".json", ".csv", ".txt", ".jsonl", ".py"}
TOPIC_MIN = 10000
TOKEN_RE = re.compile(r"(?<![0-9A-Za-z\-])N-(\d+)(?!\d)")
BASELINE_LINE_RE = re.compile(r"^(\s*- New Nodes Introduced:)(.*)$", re.MULTILINE)

NODE_BANDS = {
    "person_max": 9999,
    "topic_min": TOPIC_MIN,
    "topic_max": None,
    "person_high_min": None,
    "note": (
        "Daveed, 2026-10-13: persons are N-1..N-9999 and topic/org/place nodes are N-10000+. Ids were compacted "
        "with no holes (audits/id_compaction_2026-10-13/id_map.csv). New persons continue from canonical "
        "next_person_id, new topic/org/place nodes from next_investigation_id. No tombstones: a merged or "
        "retired id is not reserved."
    ),
}


def files() -> list[Path]:
    out = []
    for d in INCLUDE_DIRS:
        for p in sorted((CKA / d).rglob("*")):
            if p.is_file() and p.suffix in TEXT_SUFFIXES and ".transcript_sha" not in p.parts:
                out.append(p)
    return out + [p for p in INCLUDE_FILES if p.is_file()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    npath = CKA / "canonical" / "nodes.json"
    ndata = json.loads(npath.read_text(encoding="utf-8"))
    if ndata.get("next_investigation_id", 0) >= TOPIC_MIN:
        print("refuse: next_investigation_id is already in the N-10000+ band; compaction has been applied", file=sys.stderr)
        return 2
    nodes = ndata["nodes"]
    ids = sorted(int(k[2:]) for k in nodes)
    persons = [i for i in ids if i < 1000]
    topics = [i for i in ids if i >= 1000]
    idmap = {old: new for new, old in enumerate(persons, 1)}
    idmap.update({old: TOPIC_MIN + k for k, old in enumerate(topics)})

    dropped: list[tuple[str, str]] = []
    unmapped: dict[str, set[str]] = {}

    def rewrite(path: Path, text: str) -> str:
        if path.name == "episode_000.md":
            def baseline(m: re.Match[str]) -> str:
                kept = []
                for tok in [t.strip() for t in m.group(2).split(",") if t.strip()]:
                    tm = re.fullmatch(r"N-(\d+)", tok)
                    if tm and int(tm.group(1)) not in idmap:
                        dropped.append((str(path.relative_to(CKA)), tok))
                        continue
                    kept.append(tok)
                return f"{m.group(1)} {', '.join(kept)}" if kept else m.group(1)
            text = BASELINE_LINE_RE.sub(baseline, text)

        def sub(m: re.Match[str]) -> str:
            old = int(m.group(1))
            if old in idmap:
                return f"N-{idmap[old]}"
            unmapped.setdefault(f"N-{old}", set()).add(str(path.relative_to(MONUMENTS)))
            return m.group(0)

        return TOKEN_RE.sub(sub, text)

    changed = []
    for p in files():
        if p.name in ("retired_node_ids.json", "person_band_snapshot.json"):
            continue
        text = p.read_bytes().decode("utf-8")  # keep CRLF files as CRLF
        new = text
        if p == npath:
            new = re.sub(r",\s*\n\s*\"retired_ids\":\s*\[[^\]]*\](?=\s*\n\s*\})", "", new)
            new = re.sub(r"\n\s*\"retired_ids\":\s*\[[^\]]*\],", "", new)
            new = re.sub(r'("remap_note":\s*)"(?:[^"\\]|\\.)*"', r'\1""', new)
        new = rewrite(p, new)
        if p == npath:
            new = re.sub(r'("next_person_id":\s*)(null|\d+)', rf"\g<1>{len(persons) + 1}", new)
            new = re.sub(r'("next_investigation_id":\s*)\d+', rf"\g<1>{TOPIC_MIN + len(topics)}", new)
            note = (
                "2026-10-13 (Daveed): ids compacted with no holes and no tombstones. Persons N-1..N-"
                f"{len(persons)}, topic/org/place N-{TOPIC_MIN}..N-{TOPIC_MIN + len(topics) - 1}; old to new ids in "
                "audits/id_compaction_2026-10-13/id_map.csv. Earlier remap history (BoC remap, batches 1-2, "
                "catch-up, waves 1-3) is in git history and the audits folders, which keep the ids of their time."
            )
            new = re.sub(r'("remap_note":\s*)"(?:[^"\\]|\\.)*"', lambda m: m.group(1) + json.dumps(note), new)
            json.loads(new)
        if p.name == "preflight_ledger_baseline.json":
            data = json.loads(text)
            data["person_node_ids"] = [idmap[i] for i in data.get("person_node_ids") or [] if i in idmap]
            data["topic_node_ids"] = [idmap[i] for i in data.get("topic_node_ids") or [] if i in idmap]
            new = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if p.name == "preflight_gates.json" and p.parent.name == "config":
            data = json.loads(new)
            data.pop("person_band_lock", None)
            data["node_bands"] = NODE_BANDS
            new = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if new != text:
            changed.append(str(p.relative_to(MONUMENTS)))
            if not args.dry_run:
                p.write_bytes(new.encode("utf-8"))

    print(f"persons {len(persons)} -> N-1..N-{len(persons)}; topic/org/place {len(topics)} -> N-{TOPIC_MIN}..N-{TOPIC_MIN + len(topics) - 1}")
    print(f"files changed: {len(changed)}; dead ids dropped from baseline ledger: {len(dropped)}")
    for k, v in sorted(unmapped.items(), key=lambda kv: int(kv[0][2:])):
        print(f"  not a node, left as is: {k} in {', '.join(sorted(v))}")
    if args.dry_run:
        return 0

    for name in ("retired_node_ids.json", "person_band_snapshot.json"):
        (CKA / "config" / name).unlink(missing_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "id_map.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["old_id", "new_id", "name", "type"])
        for old in ids:
            meta = nodes[f"N-{old}"]
            w.writerow([f"N-{old}", f"N-{idmap[old]}", meta.get("canonical_name", ""), meta.get("type", "")])
    with (OUT_DIR / "baseline_ids_dropped.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "old_id"])
        w.writerows(dropped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
