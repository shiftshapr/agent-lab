#!/usr/bin/env python3
"""
Parse email-opportunity output and add opportunities to data/opportunities.json.

Extracts opportunities from logs/email_opportunity_YYYYMMDD.md.
Uses LLM (DeerFlow) to parse and extract structured entries when format is ambiguous.

Usage:
  python scripts/ledger-from-email.py
  python scripts/ledger-from-email.py logs/email_opportunity_20260319.md
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
LOGS_DIR = AGENT_LAB_ROOT / "logs"
LEDGER_PATH = AGENT_LAB_ROOT / "data" / "opportunities.json"


def load_ledger() -> dict:
    if not LEDGER_PATH.exists():
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        return {"schema_version": 1, "updated_at": None, "opportunities": []}
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def save_ledger(data: dict) -> None:
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _parse_deadline(text: str) -> str | None:
    """Extract YYYY-MM-DD from text."""
    # Common patterns
    for pat in [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{1,2}/\d{1,2}/\d{1,4})",
        r"(?:due|deadline|by)\s*[:\s]*(\d{0,2}\s+\w+\s+\d{4})",
        r"(\w+\s+\d{1,2},?\s+\d{4})",
    ]:
        m = re.search(pat, text, re.I)
        if m:
            s = m.group(1).strip()
            if re.match(r"\d{4}-\d{2}-\d{2}", s):
                return s
            for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y"]:
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return None


def run_deerflow_extract(content: str) -> list[dict]:
    """Use DeerFlow to extract structured opportunities from markdown."""
    prompt = """Extract opportunities (grants, fellowships, RFPs, partnerships) from this email opportunity report.

For each opportunity found, output a JSON object. Format each as: {"name": "...", "type": "grant|fellowship|rfp|partnership|other", "deadline": "YYYY-MM-DD or null", "notes": "..."}

If no deadline is mentioned, use null. Output only valid JSON, one object per line. No other text."""

    full_prompt = f"{prompt}\n\n---\n\n{content[:5000]}"

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "run-deerflow-task.py"), full_prompt, "--timeout", "120"],
            cwd=str(AGENT_LAB_ROOT),
            capture_output=True,
            text=True,
            timeout=130,
        )
    except subprocess.TimeoutExpired:
        return []
    if result.returncode != 0:
        return []

    parsed = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and obj.get("name"):
                parsed.append(obj)
        except json.JSONDecodeError:
            continue
    return parsed


def parse_markdown(content: str) -> list[dict]:
    """Simple parse of markdown list items."""
    opps = []
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("-"):
            continue
        # [Type] Subject — Sender, date — Why it matters
        m = re.match(r"-\s*\[?([^\]]+)\]?\s*(.+?)(?:\s|$)", line)
        if m:
            type_hint, rest = m.group(1).strip(), m.group(2).strip()
            type_map = {"grant": "grant", "fellowship": "fellowship", "rfp": "rfp", "partnership": "partnership"}
            t = "other"
            for k, v in type_map.items():
                if k in type_hint.lower():
                    t = v
                    break
            name = rest.split("—")[0].strip() if "—" in rest else rest[:80]
            deadline = _parse_deadline(rest) or _parse_deadline(line)
            opps.append({"name": name, "type": t, "deadline": deadline, "notes": rest[:200]})
    return opps


def merge_into_ledger(entries: list[dict], source: str = "email") -> int:
    """Merge entries into ledger. Returns count added."""
    data = load_ledger()
    existing_names = {o.get("name", "").lower() for o in data.get("opportunities", [])}
    added = 0

    for e in entries:
        name = (e.get("name") or "").strip()
        if not name or name.lower() in existing_names:
            continue
        if e.get("status") == "submitted":
            continue
        entry = {
            "id": f"{e.get('type', 'other')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "type": e.get("type", "other"),
            "deadline": e.get("deadline") or "",
            "source": source,
            "status": "open",
            "notes": (e.get("notes") or "")[:500],
            "added_at": datetime.utcnow().isoformat() + "Z",
        }
        data.setdefault("opportunities", []).append(entry)
        existing_names.add(name.lower())
        added += 1

    if added:
        save_ledger(data)
    return added


def main() -> None:
    # Find latest email opportunity file
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if path_arg:
        path = Path(path_arg) if Path(path_arg).is_absolute() else AGENT_LAB_ROOT / path_arg
    else:
        path = LOGS_DIR / f"email_opportunity_{datetime.now().strftime('%Y%m%d')}.md"
        if not path.exists():
            candidates = sorted(LOGS_DIR.glob("email_opportunity_*.md"), reverse=True)
            path = candidates[0] if candidates else None

    if not path or not path.exists():
        print("[ledger-from-email] No email opportunity file found", file=sys.stderr)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")

    # Try simple parse first
    entries = parse_markdown(content)
    if not entries:
        entries = run_deerflow_extract(content)

    added = merge_into_ledger(entries)
    print(f"[ledger-from-email] Added {added} from {path.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
