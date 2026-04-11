#!/usr/bin/env python3
"""
Apply JSON from transcript_corrected_quality_review (Copy JSON / Download JSON)
to transcripts_corrected/ episode files.

Uses correctedLineLo / correctedLineHi (1-based inclusive) from each item.
Patches per episode in descending line order so indices stay valid.

Overlapping hunks: if one item's span is fully contained in another's (same episode),
the smaller span is skipped (the wider edit supersedes).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
CORR = PROJECT / "transcripts_corrected"


def _normalize_text(s: str) -> str:
    t = (s or "").strip()
    if t in ("(empty)",):
        return ""
    return t


def _dedupe_subspans(items: list[dict]) -> tuple[list[dict], list[str]]:
    """Drop items whose [lo,hi] is strictly contained in another item on same episode."""
    by_ep: dict[str, list[dict]] = {}
    for it in items:
        by_ep.setdefault(it["episode"], []).append(it)

    kept: list[dict] = []
    skipped: list[str] = []

    for ep, eplist in by_ep.items():
        # Sort by span width descending (wider first), then by lo
        def span_key(x: dict) -> tuple:
            lo, hi = int(x["correctedLineLo"]), int(x["correctedLineHi"])
            w = hi - lo + 1
            return (-w, lo)

        sorted_ep = sorted(eplist, key=span_key)
        accepted: list[tuple[int, int, str]] = []

        for it in sorted_ep:
            lo, hi = int(it["correctedLineLo"]), int(it["correctedLineHi"])
            fid = it.get("findingId", "")
            inner = False
            for alo, ahi, _ in accepted:
                if alo <= lo and hi <= ahi:
                    if (alo, ahi) == (lo, hi):
                        continue
                    inner = True
                    break
            if inner:
                skipped.append(f"{ep} {fid} (lines {lo}-{hi} inside wider hunk)")
                continue
            accepted.append((lo, hi, fid))
            kept.append(it)

    return kept, skipped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "json_path",
        type=Path,
        nargs="?",
        default=PROJECT / "reports" / "apply_quality_payload.json",
    )
    args = ap.parse_args()
    data = json.loads(args.json_path.read_text(encoding="utf-8"))
    items: list[dict] = data["items"]

    items, skipped = _dedupe_subspans(items)
    for msg in skipped:
        print(f"SKIP subset: {msg}", file=sys.stderr)

    by_ep: dict[str, list[dict]] = {}
    for it in items:
        by_ep.setdefault(it["episode"], []).append(it)

    for ep, eplist in by_ep.items():
        eplist.sort(key=lambda x: -int(x["correctedLineLo"]))

    for ep, eplist in by_ep.items():
        path = CORR / f"{ep}.txt"
        if not path.is_file():
            print(f"SKIP missing {path.name}", file=sys.stderr)
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for it in eplist:
            lo1 = int(it["correctedLineLo"])
            hi1 = int(it["correctedLineHi"])
            if lo1 < 1 or hi1 < lo1:
                raise SystemExit(f"{path.name}: bad range {lo1}-{hi1} ({it.get('findingId')})")
            raw_txt = _normalize_text(it.get("implementText") or "")
            new_lines = raw_txt.split("\n")
            a = lo1 - 1
            b = hi1  # exclusive end: line hi1 is index hi1-1, slice end = hi1
            if b > len(lines):
                raise SystemExit(
                    f"{path.name}: lines {lo1}-{hi1} past EOF ({len(lines)}) "
                    f"— {it.get('findingId')}"
                )
            old_n = b - a
            lines[a:b] = new_lines
            print(f"  {it.get('findingId')}: replaced {old_n} line(s) with {len(new_lines)} at {lo1}-{hi1}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Updated {path.name} ({len(eplist)} patch(es))")


if __name__ == "__main__":
    main()
