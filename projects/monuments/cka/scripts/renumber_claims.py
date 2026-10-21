#!/usr/bin/env python3
"""Renumber CKA claims densely from C-1 in airing order (Daveed, 2026-10-20).

New ids follow (episode, Claim Timestamp, position in the draft), so ids read chronologically and leave no holes.
- Rewrites every C-id token (in one pass, through the old->new map) in drafts, inscription, config and
  scripts/hostile_hard_gates.py. Audits are not rewritten: they keep the ids of their time, translated by
  audits/claim_renumber_<date>/id_map.csv. Transcripts are not touched. Regenerate the companion afterwards.
- Replaces each episode's "Claim Range ..." ledger lines with one contiguous "Claim Range: C-a–C-b".
- Updates the CA_DEBT_CALLOUT note (claims no longer continue the Bride of Charlie band).

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/renumber_claims.py --date YYYY-MM-DD [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "source"))
import cka_source as cs  # noqa: E402  (ROADMAP 3.0)

CKA = Path(__file__).resolve().parents[1]
MON = CKA.parent
TOKEN = re.compile(r"(?<![0-9A-Za-z\-])C-(\d+)(?!\d)")
HEADER = re.compile(r"^\*\*C-(\d+)\*\*", re.M)
TS = re.compile(r"Claim Timestamp:\s*(\d{1,2}):(\d{2}):(\d{2})")
RANGE_LINE = re.compile(r"^\s*-\s*Claim Range[^\n]*\n", re.M)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = []
    for f in sorted((CKA / "drafts").glob("episode_*.md")):
        ep = int(re.search(r"episode_(\d+)", f.name).group(1))
        if ep == 0:
            continue
        s = cs.read_draft_text(ep)
        heads = list(HEADER.finditer(s))
        for i, m in enumerate(heads):
            block = s[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(s)]
            t = TS.search(block[:600])
            secs = int(t.group(1)) * 3600 + int(t.group(2)) * 60 + int(t.group(3)) if t else 10 ** 7
            rows.append((ep, secs, i, int(m.group(1))))
    rows.sort()
    old_ids = [r[3] for r in rows]
    if len(set(old_ids)) != len(old_ids):
        raise SystemExit("duplicate claim headers; aborting")
    mapping = {old: new for new, old in enumerate(old_ids, start=1)}
    ep_of = {r[3]: r[0] for r in rows}
    print(f"{len(mapping)} claims -> C-1..C-{len(mapping)}; unchanged ids: {sum(1 for o, n in mapping.items() if o == n)}")
    if a.dry_run:
        return 0

    def sub(m: re.Match) -> str:
        n = mapping.get(int(m.group(1)))
        return f"C-{n}" if n else m.group(0)

    files = [p for d in ("drafts", "inscription", "config") for p in (CKA / d).rglob("*") if p.is_file()
             and p.suffix in {".md", ".json", ".csv", ".txt", ".jsonl"}]
    files.append(MON / "scripts" / "hostile_hard_gates.py")
    if (CKA / "tweets" / "links.jsonl").exists():
        files.append(CKA / "tweets" / "links.jsonl")  # never tweets.jsonl: post text is verbatim
    unknown: set[str] = set()
    for p in files:
        is_draft = p.parent.name == "drafts" and re.fullmatch(r"episode_\d+\.md", p.name)
        raw = cs.read_draft_text(cs.seq_of(p)) if is_draft else p.read_text(encoding="utf-8")
        for m in TOKEN.finditer(raw):
            if int(m.group(1)) not in mapping and p.parent.name in ("drafts", "inscription"):
                unknown.add(f"{p.name}:C-{m.group(1)}")
        new = TOKEN.sub(sub, raw)
        if p.parent.name == "drafts" and p.name.startswith("episode_") and not p.name.startswith("episode_000"):
            ep = int(re.search(r"episode_(\d+)", p.name).group(1))
            ids = sorted(mapping[o] for o, e in ep_of.items() if e == ep)
            if ids:
                line = f"  - Claim Range: C-{ids[0]}–C-{ids[-1]}\n"
                if RANGE_LINE.search(new):
                    first = RANGE_LINE.search(new)
                    new = new[: first.start()] + line + RANGE_LINE.sub("", new[first.end():])
        if p.name == "hostile_accepted.json":
            new = re.sub(r'"CA_DEBT_CALLOUT": "[^"]*"',
                         '"CA_DEBT_CALLOUT": "Informational, not a defect: CKA claims were renumbered densely from C-1 in '
                         f'airing order on {a.date} (map in audits/claim_renumber_{a.date}/id_map.csv); artifact ids still '
                         'continue the BoC remap band (artifacts start at A-1077), so the leading artifact holes are expected."',
                         new)
        if new != raw:
            if is_draft:
                cs.write_draft_text(cs.seq_of(p), new)
            else:
                p.write_text(new, encoding="utf-8")
    out = CKA / "audits" / f"claim_renumber_{a.date}"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "id_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["old_id", "new_id", "episode"])
        for old in old_ids:
            w.writerow([f"C-{old}", f"C-{mapping[old]}", ep_of[old]])
    print(f"wrote {out / 'id_map.csv'}")
    if unknown:
        print(f"references to ids that are not claims (left as is): {sorted(unknown)[:20]} ({len(unknown)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
