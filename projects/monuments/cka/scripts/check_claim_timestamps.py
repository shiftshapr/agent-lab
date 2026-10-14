#!/usr/bin/env python3
"""Check that each claim's timestamp lands in the transcript block that contains its snippet.

A claim's `?t=` link is built from its Claim Timestamp. It is right when the timestamp falls between the transcript
marker before the snippet and the marker after it (with SLACK seconds either side, since markers are paragraph
starts). Claims whose snippet is not found verbatim are counted separately (the preflight snippet gate owns that).

Known older drift is listed in config/claim_timestamp_baseline.json; the check fails only on drift not in the
baseline, so new work cannot add any. --write-baseline records the current drift.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/check_claim_timestamps.py [--write-baseline] [--list]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
BASELINE = CKA / "config" / "claim_timestamp_baseline.json"
MARK = re.compile(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]")
BLOCK = re.compile(r"^\*\*(C-\d+)\*\*.*?(?=^\*\*C-|^#{1,3} |\Z)", re.M | re.S)
SLACK = 60


def secs(a: str, b: str, c: str | None) -> int:
    return int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def check() -> tuple[list[tuple[str, int, int, int, int]], int, int]:
    bad, checked, unfound = [], 0, 0
    for dp in sorted((CKA / "drafts").glob("episode_*.md")):
        ep = int(re.search(r"episode_(\d{3})", dp.name).group(1))
        tr = sorted((CKA / "transcripts_corrected").glob(f"episode_{ep:03d}_*"))
        if not tr:
            continue
        raw = tr[0].read_text(encoding="utf-8", errors="ignore")
        # Flatten to one line, keeping marker positions.
        flat = norm(raw)
        # Search text with the markers removed (line-per-marker transcripts put markers inside snippets),
        # remembering where each marker fell in that stripped text.
        marks, text, pos0 = [], "", 0
        for m in [*MARK.finditer(flat), None]:
            chunk = flat[pos0:m.start() if m else len(flat)]
            # Join without doubling the space a removed marker leaves, so recorded positions stay exact.
            text += chunk[1:] if text.endswith(" ") and chunk.startswith(" ") else chunk
            if m:
                marks.append((len(text), secs(*m.groups())))
                pos0 = m.end()
        if not marks:
            continue
        for m in BLOCK.finditer(dp.read_text(encoding="utf-8")):
            blk = m.group(0)
            ts = re.search(r"^Claim Timestamp:\s*(\d{1,2}):(\d{2}):(\d{2})\s*$", blk, re.M)
            sn = re.search(r"^Transcript Snippet:\s*(.+)$", blk, re.M)
            if not ts or not sn:
                continue
            snippet = norm(sn.group(1))
            if snippet not in text and ("…" in snippet or "..." in snippet):
                snippet = norm(re.split(r"…|\.\.\.", snippet)[0])
            hits = [i.start() for i in re.finditer(re.escape(snippet), text)] if snippet else []
            if not hits:
                unfound += 1
                continue
            checked += 1
            claim_s = int(ts.group(1)) * 3600 + int(ts.group(2)) * 60 + int(ts.group(3))

            def block(pos: int) -> tuple[int, int]:
                before = [t for p, t in marks if p <= pos]
                after = [t for p, t in marks if p > pos]
                lo = before[-1] if before else 0
                return lo, (after[0] if after else lo + 600)

            # The same words can occur more than once; judge the occurrence nearest the claim time.
            lo, hi = min((block(h) for h in hits), key=lambda b: 0 if b[0] <= claim_s <= b[1] else min(abs(claim_s - b[0]), abs(claim_s - b[1])))
            if not (lo - SLACK <= claim_s <= hi + SLACK):
                bad.append((m.group(1), ep, claim_s, lo, hi))
    return bad, checked, unfound


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    bad, checked, unfound = check()
    fmt = lambda s: f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"
    if args.write_baseline:
        BASELINE.write_text(json.dumps({"_doc": "Claims whose timestamp falls outside the transcript block of its "
                                        "snippet, recorded when the check was introduced. Fix and remove; never add.",
                                        "claims": sorted(c for c, *_ in bad)}, indent=1) + "\n", encoding="utf-8")
    known = set(json.loads(BASELINE.read_text(encoding="utf-8"))["claims"]) if BASELINE.exists() else set()
    new = [b for b in bad if b[0] not in known]
    if args.list:
        for c, ep, s, lo, hi in bad:
            print(f"{c} ep{ep} at {fmt(s)}; snippet's block {fmt(lo)}-{fmt(hi)}{'' if c in known else '  NEW'}")
    print(f"checked {checked} claims ({unfound} snippets not found verbatim); off-block {len(bad)} "
          f"({len(bad) - len(new)} in baseline, {len(new)} new)")
    return 1 if new else 0


if __name__ == "__main__":
    raise SystemExit(main())
