#!/usr/bin/env python3
"""
Add or update an opportunity in data/opportunities.json.

Usage:
  python scripts/ledger-add.py "Grant Name" --type grant --deadline 2025-04-15
  python scripts/ledger-add.py "Fellowship X" -t fellowship -d 2025-03-31 --notes "From email"
  python scripts/ledger-add.py "RFP" -t rfp -d 2025-05-01 --source email
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
LEDGER_PATH = AGENT_LAB_ROOT / "data" / "opportunities.json"

TYPES = ["grant", "fellowship", "rfp", "partnership", "speaking", "other"]


def load_ledger() -> dict:
    if not LEDGER_PATH.exists():
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        return {"schema_version": 1, "updated_at": None, "opportunities": []}
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def save_ledger(data: dict) -> None:
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add(name: str, type_: str, deadline: str, source: str = "manual", notes: str = "", status: str = "open") -> None:
    """Add or update opportunity. Returns id if updated."""
    data = load_ledger()
    opps = data.get("opportunities", [])

    # Parse deadline
    try:
        dt = datetime.strptime(deadline.strip(), "%Y-%m-%d")
        deadline_str = dt.strftime("%Y-%m-%d")
    except ValueError:
        deadline_str = deadline.strip()

    entry = {
        "id": f"{type_}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "name": name.strip(),
        "type": type_.lower() if type_.lower() in TYPES else "other",
        "deadline": deadline_str,
        "source": source,
        "status": status,
        "notes": notes.strip(),
        "added_at": datetime.utcnow().isoformat() + "Z",
    }

    # Check for existing by name
    for i, o in enumerate(opps):
        if o.get("name", "").lower() == name.strip().lower():
            entry["id"] = o.get("id", entry["id"])
            entry["added_at"] = o.get("added_at", entry["added_at"])
            opps[i] = entry
            save_ledger(data)
            print(f"[ledger] Updated: {name}", file=sys.stderr)
            return

    opps.append(entry)
    data["opportunities"] = opps
    save_ledger(data)
    print(f"[ledger] Added: {name} ({entry['id']})", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="Opportunity name")
    parser.add_argument("--type", "-t", choices=TYPES, default="other", help="Type")
    parser.add_argument("--deadline", "-d", required=True, help="Deadline YYYY-MM-DD")
    parser.add_argument("--source", "-s", default="manual", help="Source (manual, email)")
    parser.add_argument("--notes", "-n", default="", help="Notes")
    parser.add_argument("--status", default="open", choices=["open", "submitted", "passed"], help="Status")
    args = parser.parse_args()

    add(args.name, args.type, args.deadline, args.source, args.notes, args.status)


if __name__ == "__main__":
    main()
