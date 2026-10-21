#!/usr/bin/env python3
"""Integrate staged skeleton-episode drafts into CKA with global ids.

Staged drafts (one per CKA seq) use placeholders: artifacts A-L<n>[.k], claims C-L<n>, new persons N-P<n>,
new topic/org/place N-T<n>, new memes M-N<n>. This script, in airing (seq) order:

- assigns claims from the global claim tip, artifact families from the artifact tip, persons from
  canonical next_person_id, topic/org/place from next_investigation_id and memes from memes.json next_id;
- dedupes new persons/topics/memes across the batch by normalised name (first episode wins);
- maps a "new" node whose name already exists in canonical/nodes.json onto that id (reported);
- rewrites reused node register headers to their canonical names;
- writes the Episode Ledger Summary (Tip-minted, Reused, Claim Range) and an empty Anchored Artifacts line
  where a claim has none;
- updates canonical/nodes.json, canonical/memes.json and config/yt_durations.json.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/fill_skeleton_integrate.py STAGING_DIR [--batch NAME] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CKA.parent / "scripts"))
import dia_preflight as dp  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "source"))
import cka_source as cs  # noqa: E402  (ROADMAP 3.0: episodes are read and written through the JSON source)

TYPE_MAP = {"topic": "topic", "organization": "organization", "organisation": "organization", "org": "organization",
            "place": "place", "event": "topic", "thing": "topic"}


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def max_id(prefix: str) -> int:
    rx = re.compile(rf"\b{prefix}-(\d+)")
    hi = 0
    for p in (CKA / "drafts").glob("episode_*.md"):
        for m in rx.finditer(p.read_text(encoding="utf-8")):
            hi = max(hi, int(m.group(1)))
    return hi


def secs_to_hms(s: int) -> str:
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("staging", type=Path)
    ap.add_argument("--batch", default="skeleton")
    ap.add_argument("--merges", type=Path, help="JSON {variant title: canonical title} applied before minting")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    npath = CKA / "canonical" / "nodes.json"
    nraw = npath.read_text(encoding="utf-8")
    ndata = json.loads(nraw)
    nodes = ndata["nodes"]
    mpath = CKA / "canonical" / "memes.json"
    mdata = json.loads(mpath.read_text(encoding="utf-8"))
    memes = mdata["entries"]

    by_name: dict[str, str] = {}
    for k, v in nodes.items():
        for nm in [v.get("canonical_name", "")] + list(v.get("aliases") or []):
            by_name.setdefault(norm(nm), k)
    meme_by_term = {norm(re.sub(r"^\(meme\)\s*", "", v["canonical_term"])): k for k, v in memes.items()}

    next_c = max_id("C") + 1
    next_a = max_id("A") + 1
    next_p = int(ndata["next_person_id"])
    next_t = int(ndata["next_investigation_id"])
    next_m = int(mdata["next_id"])
    episodes = dp.load_draft_episodes(CKA / "drafts")
    intro_ep = dp.person_intro_episodes(episodes, strict=True)

    merges = {norm(k): v for k, v in json.loads(args.merges.read_text(encoding="utf-8")).items()} if args.merges else {}
    variant_aliases: dict[str, set[str]] = {}
    batch_new: dict[str, str] = {}      # norm name -> new id (this batch)
    batch_memes: dict[str, str] = {}
    report: list[str] = []
    early: list[str] = []
    new_nodes: dict[str, dict] = {}
    new_memes: dict[str, dict] = {}
    cited_eps: dict[str, set[int]] = {}
    out: dict[int, str] = {}
    moved: dict[int, tuple[int, int]] = {}   # node -> (new intro ep, old intro ep)

    for path in sorted(args.staging.glob("episode_*.md")):
        ep = int(re.search(r"(\d{3})", path.name).group(1))
        t = path.read_text(encoding="utf-8")
        mp: dict[str, str] = {}
        claims = re.findall(r"^\*\*(C-L\d+)\*\*", t, re.M)
        for c in claims:
            mp[c] = f"C-{next_c}"
            next_c += 1
        for fam in re.findall(r"^\*\*(A-L\d+)\*\*", t, re.M):
            mp[fam] = f"A-{next_a}"
            next_a += 1
        minted_here: list[int] = []
        for nid, title, body in re.findall(r"^\*\*(N-[PT]\d+)\*\*\s+(.+?)\n(.*?)(?=^\*\*N-|^## |\Z)", t, re.M | re.S):
            if norm(title) in merges:
                variant_aliases.setdefault(norm(merges[norm(title)]), set()).add(title.strip())
                title = merges[norm(title)]
            key = norm(title)
            if key in by_name:
                mp[nid] = by_name[key]
                report.append(f"ep{ep}: {nid} '{title}' already exists as {by_name[key]}; reused")
                continue
            if key in batch_new:
                mp[nid] = batch_new[key]
                continue
            if nid.startswith("N-P"):
                new = f"N-{next_p}"
                next_p += 1
                ntype = "person"
            else:
                tm = re.search(r"^Node Type:\s*(\w+)", body, re.M)
                ntype = TYPE_MAP.get((tm.group(1) if tm else "topic").lower(), "topic")
                new = f"N-{next_t}"
                next_t += 1
            am = re.search(r"Aliases?:\s*(.+?)\.?\s*$", body, re.M)
            aliases = [a.strip() for a in re.split(r"[;,]", am.group(1))] if am else []
            mp[nid] = batch_new[key] = new
            new_nodes[new] = {"canonical_name": title.strip(), "type": ntype,
                              "aliases": [a for a in aliases if a and norm(a) != key], "episodes": [ep]}
            minted_here.append(int(new[2:]))
        for mid, term in re.findall(r"^\*\*(M-N\d+)\*\*\s+(.+)$", t, re.M):
            if norm(term) in merges:
                term = merges[norm(term)]
            bare = re.sub(r"^\(meme\)\s*", "", term).strip()
            key = norm(bare)
            if key in meme_by_term:
                mp[mid] = meme_by_term[key]
                report.append(f"ep{ep}: {mid} '{bare}' already exists as {meme_by_term[key]}; reused")
            elif key in batch_memes:
                mp[mid] = batch_memes[key]
            else:
                new = f"M-{next_m}"
                next_m += 1
                mp[mid] = batch_memes[key] = new
                new_memes[new] = {"canonical_term": f"(meme) {bare}", "type": "meme", "aliases": [],
                                  "definition": "", "context": "cka", "first_episode": ep}

        def sub(m: re.Match[str]) -> str:
            tok = m.group(0)
            if tok in mp:
                return mp[tok]
            fam = re.match(r"(A-L\d+)(\.\d+)$", tok)
            if fam and fam.group(1) in mp:
                return mp[fam.group(1)] + fam.group(2)
            raise SystemExit(f"ep{ep}: unmapped placeholder {tok}")

        t = re.sub(r"\b(?:C-L\d+|A-L\d+(?:\.\d+)?|N-[PT]\d+|M-N\d+)\b", sub, t)
        # each claim gets an Anchored Artifacts line
        def anchor(block: str) -> str:
            if re.search(r"^Anchored Artifacts:", block, re.M):
                return block
            return re.sub(r"(^Transcript Snippet:.*\n)", r"\1\nAnchored Artifacts: \n", block, count=1, flags=re.M)
        parts = re.split(r"(?m)^(?=\*\*C-\d+\*\*)", t)
        t = parts[0] + "".join(anchor(p) for p in parts[1:])
        # canonical names on reused register headers
        def header(m: re.Match[str]) -> str:
            nid = m.group(1)
            meta = nodes.get(nid) or new_nodes.get(nid)
            return f"**{nid}** {meta['canonical_name']}" if meta else m.group(0)
        def meme_header(m: re.Match[str]) -> str:
            meta = memes.get(m.group(1)) or new_memes.get(m.group(1))
            return f"**{m.group(1)}** {meta['canonical_term']}" if meta else m.group(0)
        t = re.sub(r"^\*\*(M-\d+)\*\*\s+.+$", meme_header, t, flags=re.M)
        reg_a, reg_b = t.find("## 4. Node Register"), t.find("## 5. Claim Register")
        t = t[:reg_a] + re.sub(r"^\*\*(N-\d+)\*\*\s+.+$", header, t[reg_a:reg_b], flags=re.M) + t[reg_b:]

        cited = sorted({int(x) for x in re.findall(r"\bN-(\d+)\b", t)})
        orig = cs.read_draft_text(ep)
        kept = re.findall(r"^  - Hole-minted Nodes \(.*$", orig, re.M)
        kept_ids = {int(x) for line in kept for x in re.findall(r"N-(\d+)", line)}
        reintro_here = sorted(n for n in cited if n not in minted_here and n not in kept_ids
                              and intro_ep.get(n) is not None and intro_ep[n] > ep and n not in moved)
        for n in reintro_here:
            moved[n] = (ep, intro_ep[n])
        reused = [n for n in cited if n not in minted_here and n not in kept_ids and n not in reintro_here]
        ledger = list(kept)
        for n in cited:
            cited_eps.setdefault(f"N-{n}", set()).add(ep)
            first = intro_ep.get(n)
            if n not in minted_here and first is not None and first > ep and moved.get(n, (ep,))[0] > ep:
                early.append(f"ep{ep}: N-{n} ({(nodes.get(f'N-{n}') or {}).get('canonical_name')}) introduced in ep{first}")
        if reintro_here:
            ledger.append(f"  - Hole-minted Nodes (reintro-ep{ep:03d}): " + ", ".join(f"N-{n}" for n in reintro_here))
            ledger.append("  - Intro moved earlier (skeleton fill): these nodes first appear here; ids unchanged, later ledger line now Reused")
        if minted_here:
            ledger.append(f"  - Tip-minted Nodes ({args.batch}): " + ", ".join(f"N-{n}" for n in sorted(minted_here)))
        if reused:
            ledger.append("  - Reused Nodes Appearing: " + ", ".join(f"N-{n}" for n in reused))
        all_c = sorted({int(x) for x in re.findall(r"^\*\*C-(\d+)\*\*", t, re.M)})
        if all_c:
            runs, start = [], all_c[0]
            for a, b in zip(all_c, all_c[1:] + [None]):
                if b != a + 1:
                    runs.append(f"C-{start}" if start == a else f"C-{start}–C-{a}")
                    start = b
            ledger.append("  - Claim Range: " + ", ".join(runs))
        ledger.append("  - (see registers)")
        t = re.sub(r"(- \*\*Episode Ledger Summary\*\*:\n)(?:  - .*\n)+", lambda m: m.group(1) + "\n".join(ledger) + "\n", t, count=1)
        out[ep] = t

    print(f"episodes {sorted(out)}; claims to C-{next_c - 1}; artifacts to A-{next_a - 1}; "
          f"persons {int(ndata['next_person_id'])}..{next_p - 1}; topics {int(ndata['next_investigation_id'])}..{next_t - 1}; "
          f"memes {int(mdata['next_id'])}..{next_m - 1}")
    for r in report:
        print("  note:", r)
    print(f"intro moved earlier: {len(moved)} nodes")
    print(f"cited before intro (remaining): {len(early)}")
    for e in early:
        print("  early:", e)
    if args.dry_run:
        return 0

    for ep, t in out.items():
        cs.write_draft_text(ep, t)
    by_old: dict[int, list[int]] = {}
    for n, (_new_ep, old_ep) in moved.items():
        by_old.setdefault(old_ep, []).append(n)
    for old_ep, ids in sorted(by_old.items()):
        dpath = CKA / "drafts" / f"episode_{old_ep:03d}.md"
        d = cs.read_draft_text(old_ep)
        head, sep, rest = d.partition("\n# ")
        for n in ids:
            pat = re.compile(rf"^(  - (?:New Nodes Introduced|Hole-minted Nodes \([^)]*\)):)(.*)$", re.M)
            def drop(m: re.Match[str]) -> str:
                toks = [x.strip() for x in m.group(2).split(",") if x.strip()]
                toks = [x for x in toks if x != f"N-{n}"]
                return f"{m.group(1)} {', '.join(toks)}" if toks else "\0DROP"
            head = pat.sub(drop, head)
        head = "\n".join(l for l in head.split("\n") if l != "\0DROP")
        add = ", ".join(f"N-{n}" for n in sorted(ids))
        if re.search(r"^  - Reused Nodes Appearing:", head, re.M):
            head = re.sub(r"^(  - Reused Nodes Appearing:)(.*)$", lambda m: m.group(1) + " " + ", ".join([x.strip() for x in m.group(2).split(",") if x.strip()] + [add]), head, count=1, flags=re.M)
        else:
            head = re.sub(r"^(- \*\*Episode Ledger Summary\*\*:\n)", lambda m: m.group(1) + f"  - Reused Nodes Appearing: {add}\n", head, count=1, flags=re.M)
        cs.write_draft_text(old_ep, head + sep + rest)
        print(f"  moved intro of {add} out of ep{old_ep}")
    for nid, eps in cited_eps.items():
        meta = nodes.get(nid) or new_nodes.get(nid)
        if meta is not None:
            meta["episodes"] = sorted(set(meta.get("episodes") or []) | eps)
    for nid, meta in new_nodes.items():
        extra = variant_aliases.get(norm(meta["canonical_name"]), set())
        meta["aliases"] = sorted(set(meta["aliases"]) | {a for a in extra if norm(a) != norm(meta["canonical_name"])})
    nodes.update(new_nodes)
    ndata["nodes"] = nodes  # keep existing key order; new nodes appended
    ndata["next_person_id"] = next_p
    ndata["next_investigation_id"] = next_t
    npath.write_text(json.dumps(ndata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    memes.update(new_memes)
    mdata["next_id"] = next_m
    mpath.write_text(json.dumps(mdata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    ypath = CKA / "config" / "yt_durations.json"
    ydata = json.loads(ypath.read_text(encoding="utf-8"))
    for ep in out:
        tr = next((CKA / "transcripts_corrected").glob(f"episode_{ep:03d}_*"), None)
        if tr is None:
            continue
        fm = tr.read_text(encoding="utf-8")
        yt = re.search(r"^youtube_id:\s*(\S+)", fm, re.M)
        du = re.search(r'^duration:\s*"?([\d:]+)"?', fm, re.M)
        if yt and du:
            p = [int(x) for x in du.group(1).split(":")]
            s = p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
            ydata.setdefault("by_youtube_id", {}).setdefault(yt.group(1), s)
    ypath.write_text(json.dumps(ydata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
