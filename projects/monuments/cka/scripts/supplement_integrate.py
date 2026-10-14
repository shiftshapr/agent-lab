#!/usr/bin/env python3
"""Integrate supplement files (additions only) into existing CKA episode drafts.

A supplement adds claims, artifacts, nodes and meme occurrences that an earlier extraction missed. Existing items
are never edited, renumbered or removed. Placeholders: A-L<n>[.k], C-L<n>, N-P<n>, N-T<n>, M-N<n>.

For each episode in airing order this script:
- assigns claims from the global claim tip, artifact families from the artifact tip, persons from
  canonical next_person_id, topic/org/place from next_investigation_id and memes from memes.json next_id;
- dedupes new nodes and memes by normalised title against canonical/ and the batch (optional --merges map);
- appends new artifacts, node rows and claims to the end of the draft's registers, and appends meme occurrences
  under existing meme blocks (renumbered) or as new blocks;
- adds ledger lines: Tip-minted Nodes (<batch>) for new ids, Hole-minted Nodes (reintro-ep<NNN>) when a node first
  appears here but is introduced later (that later ledger entry becomes Reused), Reused Nodes Appearing, and an
  extended Claim Range;
- writes Coverage Notes to audits/<batch>/coverage_notes/episode_NNN.md;
- updates canonical/nodes.json and canonical/memes.json.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/supplement_integrate.py SUPPLEMENT_DIR --batch NAME [--merges JSON] [--dry-run]
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

TYPE_MAP = {"topic": "topic", "organization": "organization", "organisation": "organization", "org": "organization",
            "place": "place", "event": "topic", "thing": "topic"}
SECTION = {
    "art": r"^#{1,3} (?:3\.|III\.)?\s*Artifact Register.*$",
    "node": r"^#{1,3} (?:4\.|IV\.)?\s*Node Register.*$",
    "claim": r"^#{1,3} (?:5\.|V\.)?\s*Claim Register.*$",
    "meme": r"^#{1,3} (?:6\.|VI\.)?\s*Meme Register.*$",
}


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def max_id(prefix: str) -> int:
    rx = re.compile(rf"\b{prefix}-(\d+)")
    return max((int(m.group(1)) for p in (CKA / "drafts").glob("episode_*.md")
                for m in rx.finditer(p.read_text(encoding="utf-8"))), default=0)


def section(text: str, key: str) -> str:
    m = re.search(SECTION[key], text, re.M)
    if not m:
        return ""
    nxt = re.search(r"^#{1,3} ", text[m.end():], re.M)
    return text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]


def insert_at_section_end(text: str, key: str, block: str, fallback_header: str) -> str:
    if not block.strip():
        return text
    m = re.search(SECTION[key], text, re.M)
    if not m:
        anchor = re.search(r"^## (?:7\.|VI\.|VII\.)\s*(?:Optional Flags|Output Quality).*$", text, re.M)
        pos = anchor.start() if anchor else len(text)
        return text[:pos] + f"{fallback_header}\n\n{block.strip()}\n\n" + text[pos:]
    nxt = re.search(r"^#{1,3} ", text[m.end():], re.M)
    pos = m.end() + nxt.start() if nxt else len(text)
    before = text[:pos].rstrip("\n")
    return before + "\n\n" + block.strip() + "\n\n" + text[pos:]


def append_ids(line: str, ids: str) -> str:
    head, _, tail = line.partition(":")
    toks = [x.strip() for x in tail.split(",") if x.strip()]
    return f"{head}: " + ", ".join(toks + [x.strip() for x in ids.split(",") if x.strip()])


def blocks(sec: str, prefix: str) -> list[tuple[str, str]]:
    parts = re.split(rf"(?m)^(?=\*\*{prefix}-[\w.]+\*\*)", sec)
    return [(re.match(rf"\*\*({prefix}-[\w.]+)\*\*", p).group(1), p.rstrip()) for p in parts[1:]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("supplements", type=Path)
    ap.add_argument("--batch", required=True)
    ap.add_argument("--merges", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    npath, mpath = CKA / "canonical" / "nodes.json", CKA / "canonical" / "memes.json"
    ndata, mdata = json.loads(npath.read_text(encoding="utf-8")), json.loads(mpath.read_text(encoding="utf-8"))
    nodes, memes = ndata["nodes"], mdata["entries"]
    merges = {norm(k): v for k, v in json.loads(args.merges.read_text(encoding="utf-8")).items()} if args.merges else {}
    by_name: dict[str, str] = {}
    for k, v in nodes.items():
        for nm in [v["canonical_name"], *v.get("aliases", [])]:
            by_name.setdefault(norm(nm), k)
    meme_by_term = {norm(re.sub(r"^\(meme\)\s*", "", v["canonical_term"])): k for k, v in memes.items()}

    next_c, next_a = max_id("C") + 1, max_id("A") + 1
    next_p, next_t, next_m = int(ndata["next_person_id"]), int(ndata["next_investigation_id"]), int(mdata["next_id"])
    episodes = dp.load_draft_episodes(CKA / "drafts")
    intro_ep = dp.person_intro_episodes(episodes, strict=True)
    baseline = dp._baseline_ids(episodes)
    intro_kind: dict[int, str] = {}
    for _ep, _name, _path, content in episodes:
        for lm in re.finditer(r"^\s*-\s*(New Nodes Introduced|Hole-minted Nodes \([^)]*\)|Tip-minted Nodes \([^)]*\)):(.*)$", content, re.M):
            kind = "tip" if lm.group(1).startswith("Tip") else "hole"
            for x in re.findall(r"N-(\d+)", lm.group(2)):
                intro_kind.setdefault(int(x), kind)

    new_nodes, new_memes, batch_new, batch_memes = {}, {}, {}, {}
    moved: dict[int, tuple[int, int]] = {}
    cited_eps: dict[str, set[int]] = {}
    out, notes, report = {}, {}, []

    for path in sorted(args.supplements.glob("episode_*.md")):
        ep = int(re.search(r"(\d{3})", path.name).group(1))
        sup = path.read_text(encoding="utf-8")
        dpath = CKA / "drafts" / f"episode_{ep:03d}.md"
        draft = dpath.read_text(encoding="utf-8")
        draft_rows = set(re.findall(r"^\*\*(N-\d+)\*\*", draft, re.M))
        mp: dict[str, str] = {}
        for c in re.findall(r"^\*\*(C-L\d+)\*\*", sup, re.M):
            mp[c] = f"C-{next_c}"
            next_c += 1
        for fam in re.findall(r"^\*\*(A-L\d+)\*\*", sup, re.M):
            mp[fam] = f"A-{next_a}"
            next_a += 1
        minted: list[int] = []
        for nid, title, body in re.findall(r"^\*\*(N-[PT]\d+)\*\*\s+(.+?)\n(.*?)(?=^\*\*N-|^## |\Z)", sup, re.M | re.S):
            title = merges.get(norm(title), title).strip()
            key = norm(title)
            if key in by_name:
                mp[nid] = by_name[key]
                report.append(f"ep{ep}: {nid} '{title}' exists as {by_name[key]}; reused")
                continue
            if key in batch_new:
                mp[nid] = batch_new[key]
                continue
            if nid.startswith("N-P"):
                new, ntype = f"N-{next_p}", "person"
                next_p += 1
            else:
                tm = re.search(r"^Node Type:\s*(\w+)", body, re.M)
                ntype = TYPE_MAP.get((tm.group(1) if tm else "topic").lower(), "topic")
                new = f"N-{next_t}"
                next_t += 1
            am = re.search(r"Aliases?:\s*(.+?)\.?\s*$", body, re.M)
            aliases = [a.strip() for a in re.split(r"[;,]", am.group(1))] if am else []
            mp[nid] = batch_new[key] = new
            new_nodes[new] = {"canonical_name": title, "type": ntype,
                              "aliases": [a for a in aliases if a and norm(a) != key], "episodes": [ep]}
            minted.append(int(new[2:]))
        for mid, term in re.findall(r"^\*\*(M-N\d+)\*\*\s+(.+)$", sup, re.M):
            term = merges.get(norm(term), term)
            bare = re.sub(r"^\(meme\)\s*", "", term).strip()
            key = norm(bare)
            if key in meme_by_term:
                mp[mid] = meme_by_term[key]
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

        sup = re.sub(r"\b(?:C-L\d+|A-L\d+(?:\.\d+)?|N-[PT]\d+|M-N\d+)\b", sub, sup)
        cn = re.search(r"^## (?:7\.)\s*Coverage Notes.*$", sup, re.M)
        notes[ep] = sup[cn.end():].strip() if cn else ""

        def canon_header(m: re.Match[str]) -> str:
            meta = nodes.get(m.group(1)) or new_nodes.get(m.group(1))
            return f"**{m.group(1)}** {meta['canonical_name']}" if meta else m.group(0)

        def anchor(block: str) -> str:
            if re.search(r"^Anchored Artifacts:", block, re.M):
                return block
            return re.sub(r"(^Transcript Snippet:.*\n)", r"\1\nAnchored Artifacts: \n", block, count=1, flags=re.M)

        art = "\n\n".join(b for _, b in blocks(section(sup, "art"), "A"))
        node_rows = [re.sub(r"^\*\*(N-\d+)\*\*\s+.+$", canon_header, b, count=1, flags=re.M)
                     for nid, b in blocks(section(sup, "node"), "N") if nid not in draft_rows]
        claims = "\n\n".join(anchor(b) for _, b in blocks(section(sup, "claim"), "C"))
        text = insert_at_section_end(draft, "art", art, "## 3. Artifact Register")
        text = insert_at_section_end(text, "node", "\n\n".join(node_rows), "## 4. Node Register")
        text = insert_at_section_end(text, "claim", claims, "## 5. Claim Register")
        # memes: occurrences under existing blocks, else new block
        for mid, b in blocks(section(sup, "meme"), "M"):
            occ = re.split(r"(?m)^### Occurrence \d+\s*$", b)[1:]
            if not occ:
                continue
            msec = section(text, "meme")
            em = re.search(rf"^\*\*{mid}\*\*.*?(?=^\*\*M-|^## |\Z)", msec, re.M | re.S)
            if em:
                n0 = len(re.findall(r"^### Occurrence \d+", em.group(0), re.M))
                add = "".join(f"\n### Occurrence {n0 + i + 1}\n{o.rstrip()}\n" for i, o in enumerate(occ))
                body = em.group(0).rstrip()
                body = body[:-3].rstrip() if body.endswith("---") else body
                newb = body + "\n" + add + "\n---\n\n"
                start = text.find(msec) + em.start()
                text = text[:start] + newb + text[start + len(em.group(0)):]
            else:
                meta = memes.get(mid) or new_memes.get(mid)
                head = f"**{mid}** {meta['canonical_term']}\n" if meta else b.split("\n")[0] + "\n"
                newb = head + "".join(f"\n### Occurrence {i + 1}\n{o.rstrip()}\n" for i, o in enumerate(occ)) + "\n---"
                text = insert_at_section_end(text, "meme", newb, "## 6. Meme Register")

        sup_ids = {int(x) for x in re.findall(r"\bN-(\d+)\b", sup)}
        draft_ids = {int(x) for x in re.findall(r"\bN-(\d+)\b", draft)}
        reintro = sorted(n for n in sup_ids - set(minted) if intro_ep.get(n) is not None and intro_ep[n] > ep
                         and n not in moved and n not in baseline)
        for n in reintro:
            moved[n] = (ep, intro_ep[n])
        for n in sup_ids:
            cited_eps.setdefault(f"N-{n}", set()).add(ep)
        new_reused = sorted(n for n in sup_ids - draft_ids - set(minted) - set(reintro))
        led = []
        if minted:
            led.append(f"  - Tip-minted Nodes ({args.batch}): " + ", ".join(f"N-{n}" for n in sorted(minted)))
        re_hole = [n for n in reintro if intro_kind.get(n) != "tip"]
        re_tip = [n for n in reintro if intro_kind.get(n) == "tip"]
        if re_hole:
            led.append(f"  - Hole-minted Nodes (reintro-ep{ep:03d}): " + ", ".join(f"N-{n}" for n in re_hole))
        if re_tip:
            led.append(f"  - Tip-minted Nodes (reintro-ep{ep:03d}): " + ", ".join(f"N-{n}" for n in re_tip))
        if reintro:
            led.append("  - Intro moved earlier (supplement): these nodes first appear here; ids unchanged, later ledger line now Reused")
        if new_reused:
            if re.search(r"^  - Reused Nodes Appearing:", text, re.M):
                text = re.sub(r"^(  - Reused Nodes Appearing:.*)$", lambda m: append_ids(m.group(1), ", ".join(f"N-{n}" for n in new_reused)), text, count=1, flags=re.M)
            else:
                led.append("  - Reused Nodes Appearing: " + ", ".join(f"N-{n}" for n in new_reused))
        new_c = sorted(int(x) for x in re.findall(r"^\*\*C-(\d+)\*\*", sup, re.M))
        if new_c:
            led.append(f"  - Claim Range ({args.batch}): C-{new_c[0]}–C-{new_c[-1]}")
        if led:
            text = re.sub(r"(- \*\*Episode Ledger Summary\*\*:\n)", lambda m: m.group(1) + "\n".join(led) + "\n", text, count=1)
        out[ep] = text
        n_art = len(re.findall(r"^\*\*A-\d+\.\d+\*\*", art, re.M))
        report.append(f"ep{ep}: +{len(new_c)} claims, +{n_art} artifacts, "
                      f"+{len(minted)} new nodes, {len(reintro)} intro moves")

    print(f"claims to C-{next_c - 1}; artifacts to A-{next_a - 1}; persons {ndata['next_person_id']}..{next_p - 1}; "
          f"topics {ndata['next_investigation_id']}..{next_t - 1}; memes {mdata['next_id']}..{next_m - 1}; intro moves {len(moved)}")
    for r in report:
        print("  ", r)
    if args.dry_run:
        return 0

    for ep, t in out.items():
        (CKA / "drafts" / f"episode_{ep:03d}.md").write_text(t, encoding="utf-8")
    by_old: dict[int, list[int]] = {}
    for n, (_new, old) in moved.items():
        by_old.setdefault(old, []).append(n)
    for old, ids in by_old.items():
        dpath = CKA / "drafts" / f"episode_{old:03d}.md"
        d = dpath.read_text(encoding="utf-8")
        head, sep, rest = d, "", ""
        for n in ids:
            def drop(m: re.Match[str]) -> str:
                toks = [x.strip() for x in m.group(2).split(",") if x.strip() and x.strip() != f"N-{n}"]
                return f"{m.group(1)} {', '.join(toks)}" if toks else "\0DROP"
            head = re.sub(r"^(\s*- (?:New Nodes Introduced|(?:Hole|Tip)-minted Nodes \([^)]*\)):)(.*)$", drop, head, flags=re.M)
        head = "\n".join(l for l in head.split("\n") if l != "\0DROP")
        add = ", ".join(f"N-{n}" for n in sorted(ids))
        if re.search(r"^  - Reused Nodes Appearing:", head, re.M):
            head = re.sub(r"^(  - Reused Nodes Appearing:.*)$", lambda m: append_ids(m.group(1), add), head, count=1, flags=re.M)
        else:
            head = re.sub(r"(- \*\*Episode Ledger Summary\*\*:\n)", lambda m: m.group(1) + f"  - Reused Nodes Appearing: {add}\n", head, count=1)
        dpath.write_text(head + sep + rest, encoding="utf-8")
    for nid, eps in cited_eps.items():
        meta = nodes.get(nid) or new_nodes.get(nid)
        if meta is not None:
            meta["episodes"] = sorted(set(meta.get("episodes") or []) | eps)
    nodes.update(new_nodes)
    ndata["next_person_id"], ndata["next_investigation_id"] = next_p, next_t
    npath.write_text(json.dumps(ndata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    memes.update(new_memes)
    mdata["next_id"] = next_m
    mpath.write_text(json.dumps(mdata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    ndir = CKA / "audits" / args.batch / "coverage_notes"
    ndir.mkdir(parents=True, exist_ok=True)
    for ep, n in notes.items():
        (ndir / f"episode_{ep:03d}.md").write_text(f"# Coverage notes, episode {ep}\n\n{n or ''}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
