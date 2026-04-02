#!/usr/bin/env python3
"""
Append work_log entries (ingest=true) from data/master_calendar.json into
knowledge/work_log_digest.md for Neo4j ingest. Idempotent via HTML comment markers.

Usage (from agent-lab root):
  uv run python scripts/sweep-work-log-ingest.py
  uv run python scripts/sweep-work-log-ingest.py --dry-run
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
CALENDAR_PATH = AGENT_LAB_ROOT / "data" / "master_calendar.json"
DIGEST_PATH = AGENT_LAB_ROOT / "knowledge" / "work_log_digest.md"
MARKER_PREFIX = "<!-- wl-id:"


def main() -> int:
    dry = "--dry-run" in sys.argv
    if not CALENDAR_PATH.exists():
        print(f"[sweep-work-log] No calendar file: {CALENDAR_PATH}")
        return 1

    data = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    work_log = data.get("work_log") or []
    if not isinstance(work_log, list):
        print("[sweep-work-log] work_log is not a list")
        return 1

    existing = ""
    if DIGEST_PATH.exists():
        existing = DIGEST_PATH.read_text(encoding="utf-8")

    appended = 0
    blocks: list[str] = []

    # Oldest first so reading order matches time (list is newest-first in store)
    for entry in reversed(work_log):
        if not isinstance(entry, dict):
            continue
        if entry.get("ingest") is False:
            continue
        eid = str(entry.get("id") or "").strip()
        if not eid:
            continue
        marker = f"{MARKER_PREFIX}{eid} -->"
        if marker in existing:
            continue

        logged = entry.get("logged_at") or entry.get("created_at") or ""
        status = entry.get("status") or "note"
        text = (entry.get("text") or "").strip()
        if not text:
            continue

        lines = [
            f"## Work log {logged} — {status}",
            "",
            text,
            "",
        ]
        atts = entry.get("attachments") or []
        if isinstance(atts, list) and atts:
            lines.append("### Links and paths")
            lines.append("")
            for a in atts:
                if isinstance(a, dict):
                    v = (a.get("value") or "").strip()
                    if v:
                        lines.append(f"- {v}")
                elif isinstance(a, str) and a.strip():
                    lines.append(f"- {a.strip()}")
            lines.append("")

        lines.append(marker)
        lines.append("")
        blocks.append("\n".join(lines))
        appended += 1

    if not blocks:
        print("[sweep-work-log] Nothing new to append (all ingested ids present or empty).")
        return 0

    combined = "\n".join(blocks)
    if dry:
        print(f"[sweep-work-log] DRY RUN — would append {appended} section(s):\n")
        print(combined[:2000] + ("…" if len(combined) > 2000 else ""))
        return 0

    DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DIGEST_PATH.exists():
        header = (
            "# Work log digest\n\n"
            "Auto-appended from `data/master_calendar.json` work_log by "
            "`scripts/sweep-work-log-ingest.py`. Ingest into graph with:\n\n"
            "```bash\n"
            "uv run --project framework/deer-flow/backend python scripts/"
            "ingest-meta-layer-knowledge.py --file knowledge/work_log_digest.md\n"
            "```\n\n"
        )
        DIGEST_PATH.write_text(header + "\n", encoding="utf-8")

    with DIGEST_PATH.open("a", encoding="utf-8") as f:
        f.write(combined)

    print(f"[sweep-work-log] Appended {appended} section(s) to {DIGEST_PATH.relative_to(AGENT_LAB_ROOT)}")
    print(
        "Next: uv run --project framework/deer-flow/backend python scripts/"
        "ingest-meta-layer-knowledge.py --file knowledge/work_log_digest.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
