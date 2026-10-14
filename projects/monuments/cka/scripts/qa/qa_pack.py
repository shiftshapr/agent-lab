#!/usr/bin/env python3
"""Build a QA spot-check pack: a random sample of claims, each with the transcript around its timestamp.

Opus reviewers score each sampled claim (see docs/qa/QA_PROMPT.md); qa_report.py turns their results into qa.md.

  --since REF   sample the claims added since git REF (one batch)
  --all         sample the whole archive (baseline)

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/qa/qa_pack.py OUT_DIR (--since REF | --all) [--rate 0.025] [--seed N] [--chunk 25]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
BLOCK = re.compile(r"^\*\*(C-\d+)\*\*.*?(?=^\*\*C-|^#{1,3} |\Z)", re.M | re.S)
MARK = re.compile(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]")
BEFORE, AFTER = 120, 90


def secs(a: str, b: str, c: str | None) -> int:
    return int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)


def claims_of(text: str) -> dict[str, str]:
    return {m.group(1): m.group(0).strip().rstrip("-").strip() for m in BLOCK.finditer(text)}


def excerpt(transcript: str, at: int) -> str:
    """The transcript from the marker BEFORE seconds ahead of `at` to the marker AFTER seconds past it."""
    marks = [(m.start(), secs(*m.groups())) for m in MARK.finditer(transcript)]
    # Drop out-of-order markers (a chapter list at the top lists later times before the body restarts at 00:00).
    keep, low = [], float("inf")
    for pos, t in reversed(marks):
        if t <= low:
            keep.append((pos, t))
            low = t
    marks = keep[::-1]
    if not marks:
        return "(transcript has no time markers)"
    start = max([p for p, t in marks if t <= at - BEFORE] or [0])
    end = min([p for p, t in marks if t > at + AFTER] or [len(transcript)])
    return re.sub(r"\n{3,}", "\n\n", transcript[start:end]).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--since")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--rate", type=float, default=0.025)
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--chunk", type=int, default=25)
    args = ap.parse_args()

    names = {k: v["canonical_name"] for k, v in
             json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"].items()}
    pool = []
    for dp in sorted((CKA / "drafts").glob("episode_*.md")):
        ep = int(re.search(r"episode_(\d{3})", dp.name).group(1))
        now = claims_of(dp.read_text(encoding="utf-8"))
        if args.since:
            rel = dp.relative_to(CKA.parents[2]).as_posix()
            old = subprocess.run(["git", "show", f"{args.since}:{rel}"], capture_output=True, text=True,
                                 cwd=CKA).stdout
            now = {c: b for c, b in now.items() if c not in claims_of(old)}
        pool += [(ep, c, b) for c, b in now.items()]
    rng = random.Random(args.seed)
    n = max(1, round(len(pool) * args.rate)) if pool else 0
    sample = sorted(rng.sample(pool, n), key=lambda x: (x[0], int(x[1][2:])))

    args.out.mkdir(parents=True, exist_ok=True)
    meta = []
    for i in range(0, len(sample), args.chunk):
        parts = []
        for ep, cid, blk in sample[i:i + args.chunk]:
            tr = sorted((CKA / "transcripts_corrected").glob(f"episode_{ep:03d}_*"))
            ts = re.search(r"^Claim Timestamp:\s*(\d{1,2}):(\d{2}):(\d{2})", blk, re.M)
            at = secs(*ts.groups()) if ts else 0
            ids = sorted(set(re.findall(r"\bN-\d+\b", blk)), key=lambda x: int(x[2:]))
            people = "\n".join(f"- {x}: {names.get(x, '(unknown id)')}" for x in ids) or "- (none)"
            text = excerpt(tr[0].read_text(encoding="utf-8", errors="ignore"), at) if tr else "(no transcript)"
            parts.append(f"## {cid} (episode {ep})\n\n### Claim as recorded\n\n{blk}\n\n### Node ids named\n\n"
                         f"{people}\n\n### Transcript {tr[0].name if tr else ''} around the timestamp\n\n"
                         f"```\n{text}\n```\n")
            meta.append({"claim": cid, "episode": ep, "chunk": i // args.chunk + 1})
        (args.out / f"items_{i // args.chunk + 1:02d}.md").write_text("\n".join(parts), encoding="utf-8")
    (args.out / "sample.json").write_text(json.dumps({"pool": len(pool), "rate": args.rate, "seed": args.seed,
                                                      "since": args.since, "sample": meta}, indent=1) + "\n")
    print(f"pool {len(pool)} claims; sampled {len(sample)} into {(len(sample) + args.chunk - 1) // args.chunk} chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
