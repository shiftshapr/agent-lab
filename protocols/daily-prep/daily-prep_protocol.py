"""
Daily Prep Protocol
Produces a morning brief: calendar, emails needing attention, to-dos.

Uses DeerFlow agent (Zoho View MCP) for calendar and email.
Output: logs/daily_prep_YYYYMMDD.md
"""

from __future__ import annotations

import os
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

**IMPORTANT**: You have Zoho View MCP tools (zoho-view_*) for calendar and email. Call these tools first to fetch real data. Do not say you lack access until you have attempted to use them.

1. **Calendar**: Use Zoho View MCP to list today's meetings and events. For each meeting, provide a 1–2 sentence briefing.
2. **Emails**: Use Zoho View MCP to search unread/important emails. Summarize what needs my attention today. Flag any that need a response.
3. **To-dos**: If you have access to a task queue, list priority items.

Be concise. Output in markdown. Only if the Zoho tools fail or return errors, say so and offer to format manually provided details."""

    timeout = int(os.environ.get("DAILY_PREP_TIMEOUT", "420"))  # 7 min for cold start + MCP
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "run-deerflow-task.py"),
                prompt,
                "--output",
                str(output_path),
                "--timeout",
                str(timeout),
            ],
            cwd=str(AGENT_LAB_ROOT),
            capture_output=False,
            timeout=timeout + 30,
        )
    except subprocess.TimeoutExpired:
        print(f"[daily-prep] Timed out after {timeout}s", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"[daily-prep] Brief saved to {output_path}")


if __name__ == "__main__":
    run_daily_prep_protocol()
