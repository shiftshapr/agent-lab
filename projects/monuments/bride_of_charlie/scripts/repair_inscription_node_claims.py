#!/usr/bin/env python3
"""
Repair node↔claim edges in inscription/episode_*.json to match hub policy.

Applies ``sanitize_node_claim_graph_final`` (same rules as Phase-2 ``assign_ids`` + ``node_claim_sync``):

- **Errors** (``node_claim_subject_mismatch``): Remove ``nodes[].related_claims`` entries where the claim
  exists and has a non-empty ``related_nodes`` that does not include this node.
- **Warnings** (``claim_node_backlink_missing``): Append the claim id to each node's ``related_claims``
  when the claim lists that node in ``related_nodes``.

- **Dangling refs** (``node_claim_missing`` / bad artifact links): Remove ``related_claims`` entries on
  nodes and artifact sub-items when that claim id is not present in the file's ``claims[]``.

Usage:
  cd ~/workspace/agent-lab
  python3 projects/monuments/bride_of_charlie/scripts/repair_inscription_node_claims.py

  --dry-run          Print what would change, do not write files
  --episode N        Only episode N (repeatable); default: all episode_*.json
  --no-backlinks     Only drop mismatched edges; do not add reverse edges (warnings may remain)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INSCRIPTION_DIR = PROJECT_DIR / "inscription"
AGENT_LAB_ROOT = PROJECT_DIR.parent.parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Repair inscription node↔claim graph")
    ap.add_argument(
        "--inscription",
        type=Path,
        default=INSCRIPTION_DIR,
        help="Directory containing episode_NNN.json",
    )
    ap.add_argument(
        "--episode",
        type=int,
        action="append",
        dest="episodes",
        metavar="N",
        help="Restrict to episode N (may be repeated)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Log changes only; do not write files",
    )
    ap.add_argument(
        "--no-backlinks",
        action="store_true",
        help="Omit claim→node backlink additions",
    )
    ap.add_argument(
        "--validate-after",
        action="store_true",
        default=True,
        help="Run screen_node_claim_consistency after writes (default: on)",
    )
    ap.add_argument(
        "--no-validate-after",
        action="store_false",
        dest="validate_after",
        help="Skip post-repair validation",
    )
    args = ap.parse_args()

    ins_dir = args.inscription.resolve()
    if not ins_dir.is_dir():
        print(f"[repair] Not a directory: {ins_dir}", file=sys.stderr)
        return 1

    if str(AGENT_LAB_ROOT) not in sys.path:
        sys.path.insert(0, str(AGENT_LAB_ROOT))

    from protocols.episode_analysis.node_claim_sync import sanitize_node_claim_graph_final

    want_eps = set(args.episodes) if args.episodes else None
    paths = sorted(
        p
        for p in ins_dir.glob("episode_*.json")
        if p.is_file() and "readme" not in p.name.lower()
    )
    if want_eps is not None:
        paths = [p for p in paths if _episode_from_name(p.name) in want_eps]

    if not paths:
        print("[repair] No matching episode_*.json files.")
        return 1

    total_changes = 0
    for p in paths:
        ep = _episode_from_name(p.name)
        raw = p.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"[repair] SKIP {p.name}: JSON error: {e}", file=sys.stderr)
            return 1
        if not isinstance(data, dict):
            print(f"[repair] SKIP {p.name}: root is not an object", file=sys.stderr)
            return 1

        log = sanitize_node_claim_graph_final(
            data, add_claim_backlinks=not args.no_backlinks
        )
        if log:
            print(f"[repair] episode_{ep:03d} ({p.name}): {len(log)} change(s)")
            for line in log[:15]:
                print(f"  {line}")
            if len(log) > 15:
                print(f"  ... and {len(log) - 15} more")
            total_changes += len(log)
        else:
            print(f"[repair] episode_{ep:03d} ({p.name}): no changes")

        if not args.dry_run and log:
            p.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    if args.dry_run:
        print(f"[repair] dry-run: would apply {total_changes} change(s) across {len(paths)} file(s)")
    else:
        print(f"[repair] wrote {len(paths)} file(s); {total_changes} total change line(s)")

    if args.validate_after and not args.dry_run:
        try:
            from apps.draft_editor import bride_hub as bh
        except ImportError as e:
            print(f"[repair] validate-after skipped: {e}", file=sys.stderr)
            return 0
        out = bh.screen_node_claim_consistency(
            PROJECT_DIR, include_backlinks=not args.no_backlinks
        )
        err_n = int(out.get("error_count") or 0)
        warn_n = int(out.get("warning_count") or 0)
        print(
            f"[repair] post-check: ok={out.get('ok')} errors={err_n} warnings={warn_n}"
        )
        if err_n > 0:
            return 1
    return 0


def _episode_from_name(name: str) -> int:
    import re

    m = re.search(r"episode_(\d+)", name, re.I)
    return int(m.group(1)) if m else 0


if __name__ == "__main__":
    raise SystemExit(main())
