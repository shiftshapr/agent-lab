"""
Slack Digest Protocol
Summarizes unread/important Slack activity across configured workspaces.

Uses DeerFlow agent (Slack MCP servers).
Output: logs/slack_digest_YYYYMMDD.md
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = AGENT_LAB_ROOT / "scripts"
LOGS_DIR = AGENT_LAB_ROOT / "logs"


def run_slack_digest_protocol() -> None:
    """Run Slack digest across workspaces."""
    output_path = LOGS_DIR / f"slack_digest_{datetime.now().strftime('%Y%m%d')}.md"

    prompt = """Summarize my Slack activity across all workspaces:

1. **Unread / mentions**: List channels or DMs with unread messages or @mentions.
2. **Key threads**: Highlight important threads that need my attention.
3. **Action items**: Any follow-ups or decisions needed from me.

Group by workspace if possible. Be concise. Output in markdown."""

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "run-deerflow-task.py"), prompt, "--output", str(output_path)],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"[slack-digest] Digest saved to {output_path}")


if __name__ == "__main__":
    run_slack_digest_protocol()
