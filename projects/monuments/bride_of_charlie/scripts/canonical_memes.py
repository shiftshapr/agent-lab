"""
Canonical Meme / Euphemism / Code Dictionary

Shared across monuments. Used for meme analysis in episode extraction.

Usage:
  python scripts/canonical_memes.py add "term" --type meme --definition "..."
  python scripts/canonical_memes.py list
  python scripts/canonical_memes.py add "dog whistle" --type code --aliases "dw,dogwhistle"
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CANONICAL_DIR = PROJECT_DIR / "canonical"
MEMES_FILE = CANONICAL_DIR / "memes.json"


def _load() -> dict:
    if not MEMES_FILE.exists():
        return {
            "version": 1,
            "description": "Canonical dictionary of memes, euphemisms, and codes — shared across monuments",
            "updated": None,
            "next_id": 1,
            "entries": {},
            "types": {
                "meme": "Recurring image, phrase, or concept used as cultural shorthand",
                "euphemism": "Indirect or softened expression substituting for a blunt term",
                "code": "Deliberately obscure term or phrase with specific meaning to insiders",
            },
        }
    return json.loads(MEMES_FILE.read_text(encoding="utf-8"))


def _save(data: dict):
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now(timezone.utc).isoformat()
    MEMES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add(term: str, entry_type: str = "meme", definition: str = "", aliases: str = "", context: str = "") -> str:
    """Add or merge entry. Returns M-ID."""
    data = _load()
    entries = data.setdefault("entries", {})
    next_id = data.setdefault("next_id", 1)

    term = term.strip()
    if not term:
        raise ValueError("Term cannot be empty")

    # De-dup: exact match
    for mid, e in entries.items():
        if e.get("canonical_term", "").lower() == term.lower():
            return mid
        if term.lower() in [a.lower() for a in e.get("aliases", [])]:
            return mid

    mid = f"M-{next_id}"
    data["next_id"] = next_id + 1
    entries[mid] = {
        "canonical_term": term,
        "type": entry_type,
        "aliases": [a.strip() for a in aliases.split(",") if a.strip()] if aliases else [],
        "definition": definition,
        "context": context or "bride_of_charlie",
    }
    _save(data)
    return mid


def list_entries(entry_type: str | None = None) -> list[dict]:
    """List entries, optionally filtered by type."""
    data = _load()
    entries = list(data.get("entries", {}).items())
    if entry_type:
        entries = [(k, v) for k, v in entries if v.get("type") == entry_type]
    return [{"id": k, **v} for k, v in entries]


def main():
    ap = argparse.ArgumentParser(description="Canonical meme/euphemism/code dictionary")
    sub = ap.add_subparsers(dest="cmd")

    add_p = sub.add_parser("add", help="Add entry")
    add_p.add_argument("term", help="Canonical term")
    add_p.add_argument("--type", choices=["meme", "euphemism", "code"], default="meme")
    add_p.add_argument("--definition", default="")
    add_p.add_argument("--aliases", default="", help="Comma-separated")
    add_p.add_argument("--context", default="bride_of_charlie")

    list_p = sub.add_parser("list", help="List entries")
    list_p.add_argument("--type", choices=["meme", "euphemism", "code"], help="Filter by type")

    args = ap.parse_args()

    if args.cmd == "add":
        mid = add(args.term, args.type, args.definition, args.aliases, args.context)
        print(f"Added {mid}: {args.term}")

    elif args.cmd == "list":
        entries = list_entries(args.type)
        if not entries:
            print("No entries.")
            return
        for e in entries:
            print(f"  {e['id']} [{e.get('type', '?')}] {e.get('canonical_term', '')}")
            if e.get("aliases"):
                print(f"      aliases: {', '.join(e['aliases'])}")
            if e.get("definition"):
                print(f"      {e['definition'][:80]}...")
            print()

    else:
        ap.print_help()


if __name__ == "__main__":
    main()
