#!/usr/bin/env python3
"""Merge duplicate person nodes into a kept node, then close the id holes in the person band.

Each pair OLD:KEEP folds OLD into KEEP: OLD's aliases (and its canonical name) and episodes join KEEP, OLD's
register rows and intro-ledger entries are removed, and every other reference to OLD becomes KEEP. Person ids
above each removed id then shift down so the band stays dense (N-1..N-<p>, no holes). Topic/org/place ids
(N-10000+) are untouched.

Rewrites drafts, inscription, canonical, config, companion and scripts/hostile_hard_gates.py, like
compact_node_ids.py. Audits keep the ids of their time; the id map is written to
audits/person_merge_<date>/id_map.csv. Transcripts are not touched.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/merge_person_nodes.py OLD:KEEP [OLD:KEEP ...] --date YYYY-MM-DD [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
MONUMENTS = CKA.parent
INCLUDE_DIRS = ["drafts", "inscription", "canonical", "config", "companion"]
INCLUDE_FILES = [MONUMENTS / "scripts" / "hostile_hard_gates.py"]
TEXT_SUFFIXES = {".md", ".json", ".csv", ".txt", ".jsonl", ".py"}
TOKEN_RE = re.compile(r"(?<![0-9A-Za-z\-])N-(\d+)(?!\d)")
TOPIC_MIN = 10000
INTRO_RE = re.compile(r"^(\s*-\s*(?:\*\*)?(?:New (?:Person )?Nodes Introduced[^:]*|(?:Hole|Tip)-minted Nodes \([^)]*\))(?:\*\*)?:\s*)(.*)$", re.M)
LIST_RE = re.compile(r"^((?:Mentions|Related Nodes|Connected|CapturedAt|\s*-\s*Reused Nodes Appearing|\*Related):?\s*)(.*?)(\*?)$", re.M)


def dedupe_ids(seg: str) -> str:
    seen, out = set(), []
    for tok in (t.strip() for t in seg.split(",")):
        key = tok.split(" ")[0]
        if not tok or (TOKEN_RE.fullmatch(key) and key in seen):
            continue
        seen.add(key)
        out.append(tok)
    return ", ".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pairs", nargs="+")
    ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    merge = {int(o): int(k) for o, k in (p.replace("N-", "").split(":") for p in args.pairs)}
    if any(o >= TOPIC_MIN or k >= TOPIC_MIN or k in merge for o, k in merge.items()):
        raise SystemExit("person ids only; a KEEP id cannot itself be merged")

    npath = CKA / "canonical" / "nodes.json"
    raw = npath.read_text(encoding="utf-8")
    ndata = json.loads(raw)
    nodes = ndata["nodes"]
    persons = sorted(int(k[2:]) for k in nodes if int(k[2:]) < TOPIC_MIN)
    removed = sorted(merge)

    def shift(n: int) -> int:
        n = merge.get(n, n)
        return n - sum(1 for r in removed if r < n) if n < TOPIC_MIN else n

    id_map = {n: shift(n) for n in persons if shift(n) != n}

    # 1. canonical: fold OLD into KEEP before any renumbering
    for o, k in merge.items():
        so, sk = nodes[f"N-{o}"], nodes[f"N-{k}"]
        sk["aliases"] = sk.get("aliases", []) + [a for a in [so["canonical_name"], *so.get("aliases", [])]
                                                 if a not in sk.get("aliases", []) and a != sk["canonical_name"]]
        sk["episodes"] = sorted(set(sk.get("episodes") or []) | set(so.get("episodes") or []))
        del nodes[f"N-{o}"]
    ndata["nodes"] = {f"N-{shift(int(k[2:]))}": v for k, v in nodes.items()}
    ndata["next_person_id"] = int(ndata["next_person_id"]) - len(removed)
    if not args.dry_run:
        npath.write_text(json.dumps(ndata, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")

    # 2. drafts: drop OLD rows and intro entries, then remap and dedupe lists
    for p in sorted((CKA / "drafts").glob("episode_*.md")):
        t = p.read_bytes().decode("utf-8")
        o_t = t
        for o in merge:
            t = re.sub(rf"^\*\*N-{o}\*\*[^\n]*\n.*?(?=^\*\*[NCAM]-|^#{{1,3}} |\Z)", "", t, flags=re.M | re.S)
            t = INTRO_RE.sub(lambda m: m.group(1) + ", ".join(x for x in (s.strip() for s in m.group(2).split(","))
                                                               if x and x.split(" ")[0] != f"N-{o}"), t)
        t = TOKEN_RE.sub(lambda m: f"N-{shift(int(m.group(1)))}", t)
        t = LIST_RE.sub(lambda m: m.group(1) + dedupe_ids(m.group(2)) + m.group(3), t)
        if t != o_t and not args.dry_run:
            p.write_bytes(t.encode("utf-8"))

    # 3. inscriptions: remap, then fold duplicate node objects and dedupe id lists
    for p in sorted((CKA / "inscription").glob("*.json")):
        r = p.read_text(encoding="utf-8")
        d = json.loads(TOKEN_RE.sub(lambda m: f"N-{shift(int(m.group(1)))}", r))

        def fix(x):
            if isinstance(x, list):
                if all(isinstance(i, str) for i in x):
                    return list(dict.fromkeys(x))
                return [fix(i) for i in x]
            if isinstance(x, dict):
                return {k: fix(v) for k, v in x.items()}
            return x
        d = fix(d)
        if isinstance(d.get("nodes"), list):
            seen: dict[str, dict] = {}
            out = []
            for nd in d["nodes"]:
                ref = nd.get("ref")
                if ref in seen:
                    for k, v in nd.items():
                        if isinstance(v, list):
                            seen[ref][k] = list(dict.fromkeys((seen[ref].get(k) or []) + v))
                    continue
                seen[ref] = nd
                out.append(nd)
            d["nodes"] = out
        if not args.dry_run:
            p.write_text(json.dumps(d, indent=2, ensure_ascii="\\u" in r) + "\n", encoding="utf-8")

    # 4. everything else: token remap only
    files = [f for d in INCLUDE_DIRS if d not in ("drafts", "inscription") for f in (CKA / d).rglob("*")
             if f.is_file() and f.suffix in TEXT_SUFFIXES and f != npath] + INCLUDE_FILES
    for f in files:
        t = f.read_text(encoding="utf-8")
        t2 = TOKEN_RE.sub(lambda m: f"N-{shift(int(m.group(1)))}", t)
        if t2 != t and not args.dry_run:
            f.write_text(t2, encoding="utf-8")

    out = CKA / "audits" / f"person_merge_{args.date}"
    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)
        with open(out / "id_map.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["old_id", "new_id", "note"])
            for o, n in sorted(id_map.items()):
                w.writerow([f"N-{o}", f"N-{n}", "merged" if o in merge else "shifted"])
    print(f"merged {len(merge)}; shifted {sum(1 for o in id_map if o not in merge)} person ids; "
          f"next_person_id {ndata['next_person_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
