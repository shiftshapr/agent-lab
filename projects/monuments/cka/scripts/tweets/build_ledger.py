#!/usr/bin/env python3
"""Build or extend the CKA tweet ledger (ROADMAP 1.5): tweets/tweets.jsonl, one record per @RealCandaceO post.

Sources, merged by id (first seen wins for text; status and sources accumulate):
- the 2025-09-09..2026-10-13 collection CSV (search, timeline, syndication and Wayback, deleted posts included);
- any number of twscrape JSONL files (e.g. the daily `search "from:RealCandaceO since:<date>"`).
Records: id, date (UTC ISO), url, status (live|deleted), is_retweet, reply_to, quoted_id, text, sources.
Posts before 2025-09-09 are ignored. Sorted by date. Daveed (2026-10-21): full text is kept, deleted posts included.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/tweets/build_ledger.py [--csv PATH] [JSONL ...]
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
LEDGER = CKA / "tweets" / "tweets.jsonl"
CUTOFF = "2025-09-09"


def norm_date(s: str) -> str:
    s = s.replace("+00:00", "Z").replace(".000Z", "Z")
    return s.replace(" ", "T") if "T" not in s else s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path)
    ap.add_argument("jsonl", nargs="*", type=Path)
    a = ap.parse_args()
    recs: dict[str, dict] = {}
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            recs[r["id"]] = r
    if a.csv:
        for r in csv.DictReader(open(a.csv, encoding="utf-8")):
            rid = r["id"]
            rec = recs.setdefault(rid, {"id": rid, "date": norm_date(r["date"]), "url": r["url"], "status": r["status"],
                                        "is_retweet": r["is_retweet"] == "True", "reply_to": r["reply_to"] or None,
                                        "quoted_id": r["quoted_id"] or None, "text": r["text"], "sources": []})
            if r["status"] == "deleted":
                rec["status"] = "deleted"
            rec["sources"] = sorted(set(rec["sources"]) | set(filter(None, r["sources"].split(";"))))
    for p in a.jsonl:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            t = json.loads(line)
            if (t.get("user") or {}).get("username", "").lower() != "realcandaceo":
                continue
            rid = t["id_str"]
            rec = recs.setdefault(rid, {"id": rid, "date": norm_date(t["date"]), "url": t["url"], "status": "live",
                                        "is_retweet": bool(t.get("retweetedTweet")),
                                        "reply_to": str(t["inReplyToTweetId"]) if t.get("inReplyToTweetId") else None,
                                        "quoted_id": (t.get("quotedTweet") or {}).get("id_str"),
                                        "text": t.get("rawContent", ""), "sources": []})
            rec["sources"] = sorted(set(rec["sources"]) | {"search"})
    out = sorted((r for r in recs.values() if r["date"][:10] >= CUTOFF), key=lambda r: (r["date"], r["id"]))
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(f"{len(out)} posts ({sum(r['status'] == 'deleted' for r in out)} deleted), {out[0]['date'][:10]}..{out[-1]['date'][:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
