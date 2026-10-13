#!/usr/bin/env python3
"""One-time CKA renumber: Topic/Org/Place nodes N-1000..N-9999 -> N-10000+ (offset +9000).

Daveed ruling, 2026-10-13: persons get N-1..N-9999, topic/org/place start at N-10000.
The 34 person tombstones N-10000..N-10033 (PR 47 mints, remapped into low-band holes in PR 50)
are renamed pr47-N-100xx so their ids can be reused by the topic band (Daveed: reuse them).

Rewrites N-xxxx tokens in drafts, inscription, canonical, config, companion, audits, docs and
README. Leaves transcripts, transcript SHAs, vendor and the historical one-shot scripts alone.
BoC-era keys such as pr33-person-N-1067 refer to BoC ids and are not touched.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/renumber_topic_band_10000.py [--dry-run]
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
OFFSET = 9000
OLD_MIN = 1000
# Highest real topic id (next_investigation_id - 1). Larger 4-digit ids only occur in band prose
# ("N-1000..N-9999") and are reported, not mapped.
OLD_MAX = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["next_investigation_id"] - 1
PR47_MIN, PR47_MAX = 10000, 10033

INCLUDE_DIRS = ["drafts", "inscription", "canonical", "config", "companion", "audits", "docs"]
INCLUDE_FILES = [CKA / "README.md", MONUMENTS / "scripts" / "hostile_hard_gates.py"]
TEXT_SUFFIXES = {".md", ".json", ".csv", ".txt", ".py", ".jsonl"}
OUT_DIR = CKA / "audits" / "renumber_10000"

# Optional legacy-/wave1- prefix; any other "-" prefix (pr33-person-N-…) is history from another
# ledger and is skipped. The id must not be glued to a letter, digit or hyphen on the left.
TOKEN_RE = re.compile(r"(?<![0-9A-Za-z\-])((?:legacy-|wave1-)?)N-(\d+)(?!\d)")


def files() -> list[Path]:
    out: list[Path] = []
    for d in INCLUDE_DIRS:
        for p in sorted((CKA / d).rglob("*")):
            if p.is_file() and p.suffix in TEXT_SUFFIXES and ".transcript_sha" not in p.parts and p.parent != OUT_DIR:
                out.append(p)
    out += [p for p in INCLUDE_FILES if p.is_file()]
    return out


def rewrite(text: str, unmapped: dict[str, int]) -> tuple[str, int]:
    count = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal count
        prefix, num = m.group(1), int(m.group(2))
        if PR47_MIN <= num <= PR47_MAX:
            count += 1
            return f"pr47-N-{num}"
        if OLD_MIN <= num <= OLD_MAX:
            count += 1
            return f"{prefix}N-{num + OFFSET}"
        if OLD_MAX < num < PR47_MIN:
            unmapped[f"N-{num}"] = unmapped.get(f"N-{num}", 0) + 1
        return m.group(0)

    return TOKEN_RE.sub(sub, text), count


def rewrite_int_fields(path: Path, text: str) -> tuple[str, int]:
    """Bare-integer node ids: next_investigation_id and the topic density baseline."""
    n = 0
    if path.name == "nodes.json" and path.parent.name == "canonical":
        def nid(m: re.Match[str]) -> str:
            nonlocal n
            n += 1
            return f'{m.group(1)}{int(m.group(2)) + OFFSET}'
        text = re.sub(r'("next_investigation_id":\s*)(\d+)', nid, text)
    if path.name == "preflight_ledger_baseline.json":
        m = re.search(r'("topic_node_ids":\s*\[)([^\]]*)(\])', text)
        if m:
            def bump(t: re.Match[str]) -> str:
                nonlocal n
                v = int(t.group(0))
                if OLD_MIN <= v <= OLD_MAX:
                    n += 1
                    return str(v + OFFSET)
                return t.group(0)
            body = re.sub(r"\d+", bump, m.group(2))
            text = text[: m.start(2)] + body + text[m.end(2):]
    return text, n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if OLD_MAX >= PR47_MIN:
        print("refuse: next_investigation_id is already in the N-10000+ band; the renumber has been applied", file=sys.stderr)
        return 2
    nodes = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
    retired = json.loads((CKA / "config" / "retired_node_ids.json").read_text(encoding="utf-8"))["retired"]

    changed: list[tuple[str, int]] = []
    unmapped: dict[str, int] = {}
    for p in files():
        text = p.read_text(encoding="utf-8")
        new, n = rewrite(text, unmapped)
        new, k = rewrite_int_fields(p, new)
        if new != text:
            changed.append((str(p.relative_to(MONUMENTS)), n + k))
            if not args.dry_run:
                p.write_text(new, encoding="utf-8")

    rows = []
    for key, meta in nodes.items():
        m = re.match(r"N-(\d+)$", key)
        if m and OLD_MIN <= int(m.group(1)) <= OLD_MAX:
            rows.append((key, f"N-{int(m.group(1)) + OFFSET}", meta.get("canonical_name", ""), meta.get("type", ""), "active"))
    for key, meta in retired.items():
        m = re.match(r"(legacy|wave1)-N-(\d+)$", key)
        if not m:
            continue
        num = int(m.group(2))
        if OLD_MIN <= num <= OLD_MAX:
            rows.append((key, f"{m.group(1)}-N-{num + OFFSET}", meta.get("canonical_name", ""), "", "tombstone"))
        elif PR47_MIN <= num <= PR47_MAX:
            rows.append((key, f"pr47-N-{num}", meta.get("canonical_name", ""), "person", "tombstone renamed (id freed for topic band)"))
    rows.sort(key=lambda r: int(re.search(r"(\d+)$", r[0]).group(1)))

    print(f"files changed: {len(changed)}; tokens rewritten: {sum(n for _, n in changed)}; map rows: {len(rows)}")
    if unmapped:
        print("ids outside the mapped ranges (left as is; check for band prose):")
        for k, v in sorted(unmapped.items(), key=lambda kv: int(kv[0][2:])):
            print(f"  {k}: {v}")
    if args.dry_run:
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "renumber_map.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["old_id", "new_id", "name", "type", "status"])
        w.writerows(rows)
    with (OUT_DIR / "changed_files.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "tokens_rewritten"])
        w.writerows(changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
