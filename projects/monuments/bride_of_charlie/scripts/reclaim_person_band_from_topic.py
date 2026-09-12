#!/usr/bin/env python3
"""
Dense Person intro-order reclaim: PR33 topic-band persons + cascade shift N-18..53.

Daveed lock: People N-1..N-999 dense by first-seen ep1→ep8; Topics N-1000+ only.

Applies from current PR34 branch state (five at N-54..58) to final dense N-1..58:
  ep2 insert Jill/Susan/John → N-18..20 (shift N-18..42 +3 → N-21..45)
  ep6 insert Hugo/Tracy → N-46..47 (shift N-43..53 +5 → N-48..58)

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

# Current PR34 branch person id → dense target (N-1..17 unchanged).
DENSE_REMAP: dict[str, str] = {
    "N-54": "N-18",
    "N-55": "N-19",
    "N-56": "N-20",
    "N-18": "N-21",
    "N-19": "N-22",
    "N-20": "N-23",
    "N-21": "N-24",
    "N-22": "N-25",
    "N-23": "N-26",
    "N-24": "N-27",
    "N-25": "N-28",
    "N-26": "N-29",
    "N-27": "N-30",
    "N-28": "N-31",
    "N-29": "N-32",
    "N-30": "N-33",
    "N-31": "N-34",
    "N-32": "N-35",
    "N-33": "N-36",
    "N-34": "N-37",
    "N-35": "N-38",
    "N-36": "N-39",
    "N-37": "N-40",
    "N-38": "N-41",
    "N-39": "N-42",
    "N-40": "N-43",
    "N-41": "N-44",
    "N-42": "N-45",
    "N-57": "N-46",
    "N-58": "N-47",
    "N-43": "N-48",
    "N-44": "N-49",
    "N-45": "N-50",
    "N-46": "N-51",
    "N-47": "N-52",
    "N-48": "N-53",
    "N-49": "N-54",
    "N-50": "N-55",
    "N-51": "N-56",
    "N-52": "N-57",
    "N-53": "N-58",
}

# Main-tip (5dd9893) misplaced topic-band ids → final dense targets.
PR33_TOPIC_BAND_REMAP: dict[str, str] = {
    "N-1067": "N-18",
    "N-1068": "N-19",
    "N-1069": "N-20",
    "N-1070": "N-46",
    "N-1071": "N-47",
}

# Pre-PR34 main-tip person ids → final (for retired ledger).
MAIN_TIP_PERSON_REMAP: dict[str, str] = {
    **PR33_TOPIC_BAND_REMAP,
    **{old: DENSE_REMAP[old] for old in DENSE_REMAP if old not in PR33_TOPIC_BAND_REMAP},
}

PERSON_NAMES: dict[str, str] = {
    "N-18": "Jill Kesler",
    "N-19": "Susan B. Silverstein",
    "N-20": "John Walton",
    "N-21": "Richard Erpenbeck",
    "N-22": "Tony Erpenbeck",
    "N-23": "Bill Erpenbeck",
    "N-24": "Gary Erpenbeck",
    "N-25": "Jeff Erpenbeck",
    "N-26": "Donna Erpenbeck",
    "N-27": "Pastor Terry Crist",
    "N-28": "Brian Houston",
    "N-29": "Jack Solomon",
    "N-30": "Vince Lombardi",
    "N-31": "Carla Solomon",
    "N-32": "James Melvin Stanley",
    "N-33": "John Robert Walstad",
    "N-34": "Angela Lombardo",
    "N-35": "Jeffrey Epstein",
    "N-36": "Deborah Himil",
    "N-37": "Nancy Gerard",
    "N-38": "Tyler Sanford",
    "N-39": "Dennis Frantzve",
    "N-40": "Curtis Kolvet",
    "N-41": "Robert Kolvet",
    "N-42": "Andrew Kolvet",
    "N-43": "Justin Strife",
    "N-44": "Charles Cookie Thornton",
    "N-45": "Rob McCoy",
    "N-46": "Hugo E. Salazar",
    "N-47": "Tracy Martin",
    "N-48": "Josh Harelson",
    "N-49": "JT Massie",
    "N-50": "Tucker Carlson",
    "N-51": "Cabot Phillips",
    "N-52": "Bishop Thomas J. O'Brien",
    "N-53": "Jim Lee Reed",
    "N-54": "Patricia Patrick",
    "N-55": "James Woolsey",
    "N-56": "Kanye West",
    "N-57": "Kouri Richins",
    "N-58": "Matt Walsh",
}

_ID_TOKEN = re.compile(r"(?<![A-Za-z0-9-])(N-\d+)(?![0-9])")


def _replace_ids(text: str, remap: dict[str, str]) -> str:
    """Two-phase replace to avoid chain collisions."""
    temp: dict[str, str] = {}
    for i, old in enumerate(remap):
        temp[old] = f"__PERSON_TMP_{i:03d}__"
    out = text
    for old, tmp in temp.items():
        out = _ID_TOKEN.sub(lambda m, o=old, t=tmp: t if m.group(1) == o else m.group(0), out)
    rev = {v: remap[k] for k, v in temp.items()}
    for tmp, new in rev.items():
        out = out.replace(tmp, new)
    return out


def _collect_text_files() -> list[Path]:
    candidates: list[Path] = []
    drafts = PROJECT / "drafts"
    if drafts.exists():
        candidates.extend(drafts.glob("*.md"))
    return sorted(set(candidates))


def _touch_text_files(dry_run: bool) -> list[str]:
    touched: list[str] = []
    for path in _collect_text_files():
        if "drafts_backup" in str(path):
            continue
        original = path.read_text(encoding="utf-8")
        updated = _replace_ids(original, DENSE_REMAP)
        if updated != original:
            touched.append(str(path.relative_to(PROJECT)))
            if not dry_run:
                path.write_text(updated, encoding="utf-8")
    return touched


def _update_canonical(dry_run: bool) -> None:
    nodes_path = PROJECT / "canonical" / "nodes.json"
    data = json.loads(nodes_path.read_text(encoding="utf-8"))
    nodes = data["nodes"]
    new_nodes: dict = {}
    persons: dict[str, dict] = {}

    for key, entry in nodes.items():
        if entry.get("type") == "person":
            persons[key] = entry
        else:
            new_nodes[key] = entry

    for old_key, entry in persons.items():
        new_key = DENSE_REMAP.get(old_key, old_key)
        if new_key in new_nodes and new_nodes[new_key].get("type") == "person":
            raise ValueError(f"duplicate person target {new_key} from {old_key}")
        new_nodes[new_key] = entry

    data["nodes"] = new_nodes
    data["next_person_id"] = 59
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not dry_run:
        nodes_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _update_retired(dry_run: bool) -> None:
    retired_path = PROJECT / "config" / "retired_node_ids.json"
    data = json.loads(retired_path.read_text(encoding="utf-8"))
    retired = data["retired"]

    pr33_chain = {
        "legacy-N-1063": "N-18",
        "legacy-N-1064": "N-19",
        "legacy-N-1065": "N-20",
        "legacy-N-1067": "N-46",
        "legacy-N-1068": "N-47",
    }
    for key, target in pr33_chain.items():
        if key in retired:
            retired[key]["survives_as"] = target
            retired[key]["reason"] = (
                retired[key]["reason"].split("; reclaimed")[0].split("; dense")[0]
                + f"; dense Person intro-order final {target} (Daveed lock)."
            )

    for old, new in PR33_TOPIC_BAND_REMAP.items():
        tomb = f"pr33-person-{old}"
        retired[tomb] = {
            "survives_as": new,
            "canonical_name": PERSON_NAMES[new],
            "reason": "PR33 misplaced Person in Topic band; dense intro-order reclaim (Daveed lock).",
        }

    for old, new in DENSE_REMAP.items():
        if old in PR33_TOPIC_BAND_REMAP.values():
            continue
        name = PERSON_NAMES.get(new, retired.get(f"pr34-dense-{old}", {}).get("canonical_name", ""))
        if not name and old.startswith("N-"):
            # lookup from canonical name map via inverse
            pass
        retired[f"pr34-dense-{old}"] = {
            "survives_as": new,
            "canonical_name": PERSON_NAMES[new],
            "reason": f"PR34 dense intro-order shift; was {old} before cascade.",
        }

    for old, new in MAIN_TIP_PERSON_REMAP.items():
        if int(old.split("-")[1]) >= 1000:
            continue
        if old == new:
            continue
        key = f"pr34-main-{old}"
        if key not in retired:
            retired[key] = {
                "survives_as": new,
                "canonical_name": PERSON_NAMES[new],
                "reason": f"Main-tip person id {old} → dense intro-order {new} (PR34).",
            }

    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data["description"] = (
        "Tombstone ledger: Person N-1..N-999 dense intro-order; Topic/Org/Place N-1000+ only."
    )
    if not dry_run:
        retired_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dense Person intro-order reclaim")
    parser.add_argument("--apply", action="store_true")
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

    print("\nDense remap (PR34 branch old → new):")
    for old in sorted(DENSE_REMAP, key=lambda x: int(x.split("-")[1])):
        print(f"  {old} → {DENSE_REMAP[old]}  ({PERSON_NAMES[DENSE_REMAP[old]]})")

    if dry_run:
        print("\nDry-run only. Re-run with --apply.")


if __name__ == "__main__":
    main()
