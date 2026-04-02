#!/usr/bin/env python3
"""
One-shot: replace NODE_* in inscription JSON string fields with N-* (numeric suffix preserved).

Legacy files may still have NODE_* inside node.related_nodes. Future assign_ids runs fix this
via apply_ids_to_json.

Usage:
  python3 scripts/fix_inscription_node_placeholders.py
  python3 scripts/fix_inscription_node_placeholders.py --dry-run
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
NODE_RE = re.compile(r"\bNODE_(\d+)\b")


def sub_node(m: re.Match[str]) -> str:
    return f"N-{m.group(1)}"


def fix_value(v: object) -> object:
    if isinstance(v, str):
        return NODE_RE.sub(sub_node, v)
    if isinstance(v, dict):
        return {k: fix_value(x) for k, x in v.items()}
    if isinstance(v, list):
        return [fix_value(x) for x in v]
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for jpath in sorted((PROJECT_DIR / "inscription").glob("episode_*.json")):
        if not re.match(r"episode_\d{3}\.json$", jpath.name):
            continue
        data = json.loads(jpath.read_text(encoding="utf-8"))
        new_data = fix_value(copy.deepcopy(data))
        if json.dumps(data, sort_keys=True) != json.dumps(new_data, sort_keys=True):
            print(f"[fix] {jpath.relative_to(PROJECT_DIR)}: rewriting NODE_ -> N-")
            if not args.dry_run:
                jpath.write_text(json.dumps(new_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
