#!/usr/bin/env python3
"""
Validate nodes[].related_claims vs claims[].related_nodes for inscription/ JSON.

Uses agent-lab ``apps.draft_editor.bride_hub.screen_node_claim_consistency`` (same as
Draft Editor ``GET /api/bride/hub/validate-node-claims``).

Exit codes:
  0 — no errors (warnings allowed unless --strict-warnings)
  1 — one or more errors (node_claim_subject_mismatch, missing ids, etc.)
  2 — warnings only and --strict-warnings

Usage:
  cd ~/workspace/agent-lab
  uv run --project framework/deer-flow/backend \\
    python projects/monuments/bride_of_charlie/scripts/validate_inscription_node_claims.py

  --no-backlinks     Omit claim_node_backlink_missing warnings (faster triage on errors)
  --strict-warnings  Exit 2 if any warning (e.g. missing reverse edges)
  --json             Print full report JSON to stdout
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# agent-lab repo root (…/agent-lab)
AGENT_LAB_ROOT = Path(__file__).resolve().parents[4]
BRIDE_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate inscription node↔claim consistency")
    ap.add_argument(
        "--project",
        type=Path,
        default=BRIDE_ROOT,
        help="Bride of Charlie project root (default: beside this script)",
    )
    ap.add_argument(
        "--no-backlinks",
        action="store_true",
        help="Do not report claim→node backlink warnings",
    )
    ap.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Non-zero exit if any warning remains",
    )
    ap.add_argument("--json", action="store_true", help="Print full JSON report")
    args = ap.parse_args()

    if str(AGENT_LAB_ROOT) not in sys.path:
        sys.path.insert(0, str(AGENT_LAB_ROOT))
    try:
        from apps.draft_editor import bride_hub as bh
    except ImportError as e:
        print(f"[validate] Cannot import bride_hub: {e}", file=sys.stderr)
        print(f"[validate] AGENT_LAB_ROOT={AGENT_LAB_ROOT}", file=sys.stderr)
        return 1

    bride = args.project.resolve()
    if not bride.is_dir():
        print(f"[validate] Not a directory: {bride}", file=sys.stderr)
        return 1

    out = bh.screen_node_claim_consistency(
        bride, include_backlinks=not args.no_backlinks
    )
    if args.json:
        print(json.dumps(out, indent=2, default=str))

    err_n = int(out.get("error_count") or 0)
    warn_n = int(out.get("warning_count") or 0)

    if not args.json:
        print(
            f"[validate] ok={out.get('ok')} errors={err_n} warnings={warn_n} "
            f"project={bride}"
        )
        by_kind = out.get("by_kind") or {}
        if by_kind:
            print(f"[validate] by_kind: {by_kind}")

    if err_n > 0:
        return 1
    if args.strict_warnings and warn_n > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
