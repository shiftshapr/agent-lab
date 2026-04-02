#!/usr/bin/env python3
"""
Record "this is wrong" in a durable place.

Appends:
  - canonical/name_issues.jsonl  (one JSON object per line)
  - docs/NAME_ISSUES.md        (bullet under ## Open flags)

Usage:
  cd projects/monuments/bride_of_charlie
  uv run --project ../../../framework/deer-flow/backend python scripts/flag_issue.py \\
    "Kent Bronze is not Kent Frantzve" --where "N-14 episode_001 draft + Neo4j merge"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DOCS_ISSUES = PROJECT_DIR / "docs" / "NAME_ISSUES.md"
JSONL = PROJECT_DIR / "canonical" / "name_issues.jsonl"

MARKER = "<!-- flag_issue.py appends below this line -->"


def main() -> int:
    ap = argparse.ArgumentParser(description='Flag "this is wrong" for Bride of Charlie')
    ap.add_argument("message", help="What is wrong (short, human)")
    ap.add_argument(
        "--where",
        default="",
        help="N-id, file, graph, transcript, etc.",
    )
    ap.add_argument(
        "--scope",
        default="name",
        choices=("name", "claim", "artifact", "ingest", "transcript", "other"),
        help="Rough category",
    )
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec = {
        "timestamp": ts,
        "scope": args.scope,
        "message": args.message.strip(),
        "where": (args.where or "").strip(),
        "status": "open",
    }

    JSONL.parent.mkdir(parents=True, exist_ok=True)
    with JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    where_bit = f" — _{rec['where']}_" if rec["where"] else ""
    bullet = f"- **{ts}** `[{rec['scope']}]` {rec['message']}{where_bit}\n"

    if not DOCS_ISSUES.exists():
        DOCS_ISSUES.write_text(
            f"# This is wrong\n\n## Open flags\n\n{MARKER}\n\n{bullet}\n",
            encoding="utf-8",
        )
        print(f"✓ {JSONL}")
        print(f"✓ {DOCS_ISSUES}")
        return 0

    text = DOCS_ISSUES.read_text(encoding="utf-8")
    if MARKER in text:
        text = text.replace(MARKER, MARKER + "\n\n" + bullet, 1)
    else:
        text = text.rstrip() + f"\n\n## Open flags\n\n{MARKER}\n\n{bullet}\n"
    DOCS_ISSUES.write_text(text, encoding="utf-8")
    print(f"✓ {JSONL}")
    print(f"✓ {DOCS_ISSUES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
