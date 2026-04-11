#!/usr/bin/env python3
"""
Heuristic scan of inscription/*.json for org nodes, institution usage, and
relationship-relevant language in claims (episodes 1–7 by default).

Usage:
  cd projects/monuments/bride_of_charlie
  python3 scripts/scan_episode_relationship_patterns.py
  python3 scripts/scan_episode_relationship_patterns.py --episodes 1-3
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent

REL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("kinship", re.compile(
        r"\b(mother|father|parent|son|daughter|child|husband|wife|spouse|ex-?husband|ex-?wife|"
        r"divorc|married to|sibling|brother|sister|uncle|aunt|cousin|stepmother|stepfather|"
        r"in-?law|grandmother|grandfather|mormor|farfar|farmor|morfar)\b",
        re.I,
    )),
    ("work_org", re.compile(
        r"\b(CEO|CFO|president|chair|board|employ|worked at|works for|founded|co-?founder|"
        r"owner|LLC|Inc\.|corporation|non-?profit|501\(|charity|foundation)\b",
        re.I,
    )),
    ("legal_gov", re.compile(
        r"\b(CIA|FBI|agency|department|government|military|police|court|judge|filing|lawsuit|subpoena)\b",
        re.I,
    )),
    ("financial_record", re.compile(
        r"\b(registered|domain|trademark|patent|contract|loan|mortgage|bank|wire|payment|\$[\d,]+|million|billion)\b",
        re.I,
    )),
    ("attribution", re.compile(
        r"\b(alleged|claimed|stated|testified|denied|recall|remember|according to)\b",
        re.I,
    )),
    ("temporal", re.compile(
        r"\b(before|after|on \w+ \d{1,2}|in \d{4}|timeline|same day|overlap)\b",
        re.I,
    )),
    ("education", re.compile(
        r"\b(attended|enrolled|graduated|alumni|student|teacher|principal|school)\b",
        re.I,
    )),
    ("travel_citizenship", re.compile(
        r"\b(visited|traveled|flight|passport|citizenship|visa|country|abroad)\b",
        re.I,
    )),
]


def parse_episodes(spec: str | None) -> list[int] | None:
    if not spec or not spec.strip():
        return list(range(1, 8))
    out: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            if a.strip().isdigit() and b.strip().isdigit():
                lo, hi = int(a.strip()), int(b.strip())
                out.update(range(min(lo, hi), max(lo, hi) + 1))
        elif chunk.isdigit():
            out.add(int(chunk))
    return sorted(out) if out else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan inscription JSON for relationship heuristics")
    ap.add_argument("--episodes", type=str, default="1-7", metavar="SPEC", help="e.g. 1-7 or 1,2,3")
    args = ap.parse_args()
    eps = parse_episodes(args.episodes)
    if not eps:
        print("No episodes parsed", file=sys.stderr)
        return 1

    org_nodes: list[tuple[int, str, str]] = []
    place_nodes: list[tuple[int, str, str]] = []
    topic_nodes: list[tuple[int, str, str]] = []
    rel_counts: dict[str, int] = {k: 0 for k, _ in REL_PATTERNS}

    for ep in eps:
        p = PROJECT_DIR / "inscription" / f"episode_{ep:03d}.json"
        if not p.is_file():
            print(f"[skip] missing {p.name}")
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for n in data.get("nodes") or []:
            if not isinstance(n, dict):
                continue
            name = str(n.get("name") or "")
            t = str(n.get("type") or "").lower()
            at = str(n.get("@type") or "")
            desc = str(n.get("description") or "")[:120]
            if t in ("institution", "organization") or at == "Organization":
                org_nodes.append((ep, name, desc))
            elif t == "place" or at == "Place":
                place_nodes.append((ep, name, desc))
            elif t in ("investigation_target", "topic") or at in ("InvestigationTarget", "Topic"):
                topic_nodes.append((ep, name, desc))
        for c in data.get("claims") or []:
            if not isinstance(c, dict):
                continue
            blob = " ".join(
                str(c.get(k) or "")
                for k in ("claim", "label", "transcript_snippet", "investigative_direction")
            )
            for key, rx in REL_PATTERNS:
                if rx.search(blob):
                    rel_counts[key] += 1

    print("=== Organization / institution nodes ===")
    for row in org_nodes:
        print(f"  ep{row[0]:03d}  {row[1]}  — {row[2]}")
    print(f"  total: {len(org_nodes)}")

    print("\n=== Place nodes ===")
    for row in place_nodes:
        print(f"  ep{row[0]:03d}  {row[1]}  — {row[2]}")
    print(f"  total: {len(place_nodes)}")

    print("\n=== Topic / thematic nodes (legacy InvestigationTarget) ===")
    from collections import Counter

    c = Counter(ep for ep, _, _ in topic_nodes)
    for ep in eps:
        print(f"  ep{ep:03d}: {c.get(ep, 0)}")
    print(f"  total: {len(topic_nodes)}")

    print("\n=== Claim text pattern hits (a claim counts once per category if any field matches) ===")
    for k, _ in sorted(REL_PATTERNS, key=lambda x: -rel_counts[x[0]]):
        print(f"  {k}: {rel_counts[k]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
