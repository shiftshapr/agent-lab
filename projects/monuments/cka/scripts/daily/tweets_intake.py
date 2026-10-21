#!/usr/bin/env python3
"""Daily tweet intake (ROADMAP 1.5): fetch new @RealCandaceO posts and build a linking pack for them.

- Runs twscrape (spare account in ~/agent-lab-data/cka_tweets_tools/accounts.db; never the main X account) for
  `from:RealCandaceO since:<last ledger date - 1 day>`, saving WORK/tweets_new.jsonl.
- Extends tweets/tweets.jsonl with build_ledger.py, then writes WORK/tweets_pack with link_pack.py for posts that
  tweets/links.jsonl does not cover yet.
Exit status: 0 with posts to link, 3 when there is nothing new, 1 on error. It edits the working tree only.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/daily/tweets_intake.py WORK_DIR
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
REPO = CKA.parents[2]
TOOLS = Path.home() / "agent-lab-data" / "cka_tweets_tools"


def main() -> int:
    work = Path(sys.argv[1])
    work.mkdir(parents=True, exist_ok=True)
    ledger = CKA / "tweets" / "tweets.jsonl"
    last = max(json.loads(l)["date"][:10] for l in ledger.read_text(encoding="utf-8").splitlines())
    since = (dt.date.fromisoformat(last) - dt.timedelta(days=1)).isoformat()
    out = work / "tweets_new.jsonl"
    with open(out, "w") as f, open(work / "tweets_new.err", "w") as e:
        r = subprocess.run([str(TOOLS / ".venv" / "bin" / "twscrape"), "--db", str(TOOLS / "accounts.db"), "search",
                            f"from:RealCandaceO since:{since}", "--limit", "1000"], stdout=f, stderr=e, cwd=TOOLS)
    if r.returncode != 0:
        print("twscrape failed; see tweets_new.err")
        return 1
    py = sys.executable
    subprocess.run([py, str(CKA / "scripts" / "tweets" / "build_ledger.py"), str(out)], cwd=REPO, check=True)
    pack = work / "tweets_pack"
    res = subprocess.run([py, str(CKA / "scripts" / "tweets" / "link_pack.py"), str(pack), "--chunk", "100"],
                         cwd=REPO, capture_output=True, text=True, check=True)
    print(res.stdout.strip())
    return 3 if res.stdout.startswith("0 posts") else 0


if __name__ == "__main__":
    raise SystemExit(main())
