"""
Weekly Preview Protocol
Sunday preview of the upcoming week: meetings, deadlines, blocked time.

Uses DeerFlow agent (Zoho View MCP) for calendar.
Output: logs/weekly_preview_YYYYMMDD.md
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = AGENT_LAB_ROOT / "scripts"
LOGS_DIR = AGENT_LAB_ROOT / "logs"


def run_weekly_preview_protocol() -> None:
    """Run weekly preview for the upcoming week."""
    output_path = LOGS_DIR / f"weekly_preview_{datetime.now().strftime('%Y%m%d')}.md"

    prompt = """Prepare my weekly preview for the upcoming week (starting tomorrow).

1. **Meetings**: List all meetings with briefings for important ones.
2. **Deadlines**: Note any deadlines or milestones.
3. **Blocked time / travel**: Call out blocked time, travel, or other constraints.
4. **Summary**: A short overview of the week's focus.

Output in markdown. Be concise."""

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "run-deerflow-task.py"), prompt, "--output", str(output_path)],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"[weekly-preview] Preview saved to {output_path}")


if __name__ == "__main__":
    run_weekly_preview_protocol()
