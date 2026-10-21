#!/usr/bin/env python3
"""Build a tweet-linking pack (ROADMAP 1.5) for Opus reviewers.

For the ledger posts that tweets/links.jsonl does not cover yet (or --all), in date order, chunks of --chunk posts:
- PACK/tweets_<NNN>.md lists each post (id, date, status, retweet/reply flags, text);
- PACK/claims_<NNN>.tsv lists the candidate claims from episodes uploaded between 3 days before the first post and
  10 days after the last (id, episode, upload date, label, claim text, Mentions);
- PACK/nodes.tsv (id, type, name, aliases) and PACK/PROMPT.md (from docs/tweets/LINK_PROMPT.md, <PACK> filled in).
Reviewers write PACK/links_<NNN>.json; merge them with merge_links.py.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/tweets/link_pack.py PACK [--chunk 100] [--all]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pack", type=Path)
    ap.add_argument("--chunk", type=int, default=100)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    tweets = [json.loads(l) for l in (CKA / "tweets" / "tweets.jsonl").read_text(encoding="utf-8").splitlines()]
    done = set()
    lp = CKA / "tweets" / "links.jsonl"
    if lp.exists() and not a.all:
        done = {json.loads(l)["id"] for l in lp.read_text(encoding="utf-8").splitlines()}
    todo = [t for t in tweets if t["id"] not in done]
    man = json.loads((CKA / "input" / "episode_manifest.json").read_text(encoding="utf-8"))
    ep_date = {e["seq"]: e["upload_date"] for e in man["episodes"]}
    claims = []
    for f in sorted((CKA / "drafts").glob("episode_*.md")):
        ep = int(re.search(r"episode_(\d+)", f.name).group(1))
        if ep == 0 or ep not in ep_date:
            continue
        for m in re.finditer(r"^\*\*(C-\d+)\*\* (.*?)\n(.*?)(?=^\*\*C-|\Z)", f.read_text(encoding="utf-8"), re.M | re.S):
            body = m.group(3)
            cl = re.search(r"^Claim: (.*)$", body, re.M)
            me = re.search(r"^Mentions: (.*)$", body, re.M)
            claims.append((ep_date[ep], m.group(1), ep, m.group(2).strip(), (cl.group(1) if cl else "")[:300],
                           me.group(1).strip() if me else ""))
    nodes = json.loads((CKA / "canonical" / "nodes.json").read_text(encoding="utf-8"))["nodes"]
    a.pack.mkdir(parents=True, exist_ok=True)
    with open(a.pack / "nodes.tsv", "w", encoding="utf-8") as f:
        f.write("id\ttype\tname\taliases\n")
        for k, v in sorted(nodes.items(), key=lambda kv: int(kv[0][2:])):
            f.write(f"{k}\t{v.get('type', '')}\t{v['canonical_name']}\t{'; '.join(v.get('aliases', []))}\n")
    prompt = (CKA / "docs" / "tweets" / "LINK_PROMPT.md").read_text(encoding="utf-8").replace("<PACK>", str(a.pack))
    (a.pack / "PROMPT.md").write_text(prompt, encoding="utf-8")
    n = 0
    for i in range(0, len(todo), a.chunk):
        n += 1
        ch = todo[i:i + a.chunk]
        lo = (dt.date.fromisoformat(ch[0]["date"][:10]) - dt.timedelta(days=3)).isoformat()
        hi = (dt.date.fromisoformat(ch[-1]["date"][:10]) + dt.timedelta(days=10)).isoformat()
        with open(a.pack / f"tweets_{n:03d}.md", "w", encoding="utf-8") as f:
            for t in ch:
                flags = ", ".join(x for x in ("DELETED" if t["status"] == "deleted" else "",
                                              "retweet" if t["is_retweet"] else "",
                                              f"reply to {t['reply_to']}" if t["reply_to"] else "",
                                              f"quotes {t['quoted_id']}" if t["quoted_id"] else "") if x)
                f.write(f"## {t['id']} ({t['date']}{', ' + flags if flags else ''})\n{t['text']}\n\n")
        with open(a.pack / f"claims_{n:03d}.tsv", "w", encoding="utf-8") as f:
            f.write("claim\tepisode\tdate\tlabel\tclaim\tmentions\n")
            for c in claims:
                if lo <= c[0] <= hi:
                    f.write(f"{c[1]}\t{c[2]}\t{c[0]}\t{c[3]}\t{c[4]}\t{c[5]}\n")
    print(f"{len(todo)} posts to link in {n} chunks -> {a.pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
