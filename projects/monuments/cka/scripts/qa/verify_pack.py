#!/usr/bin/env python3
"""Build the full-archive verification pack (ROADMAP 2.5): every claim, with the transcript around its timestamp.

Each chunk holds CHUNK claims in airing order. Before the first claim of each episode the chunk lists that
episode's person nodes (id and canonical name), so reviewers can correct Mentions. Reviewers follow
docs/qa/VERIFY_PROMPT.md and write results_NNN.json beside the items.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/qa/verify_pack.py OUT_DIR [--chunk 60] [--episodes 1 2 ...] [--claims FILE]

--claims FILE limits the pack to the claim ids listed in FILE (one per line, or a JSON list), for a targeted re-check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_pack  # noqa: E402

qa_pack.BEFORE, qa_pack.AFTER = 60, 90
MAX_CHARS, LEAD = 3500, 1200


def window(transcript: str, at: int) -> str:
    """The transcript around second `at`: marker-bounded (qa_pack.excerpt), but at most MAX_CHARS. Transcripts with
    sparse markers have long blocks; there the position of `at` is interpolated between markers and the window is
    cut around it."""
    ex = qa_pack.excerpt(transcript, at)
    if len(ex) <= MAX_CHARS:
        return ex
    marks = [(m.start(), qa_pack.secs(*m.groups())) for m in qa_pack.MARK.finditer(ex)]
    pos = 0
    for (p0, t0), (p1, t1) in zip(marks, marks[1:]):
        if t0 <= at <= t1 and t1 > t0:
            pos = p0 + (p1 - p0) * (at - t0) // (t1 - t0)
            break
    else:
        if marks and at > marks[-1][1]:
            # Past the last marker: place `at` by the excerpt's average speaking rate (characters per second).
            span = marks[-1][1] - marks[0][1]
            rate = (marks[-1][0] - marks[0][0]) / span if span > 0 else 15.0
            pos = marks[-1][0] + int((at - marks[-1][1]) * max(rate, 5.0))
    start = max(0, pos - LEAD)
    return ("[…] " if start else "") + ex[start:start + MAX_CHARS] + " […]"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--chunk", type=int, default=60)
    ap.add_argument("--episodes", type=int, nargs="*")
    ap.add_argument("--claims", type=Path)
    args = ap.parse_args()
    only = set(re.findall(r"C-\d+", args.claims.read_text(encoding="utf-8"))) if args.claims else None

    nodes = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
    args.out.mkdir(parents=True, exist_ok=True)
    parts, n_chunk, meta, total = [], 0, [], 0

    def flush() -> None:
        nonlocal parts, n_chunk
        if parts:
            n_chunk += 1
            (args.out / f"items_{n_chunk:03d}.md").write_text("\n".join(parts), encoding="utf-8")
            parts = []

    for dp in sorted((CKA / "drafts").glob("episode_*.md")):
        ep = int(re.search(r"episode_(\d{3})", dp.name).group(1))
        if ep == 0 or (args.episodes and ep not in args.episodes):
            continue
        text = dp.read_text(encoding="utf-8")
        tr = sorted((CKA / "transcripts_corrected").glob(f"episode_{ep:03d}_*"))
        transcript = tr[0].read_text(encoding="utf-8", errors="ignore") if tr else ""
        persons = sorted({x for x in re.findall(r"\bN-\d+\b", text) if nodes.get(x, {}).get("type") == "person"},
                         key=lambda x: int(x[2:]))
        roster = "; ".join(f"{x} {nodes[x]['canonical_name']}" for x in persons if x in nodes)
        header = f"# Episode {ep}\n\nPerson nodes in this episode: {roster}\n"
        first = True
        for cid, blk in qa_pack.claims_of(text).items():
            if only is not None and cid not in only:
                continue
            if len(parts) >= args.chunk:
                flush()
                first = True
            ts = re.search(r"^Claim Timestamp:\s*(\d{1,2}):(\d{2}):(\d{2})", blk, re.M)
            at = qa_pack.secs(*ts.groups()) if ts else 0
            ids = sorted(set(re.findall(r"\bN-\d+\b", blk)), key=lambda x: int(x[2:]))
            named = "; ".join(f"{x} {nodes.get(x, {}).get('canonical_name', '(unknown id)')}" for x in ids) or "(none)"
            ex = window(transcript, at) if transcript else "(no transcript)"
            parts.append((header if first else "") + f"\n## {cid} (episode {ep})\n\n{blk}\n\nNode ids named: {named}\n\n"
                         f"Transcript around the timestamp:\n\n```\n{ex}\n```\n")
            first = False
            meta.append({"claim": cid, "episode": ep, "chunk": n_chunk + 1})
            total += 1
    flush()
    (args.out / "sample.json").write_text(json.dumps({"pool": total, "rate": 1.0, "seed": 0, "since": None,
                                                      "sample": meta}, indent=1) + "\n")
    print(f"{total} claims in {n_chunk} chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
