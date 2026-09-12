#!/usr/bin/env python3
"""
Reclaim five Persons misplaced in Topic band (N-1067..N-1071) into Person band N-54..N-58.

Daveed lock: People = N-1..N-999; Topics/Orgs/Places = N-1000+.
Run from repo root after checkout on main tip.

Usage:
  python projects/monuments/bride_of_charlie/scripts/reclaim_person_band_from_topic.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

# First-introduction order ep1→ep8 (all after Matt Walsh N-53).
PERSON_REMAP: dict[str, str] = {
    "N-1067": "N-54",  # Jill Kesler — ep 2
    "N-1068": "N-55",  # Susan B. Silverstein — ep 2
    "N-1069": "N-56",  # John Walton — ep 2
    "N-1070": "N-57",  # Hugo E. Salazar — ep 6
    "N-1071": "N-58",  # Tracy Martin — ep 6
}

PERSON_NAMES: dict[str, str] = {
    "N-54": "Jill Kesler",
    "N-55": "Susan B. Silverstein",
    "N-56": "John Walton",
    "N-57": "Hugo E. Salazar",
    "N-58": "Tracy Martin",
}

# Files that receive global N-ID substitution (not retired ledger — handled separately).
TEXT_GLOB_DIRS = [
    PROJECT / "drafts",
    PROJECT / "scripts",
]
TEXT_GLOB_FILES: list[Path] = []

RETIRED_CHAIN_UPDATES: dict[str, str] = {
    "legacy-N-1063": "N-54",
    "legacy-N-1064": "N-55",
    "legacy-N-1065": "N-56",
    "legacy-N-1067": "N-57",
    "legacy-N-1068": "N-58",
}


def _replace_ids(text: str) -> str:
    """Replace old person IDs; highest numbers first."""
    for old in sorted(PERSON_REMAP, key=lambda x: int(x.split("-")[1]), reverse=True):
        new = PERSON_REMAP[old]
        text = re.sub(rf"(?<![A-Za-z0-9-]){re.escape(old)}(?![0-9])", new, text)
    return text


def _touch_text_files(dry_run: bool) -> list[str]:
    touched: list[str] = []
    candidates: list[Path] = []
    for d in TEXT_GLOB_DIRS:
        if d.exists():
            candidates.extend(d.rglob("*.md"))
            candidates.extend(d.rglob("*.py"))
    candidates.extend(TEXT_GLOB_FILES)

    seen: set[Path] = set()
    for path in sorted(candidates):
        if path.name == Path(__file__).name or path in seen:
            continue
        seen.add(path)
        if "drafts_backup" in str(path):
            continue
        original = path.read_text(encoding="utf-8")
        updated = _replace_ids(original)
        if updated != original:
            touched.append(str(path.relative_to(PROJECT)))
            if not dry_run:
                path.write_text(updated, encoding="utf-8")
    return touched


def _update_canonical(dry_run: bool) -> None:
    nodes_path = PROJECT / "canonical" / "nodes.json"
    data = json.loads(nodes_path.read_text(encoding="utf-8"))
    nodes = data["nodes"]

    for old, new in PERSON_REMAP.items():
        if old not in nodes:
            raise KeyError(f"missing {old} in canonical/nodes.json")
        entry = nodes.pop(old)
        if entry.get("type") != "person":
            raise ValueError(f"{old} is not type person: {entry}")
        nodes[new] = {
            "canonical_name": entry["canonical_name"],
            "type": "person",
            "aliases": entry.get("aliases", []),
        }

    data["next_person_id"] = 59
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not dry_run:
        nodes_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _update_retired(dry_run: bool) -> None:
    retired_path = PROJECT / "config" / "retired_node_ids.json"
    data = json.loads(retired_path.read_text(encoding="utf-8"))
    retired = data["retired"]

    for key, new_survives in RETIRED_CHAIN_UPDATES.items():
        if key not in retired:
            raise KeyError(f"missing {key} in retired_node_ids.json")
        retired[key]["survives_as"] = new_survives
        retired[key]["reason"] = (
            retired[key]["reason"].split("; was ")[0]
            + f"; reclaimed to Person band {new_survives} (Daveed lock)."
        )

    now_reason = "PR33 misplaced Person in Topic band; reclaimed to Person band (Daveed lock)."
    for old, new in PERSON_REMAP.items():
        tomb_key = f"pr33-person-{old}"
        retired[tomb_key] = {
            "survives_as": new,
            "canonical_name": PERSON_NAMES[new],
            "reason": now_reason,
        }

    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["description"] = (
        "Tombstone ledger for legacy N-IDs after intro-order renumber "
        "(N-1..N-999 Person dense; N-1000+ Topic/Org/Place only)."
    )
    if not dry_run:
        retired_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reclaim Person band from Topic band misplacements")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = parser.parse_args()
    dry_run = not args.apply

    touched = _touch_text_files(dry_run)
    print(f"Text files {'would be ' if dry_run else ''}updated: {len(touched)}")
    for t in touched:
        print(f"  {t}")

    _update_canonical(dry_run)
    print("canonical/nodes.json OK")

    _update_retired(dry_run)
    print("config/retired_node_ids.json OK")

    print("\nPerson map (old → new):")
    for old, new in PERSON_REMAP.items():
        print(f"  {old} → {new}  ({PERSON_NAMES[new]})")

    if dry_run:
        print("\nDry-run only. Re-run with --apply to write.")


if __name__ == "__main__":
    main()
