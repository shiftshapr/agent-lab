#!/usr/bin/env python3
"""Pre- and post-integration checks for a supplement batch.

  --pre:   every expected episode has a staging file (no agent still running), and every staged new node or meme
           is checked against canonical/ for exact and near-duplicate names (prints a merge-map suggestion list).
  --post:  for every staged episode, the claims, artifact sub-items and meme occurrences added to the draft
           (versus REF, default HEAD) equal what was staged. Any mismatch exits 1.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/supplement/verify_batch.py STAGING_DIR --pre --expect BATCH_JSON
  python3 projects/monuments/cka/scripts/supplement/verify_batch.py STAGING_DIR --post [--ref HEAD]
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CKA / "scripts"))
import supplement_integrate as si  # noqa: E402


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.M))


def staged_counts(text: str) -> tuple[int, int, int]:
    return (count(text, r"^\*\*C-L\d+\*\*"), count(text, r"^\*\*A-L\d+\.\d+\*\*"),
            count(si.section(text, "meme"), r"^### Occurrence"))


def draft_counts(text: str) -> tuple[int, int, int]:
    return (count(text, r"^\*\*C-\d+\*\*"), count(text, r"^\*\*A-\d+\.\d+\*\*"), count(text, r"^### Occurrence"))


def pre(staging: Path, expect: Path) -> int:
    want = {e for e, _ in json.loads(expect.read_text(encoding="utf-8"))}
    have = {int(re.search(r"episode_(\d{3})", p.name).group(1)) for p in staging.glob("episode_*.md")}
    missing = sorted(want - have)
    if missing:
        print("NOT READY, staging files missing for:", missing)
        return 1
    nodes = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
    names = {}
    for k, v in nodes.items():
        for n in [v["canonical_name"], *v.get("aliases", [])]:
            names[si.norm(n)] = (k, v["canonical_name"])
    terms = {si.norm(re.sub(r"^\(meme\)\s*", "", v["canonical_term"])): k
             for k, v in json.loads((CKA / "canonical" / "memes.json").read_text(encoding="utf-8"))["entries"].items()}
    seen: dict[str, int] = {}
    for p in sorted(staging.glob("episode_*.md")):
        ep = int(re.search(r"episode_(\d{3})", p.name).group(1))
        text = p.read_text(encoding="utf-8")
        for nid, title in re.findall(r"^\*\*(N-[PT]\d+)\*\*\s+(.+)$", text, re.M):
            key = si.norm(title)
            if key in names:
                print(f"ep{ep} {nid} {title!r}: exact match {names[key]} (reused automatically)")
                continue
            near = difflib.get_close_matches(key, list(names), n=2, cutoff=0.8)
            if near or key in seen:
                print(f"ep{ep} {nid} {title!r}: near {[names[x] for x in near]} batch-dup ep{seen.get(key)}")
            seen.setdefault(key, ep)
        for mid, term in re.findall(r"^\*\*(M-N\d+)\*\*\s+(.+)$", text, re.M):
            key = si.norm(re.sub(r"^\(meme\)\s*", "", term))
            near = difflib.get_close_matches(key, list(terms), n=1, cutoff=0.8)
            if near and key not in terms:
                print(f"ep{ep} {mid} {term!r}: near meme {terms[near[0]]}")
    print(f"ready: {len(have)} staging files")
    return 0


def post(staging: Path, ref: str) -> int:
    bad, total = 0, [0, 0, 0]
    for p in sorted(staging.glob("episode_*.md")):
        ep = int(re.search(r"episode_(\d{3})", p.name).group(1))
        rel = f"projects/monuments/cka/drafts/episode_{ep:03d}.md"
        before = subprocess.run(["git", "show", f"{ref}:{rel}"], capture_output=True, text=True).stdout
        after = (CKA / "drafts" / f"episode_{ep:03d}.md").read_text(encoding="utf-8")
        staged = staged_counts(p.read_text(encoding="utf-8"))
        added = tuple(a - b for a, b in zip(draft_counts(after), draft_counts(before)))
        total = [t + a for t, a in zip(total, added)]
        if staged != added:
            bad += 1
            print(f"MISMATCH ep{ep}: staged claims/artifacts/occurrences {staged} vs added {added}")
    print(f"mismatches {bad}; added claims {total[0]}, artifact items {total[1]}, meme occurrences {total[2]}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("staging", type=Path)
    ap.add_argument("--pre", action="store_true")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--expect", type=Path)
    ap.add_argument("--ref", default="HEAD")
    args = ap.parse_args()
    if args.pre:
        if not args.expect:
            raise SystemExit("--pre needs --expect BATCH_JSON")
        return pre(args.staging, args.expect)
    if args.post:
        return post(args.staging, args.ref)
    raise SystemExit("choose --pre or --post")


if __name__ == "__main__":
    raise SystemExit(main())
