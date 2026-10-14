#!/usr/bin/env python3
"""Build a supplement agent pack: reference tables, specs, the agent prompt and an episode list.

The pack is a working folder outside the repo (e.g. a scratchpad). It gets:
- nodes.tsv, memes.tsv, claims_index.tsv from the current canonical/ and drafts/ (agents grep these);
- SUPPLEMENT_SPEC.md, AGENT_PROMPT.md (paths filled in), SPEC.md, EPISTEMIC_GRAPH.md, example_episode_102.md and
  EXAMPLE_SUPPLEMENT_ep060.md;
- an empty staging folder and batch.json: the episodes to supplement, lowest claims-per-minute first.

Episodes already supplemented (audits/supplement_*/coverage_notes/) or skeleton-filled
(audits/skeleton_fill_*/episodes.json) are excluded, unless --episodes names
them. check_supplement.py reads the pack through the SKELETON_PACK environment variable.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/supplement/build_pack.py PACK_DIR --staging NAME [--count 20] [--episodes 12,57]
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import shutil
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
MARK = re.compile(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]")


def last_marker_minutes(transcript: Path) -> float:
    secs = [int(a) * 60 + int(b) if not c else int(a) * 3600 + int(b) * 60 + int(c)
            for a, b, c in MARK.findall(transcript.read_text(encoding="utf-8", errors="ignore"))]
    return max(secs) / 60 if secs else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack", type=Path)
    ap.add_argument("--staging", required=True)
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--episodes", help="comma-separated seq numbers to use instead of the density pick")
    args = ap.parse_args()
    pack = args.pack
    (pack / args.staging).mkdir(parents=True, exist_ok=True)

    nodes = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
    with open(pack / "nodes.tsv", "w", encoding="utf-8") as f:
        f.write("id\ttype\tname\taliases\n")
        for k, v in nodes.items():
            f.write(f"{k}\t{v['type']}\t{v['canonical_name']}\t{'; '.join(v.get('aliases', []))}\n")
    memes = json.loads((CKA / "canonical" / "memes.json").read_text(encoding="utf-8"))["entries"]
    with open(pack / "memes.tsv", "w", encoding="utf-8") as f:
        f.write("id\tterm\tdefinition\taliases\n")
        for k, v in memes.items():
            d = (v.get("definition") or "").replace("\t", " ").replace("\n", " ")
            f.write(f"{k}\t{v['canonical_term']}\t{d}\t{'; '.join(v.get('aliases', []))}\n")

    done = {int(m) for p in glob.glob(str(CKA / "audits" / "supplement_*" / "coverage_notes" / "episode_*.md"))
            for m in re.findall(r"episode_(\d{3})", Path(p).name)}
    for p in glob.glob(str(CKA / "audits" / "skeleton_fill_*" / "episodes.json")):
        done |= set(json.loads(Path(p).read_text(encoding="utf-8")))
    density = []
    with open(pack / "claims_index.tsv", "w", encoding="utf-8") as f:
        f.write("id\tepisode\tlabel\n")
        for p in sorted((CKA / "drafts").glob("episode_*.md")):
            ep = int(re.search(r"episode_(\d{3})", p.name).group(1))
            claims = re.findall(r"^\*\*(C-\d+)\*\*\s*(.*)$", p.read_text(encoding="utf-8"), re.M)
            for c, label in claims:
                f.write(f"{c}\t{ep}\t{label.strip()}\n")
            tr = sorted((CKA / "transcripts_corrected").glob(f"episode_{ep:03d}_*"))
            minutes = last_marker_minutes(tr[0]) if tr else 0
            if tr and minutes > 10:
                density.append((len(claims) / minutes, ep, tr[0].name))

    if args.episodes:
        want = [int(x) for x in args.episodes.split(",")]
        by_ep = {e: (d, e, n) for d, e, n in density}
        batch = [by_ep[e] for e in want]
    else:
        batch = sorted(x for x in density if x[1] not in done)[: args.count]
    (pack / "batch.json").write_text(json.dumps([[e, n] for _, e, n in batch], indent=1) + "\n", encoding="utf-8")

    docs = CKA / "docs"
    shutil.copy(docs / "supplement" / "SUPPLEMENT_SPEC.md", pack / "SUPPLEMENT_SPEC.md")
    shutil.copy(docs / "supplement" / "EXAMPLE_SUPPLEMENT_ep060.md", pack / "EXAMPLE_SUPPLEMENT_ep060.md")
    shutil.copy(docs / "EPISTEMIC_GRAPH.md", pack / "EPISTEMIC_GRAPH.md")
    shutil.copy(CKA / "audits" / "skeleton_fill_2026-10-13" / "EXTRACTION_SPEC.md", pack / "SPEC.md")
    shutil.copy(CKA / "drafts" / "episode_102.md", pack / "example_episode_102.md")
    prompt = (docs / "supplement" / "AGENT_PROMPT.md").read_text(encoding="utf-8")
    prompt = prompt.replace("<PACK>", str(pack.resolve())).replace("<CKA>", str(CKA)).replace("<STAGING>", args.staging)
    (pack / "AGENT_PROMPT.md").write_text(prompt, encoding="utf-8")

    print(f"pack {pack}: {len(nodes)} nodes, {len(memes)} memes; batch of {len(batch)}: "
          + ", ".join(str(e) for _, e, _ in batch))
    print(f"agent prompt: 'Follow {pack.resolve()}/AGENT_PROMPT.md exactly. SEQ=<n>, TRANSCRIPT=<file>'")
    print(f"checker: SKELETON_PACK={pack.resolve()} python3 -I {CKA}/scripts/check_supplement.py <n> --dir {args.staging}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
