#!/usr/bin/env python3
"""Add meme occurrences from already-integrated supplement files that the integrator skipped.

supplement_integrate.py ended a register section at the first ``###`` heading, so a supplement's Meme Register
(``### Occurrence N`` subheadings) parsed as empty and its occurrences were dropped. Claims, artifacts and nodes
were not affected. This re-reads each supplement's Meme Register, maps M-N placeholders to the meme ids the
integration minted (by canonical term), maps any C-L placeholder to the integrated claim with the same title,
and inserts the occurrences with the same logic as the integrator. Exact repeats are skipped, so a rerun is a
no-op. Empty canonical definitions are filled from the block's Definition line or its first occurrence Context.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/supplement_memes_backfill.py SUPPLEMENT_DIR [--merges JSON] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import supplement_integrate as si  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "source"))
import cka_source as cs  # noqa: E402  (ROADMAP 3.0: episodes are read and written through the JSON source)

CKA = si.CKA


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("supplements", type=Path)
    ap.add_argument("--merges", type=Path, help="the title merge map used for the integration")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mpath = CKA / "canonical" / "memes.json"
    raw = mpath.read_text(encoding="utf-8")
    mdata = json.loads(raw)
    memes = mdata["entries"]
    merges = {si.norm(k): v for k, v in json.loads(args.merges.read_text(encoding="utf-8")).items()} if args.merges else {}
    by_term = {si.norm(re.sub(r"^\(meme\)\s*", "", v["canonical_term"])): k for k, v in memes.items()}
    node_by_name: dict[str, str] = {}
    for k, v in json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"].items():
        for nm in [v["canonical_name"], *v.get("aliases", [])]:
            node_by_name.setdefault(si.norm(nm), k)
    corrections = [(re.compile(r[0]), r[1], set(r[2]) if len(r) > 2 else None) for r in json.loads(
        (CKA / "config" / "transcript_name_corrections.json").read_text(encoding="utf-8"))["corrections"]]
    total, defs = 0, 0
    for path in sorted(args.supplements.glob("episode_*.md")):
        ep = int(re.search(r"episode_(\d{3})", path.name).group(1))
        sup = path.read_text(encoding="utf-8")
        msec = si.section(sup, "meme")
        if not msec.strip():
            continue
        dpath = CKA / "drafts" / f"episode_{ep:03d}.md"
        draft = cs.read_draft_text(ep)
        mp: dict[str, str] = {}
        for mid, term in re.findall(r"^\*\*(M-N\d+)\*\*\s+(.+)$", msec, re.M):
            term = merges.get(si.norm(term), term)
            key = si.norm(re.sub(r"^\(meme\)\s*", "", term))
            if key not in by_term:
                raise SystemExit(f"ep{ep}: {mid} '{term}' has no canonical meme")
            mp[mid] = by_term[key]
        for nid, title in re.findall(r"^\*\*(N-[PT]\d+)\*\*\s+(.+)$", sup, re.M):
            key = si.norm(merges.get(si.norm(title), title))
            if key in node_by_name:
                mp[nid] = node_by_name[key]
        titles = {t.strip(): c for c, t in re.findall(r"^\*\*(C-\d+)\*\*\s+(.+)$", draft, re.M)}
        for cl, t in re.findall(r"^\*\*(C-L\d+)\*\*\s+(.+)$", sup, re.M):
            if t.strip() in titles:
                mp[cl] = titles[t.strip()]

        def sub(m: re.Match[str]) -> str:
            if m.group(0) not in mp:
                raise SystemExit(f"ep{ep}: unmapped placeholder {m.group(0)} in Meme Register")
            return mp[m.group(0)]

        msec = re.sub(r"\b(?:C-L\d+|A-L\d+(?:\.\d+)?|N-[PT]\d+|M-N\d+)\b", sub, msec)
        # Staged text predates apply_name_corrections; correct it too, or a corrected draft's occurrences look new.
        for rx, rep, eps in corrections:
            if eps is None or ep in eps:
                msec = rx.sub(rep, msec)
        before = len(re.findall(r"^### Occurrence \d+", si.section(draft, "meme"), re.M))
        text = si.insert_memes(draft, msec, memes.get)
        added = len(re.findall(r"^### Occurrence \d+", si.section(text, "meme"), re.M)) - before
        total += added
        for mid, b in si.blocks(msec, "M"):
            meta = memes.get(mid)
            if meta is None or meta.get("definition"):
                continue
            dm = re.search(r"^Definition:\s*(.+)$", b, re.M) or re.search(r"^Context:\s*(.+)$", b, re.M)
            if dm:
                meta["definition"] = dm.group(1).strip()
                defs += 1
        print(f"ep{ep}: +{added} meme occurrences")
        if not args.dry_run and text != draft:
            cs.write_draft_text(ep, text)
    print(f"total +{total} occurrences; {defs} definitions filled")
    if not args.dry_run:
        mpath.write_text(json.dumps(mdata, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
