#!/usr/bin/env python3
"""Copy each draft claim's `Tags:` line (e.g. relevance:core) into its inscription claim `tags` list.

The inscription builder fills claim `tags` from sensitive-topic tags only, so the relevance tags written in the
drafts did not reach the inscriptions. This adds every draft tag that the inscription claim lacks, keeping the
existing tags and their order; it never removes a tag. A rerun is a no-op.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/sync_claim_tags.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CKA.parent / "bride_of_charlie" / "scripts"))
from neo4j_ingest import extract_claims  # noqa: E402  (the one draft parser, ROADMAP 0.7)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    added = files = 0
    for dpath in sorted((CKA / "drafts").glob("episode_*.md")):
        ipath = CKA / "inscription" / dpath.name.replace(".md", ".json")
        if not ipath.exists():
            continue
        tags = {c["id"]: c["tags"] for c in extract_claims(dpath.read_text(encoding="utf-8"), 0)}
        raw = ipath.read_text(encoding="utf-8")
        data = json.loads(raw)
        n = 0
        for c in data.get("claims", []):
            want = tags.get(c.get("ref"), [])
            have = c.get("tags") or []
            new = [t for t in want if t not in have]
            if new:
                c["tags"] = have + new
                n += len(new)
        if n:
            added += n
            files += 1
            if not args.dry_run:
                ipath.write_text(json.dumps(data, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    print(f"added {added} tags across {files} inscription files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
