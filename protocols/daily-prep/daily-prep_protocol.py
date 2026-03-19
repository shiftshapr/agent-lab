"""
Daily Prep Protocol
Produces a morning brief: calendar, emails needing attention, to-dos.

Uses DeerFlow agent (Zoho View MCP) for calendar and email.
Output: logs/daily_prep_YYYYMMDD.md
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = AGENT_LAB_ROOT / "scripts"
LOGS_DIR = AGENT_LAB_ROOT / "logs"


def run_daily_prep_protocol() -> None:
    """Run daily prep: calendar + email summary."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = LOGS_DIR / f"daily_prep_{datetime.now().strftime('%Y%m%d')}.md"

    prompt = f"""Prepare my daily brief for {date_str}.

1. **Calendar**: List today's meetings and events. For each meeting, provide a 1–2 sentence briefing.
2. **Emails**: Summarize unread or important emails that need my attention today. Flag any that need a response.
3. **To-dos**: If you have access to a task queue, list priority items.

Be concise. Output in markdown."""

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "run-deerflow-task.py"), prompt, "--output", str(output_path)],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"[daily-prep] Brief saved to {output_path}")


if __name__ == "__main__":
    run_daily_prep_protocol()
