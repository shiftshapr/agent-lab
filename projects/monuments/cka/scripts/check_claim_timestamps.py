#!/usr/bin/env python3
"""Check that each claim's timestamp lands on the words of its snippet.

A claim's `?t=` link is built from its Claim Timestamp. The snippet's spoken time is estimated from the transcript
markers: exact at a marker, interpolated by character position inside a block (paragraph blocks can run for minutes).
The timestamp may be at most LATE seconds after that time and EARLY seconds before it. Claims whose snippet is not
found verbatim are counted separately (the preflight snippet gate owns that).

Known older drift is listed in config/claim_timestamp_baseline.json; the check fails only on drift not in the
baseline, so new work cannot add any. --write-baseline records the current drift.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/check_claim_timestamps.py [--write-baseline] [--list]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CKA.parent / "bride_of_charlie" / "scripts"))
from neo4j_ingest import extract_claims  # noqa: E402  (the one draft parser, ROADMAP 0.7)
BASELINE = CKA / "config" / "claim_timestamp_baseline.json"
MARK = re.compile(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]")
LATE = 20   # the link may start at most this long after the words are (estimated to be) spoken
EARLY = 75  # ... and at most this long before them


def secs(a: str, b: str, c: str | None) -> int:
    return int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def spoken_at(pos: int, marks: list[tuple[int, int]], rate: float) -> tuple[int, int]:
    """Estimated second at which the text at `pos` is spoken, and the marker time before it.

    Markers give exact times only at block starts; inside a block the time is interpolated by character position
    (blocks can run two minutes or more). After the last marker the transcript's average speaking rate is used."""
    i = max((k for k, (p, _) in enumerate(marks) if p <= pos), default=None)
    if i is None:
        return marks[0][1], marks[0][1]
    p0, t0 = marks[i]
    if i + 1 < len(marks) and marks[i + 1][1] > t0 and marks[i + 1][0] > p0:
        p1, t1 = marks[i + 1]
        return round(t0 + (t1 - t0) * (pos - p0) / (p1 - p0)), t0
    return round(t0 + (pos - p0) / max(rate, 1.0)), t0


def check() -> tuple[list[tuple[str, int, int, int, int]], int, int]:
    """(claim, episode, claim seconds, estimated spoken seconds, block start) for each claim off its words."""
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
        # The episode's end (frontmatter duration) closes the last block, so its times are interpolated too.
        du = re.search(r'^duration:\s*"?([\d:]+)', raw[:800], re.M)
        end = sum(int(x) * k for x, k in zip(reversed(du.group(1).split(":")), (1, 60, 3600))) if du else 0
        if end > marks[-1][1]:
            marks.append((len(text), end))
        span = marks[-1][1] - marks[0][1]
        rate = (marks[-1][0] - marks[0][0]) / span if span > 0 else 15.0  # characters per second
        for c in extract_claims(dp.read_text(encoding="utf-8"), ep):
            ts = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", (c["claim_ts"] or "").strip())
            if not ts or not c["transcript_snippet"]:
                continue
            snippet = norm(c["transcript_snippet"])
            if snippet not in text and ("…" in snippet or "..." in snippet):
                snippet = norm(re.split(r"…|\.\.\.", snippet)[0])
            hits = [i.start() for i in re.finditer(re.escape(snippet), text)] if snippet else []
            if not hits:
                unfound += 1
                continue
            checked += 1
            claim_s = int(ts.group(1)) * 3600 + int(ts.group(2)) * 60 + int(ts.group(3))
            # The same words can occur more than once; judge the occurrence nearest the claim time.
            est, lo = min((spoken_at(h, marks, rate) for h in hits), key=lambda e: abs(e[0] - claim_s))
            if claim_s - est > LATE or est - claim_s > EARLY:
                bad.append((c["id"], ep, claim_s, est, lo))
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
        for c, ep, s, est, lo in bad:
            print(f"{c} ep{ep} at {fmt(s)}; words at ~{fmt(est)} (block {fmt(lo)}){'' if c in known else '  NEW'}")
    print(f"checked {checked} claims ({unfound} snippets not found verbatim); off-block {len(bad)} "
          f"({len(bad) - len(new)} in baseline, {len(new)} new)")
    return 1 if new else 0


if __name__ == "__main__":
    raise SystemExit(main())
