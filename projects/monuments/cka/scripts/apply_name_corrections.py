#!/usr/bin/env python3
"""Apply config/transcript_name_corrections.json everywhere a mis-transcribed name can live.

Ruling (Daveed 2026-10-14): a mis-transcribed name is not an alias and must not survive anywhere, including
transcript snippets and meme quotes. Because snippets are checked as verbatim substrings of
transcripts_corrected/, the same corrections are applied to the transcripts, the drafts (every line) and the
inscriptions (every string), so snippets stay verbatim. Node aliases that a correction rewrites are dropped from
canonical/nodes.json. Run it on every new transcript before extraction. A rerun is a no-op.

A rule is [pattern, replacement] (archive-wide) or [pattern, replacement, [seq, ...]] (only those episodes'
transcript, draft and inscription). Scope a rule whenever the wrong rendering is itself a real name or an ordinary
word elsewhere ("Frank Church", "Andrew Klavan", "scientists"). Node names and aliases use archive-wide rules only.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/apply_name_corrections.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "source"))
import cka_source as cs  # noqa: E402  (ROADMAP 3.0: episodes are read and written through the JSON source)

CKA = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    rules = [(re.compile(r[0]), r[1], set(r[2]) if len(r) > 2 else None) for r in
             json.loads((CKA / "config" / "transcript_name_corrections.json").read_text(encoding="utf-8"))["corrections"]]

    def fix(s: str, ep: int | None = None) -> str:
        for rx, b, eps in rules:
            if eps is None or (ep is not None and ep in eps):
                s = rx.sub(b, s)
        return s

    def ep_of(p: Path) -> int | None:
        m = re.match(r"episode_(\d{3})", p.name)
        return int(m.group(1)) if m else None

    changed = {"transcripts": 0, "drafts": 0, "inscriptions": 0, "aliases": 0}
    for key, pattern in (("transcripts", "transcripts_corrected/episode_*"), ("drafts", "drafts/episode_*.md")):
        for p in sorted(CKA.glob(pattern)):
            t = cs.read_draft_text(cs.seq_of(p)) if key == "drafts" else p.read_bytes().decode("utf-8")
            t2 = fix(t, ep_of(p))
            if t2 != t:
                changed[key] += 1
                if not args.dry_run:
                    if key == "drafts":
                        cs.write_draft_text(cs.seq_of(p), t2)
                    else:
                        p.write_bytes(t2.encode("utf-8"))
    for p in sorted((CKA / "inscription").glob("*.json")):
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
        ep = ep_of(p)

        def walk(x):
            if isinstance(x, dict):
                return {k: walk(v) for k, v in x.items()}
            if isinstance(x, list):
                return [walk(i) for i in x]
            return fix(x, ep) if isinstance(x, str) else x
        new = walk(data)
        if new != data:
            changed["inscriptions"] += 1
            if not args.dry_run:
                p.write_text(json.dumps(new, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    npath = CKA / "canonical" / "nodes.json"
    raw = npath.read_text(encoding="utf-8")
    ndata = json.loads(raw)
    for v in ndata["nodes"].values():
        keep = [a for a in v.get("aliases", []) if fix(a) == a]
        changed["aliases"] += len(v.get("aliases", [])) - len(keep)
        v["aliases"] = keep
        v["canonical_name"] = fix(v["canonical_name"])
    if not args.dry_run:
        npath.write_text(json.dumps(ndata, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    print(", ".join(f"{k}: {v}" for k, v in changed.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
