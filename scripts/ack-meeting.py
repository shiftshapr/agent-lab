#!/usr/bin/env python3
"""
Mark a meeting as acknowledged (skip 5-min escalation).

Usage:
  python scripts/ack-meeting.py "Standup"
  python scripts/ack-meeting.py "09:30 | Standup"
  echo "Standup" | python scripts/ack-meeting.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
LOGS_DIR = AGENT_LAB_ROOT / "logs"
STATE_FILE = LOGS_DIR / "meeting_reminder_state.json"


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def ack(title_or_key: str) -> bool:
    """Mark matching meeting(s) as acked. Returns True if any matched."""
    state = load_state()
    title_lower = title_or_key.strip().lower()
    matched = False

    for key in list(state.keys()):
        if key.startswith("_"):
            continue
        entry = state[key]
        if not isinstance(entry, dict):
            continue
        # Key format: "HH:MM|Title"
        if "|" in key:
            _, title = key.split("|", 1)
        else:
            title = key
        if title_lower in title.lower() or title_or_key.strip() in key:
            entry["acked"] = True
            matched = True
            print(f"[ack] Marked as acked: {title}", file=sys.stderr)

    if matched:
        save_state(state)
    return matched


def main() -> None:
    if len(sys.argv) > 1:
        arg = " ".join(sys.argv[1:])
    else:
        arg = sys.stdin.read().strip() if not sys.stdin.isatty() else ""

    if not arg:
        print("Usage: ack-meeting.py 'Meeting Title'", file=sys.stderr)
        sys.exit(1)

    if ack(arg):
        sys.exit(0)
    else:
        print(f"[ack] No matching meeting found for: {arg}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
