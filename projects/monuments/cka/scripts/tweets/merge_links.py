#!/usr/bin/env python3
"""Merge reviewers' links_<NNN>.json into tweets/links.jsonl, and check the tweet ledger (ROADMAP 1.5 gate).

Merge: `merge_links.py PACK` adds or replaces one entry per post from PACK/links_*.json (ids normalised; unknown claim
or node ids are dropped and reported).
Check: `merge_links.py --check` verifies that every post in tweets/tweets.jsonl has exactly one links entry, every
claim and node id exists, relation and unlinked values are valid, and an unlinked entry carries no ids.
Exits non-zero if the check fails.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/tweets/merge_links.py [PACK] [--check]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
RELATIONS = {"same_allegation", "shown_on_air", "follow_up", "contradicts"}
UNLINKED = {"off_topic", "personal", "promotion", "retweet_no_comment", "reply_chatter", "unclear"}


def known_ids() -> tuple[set[str], set[str]]:
    claims = set()
    for f in (CKA / "drafts").glob("episode_*.md"):
        if not f.name.startswith("episode_000"):
            claims |= set(re.findall(r"^\*\*(C-\d+)\*\*", f.read_text(encoding="utf-8"), re.M))
    nodes = set(json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"])
    return claims, nodes


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack", nargs="?", type=Path)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    tweets = load(CKA / "tweets" / "tweets.jsonl")
    order = {t["id"]: i for i, t in enumerate(tweets)}
    lp = CKA / "tweets" / "links.jsonl"
    links = {l["id"]: l for l in load(lp)}
    claims, nodes = known_ids()
    if a.pack:
        dropped = []
        for f in sorted(a.pack.glob("links_*.json")):
            for e in json.load(open(f, encoding="utf-8")):
                e["id"] = str(e["id"])
                if e["id"] not in order:
                    dropped.append(f"{f.name}: unknown post {e['id']}")
                    continue
                for key, ok in (("claims", claims), ("nodes", nodes)):
                    if key in e:
                        bad = [x for x in e[key] if x not in ok]
                        dropped += [f"{e['id']}: {key} {x}" for x in bad]
                        e[key] = [x for x in dict.fromkeys(e[key]) if x in ok]
                        if not e[key]:
                            e.pop(key)
                if not e.get("claims"):
                    e.pop("relation", None)
                if e.get("note") == "":
                    e.pop("note")
                links[e["id"]] = {k: e[k] for k in ("id", "claims", "relation", "nodes", "unlinked", "note") if k in e}
        lp.write_text("".join(json.dumps(links[i], ensure_ascii=False) + "\n"
                              for i in sorted(links, key=lambda x: order.get(x, 1 << 30))), encoding="utf-8")
        print(f"links: {len(links)} of {len(tweets)} posts; dropped {len(dropped)} bad ids")
        for d in dropped[:20]:
            print("  dropped", d)
    if a.check:
        errs = []
        for t in tweets:
            e = links.get(t["id"])
            if not e:
                errs.append(f"{t['id']}: no links entry")
                continue
            if "unlinked" in e:
                if e["unlinked"] not in UNLINKED or e.get("claims") or e.get("nodes"):
                    errs.append(f"{t['id']}: bad unlinked entry")
            elif not e.get("claims") and not e.get("nodes"):
                errs.append(f"{t['id']}: neither linked nor unlinked")
            if e.get("claims") and e.get("relation") not in RELATIONS:
                errs.append(f"{t['id']}: bad relation {e.get('relation')}")
            errs += [f"{t['id']}: unknown claim {x}" for x in e.get("claims", []) if x not in claims]
            errs += [f"{t['id']}: unknown node {x}" for x in e.get("nodes", []) if x not in nodes]
        errs += [f"{i}: links entry for a post not in the ledger" for i in links if i not in order]
        print(f"tweet check: {len(tweets)} posts, {len(errs)} problems")
        for x in errs[:30]:
            print("  ", x)
        return 1 if errs else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
