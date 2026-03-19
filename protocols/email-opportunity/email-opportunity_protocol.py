"""
Email Opportunity Search Protocol
Searches emails and links for project opportunities and items needing response.

Uses DeerFlow agent (Zoho View MCP). Project tags from config/project_tags.yaml.
Output: logs/email_opportunity_YYYYMMDD.md
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = AGENT_LAB_ROOT / "scripts"
LOGS_DIR = AGENT_LAB_ROOT / "logs"
CONFIG_DIR = AGENT_LAB_ROOT / "config"


def _load_project_context() -> str:
    """Load project tags for opportunity classification."""
    tags_path = CONFIG_DIR / "project_tags.yaml"
    if not tags_path.exists():
        return ""
    try:
        content = tags_path.read_text(encoding="utf-8")
        return f"\n\nProject tags for classification:\n{content}"
    except Exception:
        return ""


def run_email_opportunity_protocol() -> None:
    """Run email opportunity search."""
    output_path = LOGS_DIR / f"email_opportunity_{datetime.now().strftime('%Y%m%d')}.md"
    project_context = _load_project_context()

    prompt = f"""Search my emails from the last 7 days for:

1. **Opportunities**: Grants, fellowships, partnerships, product feedback, community/speaking opportunities.
2. **Items needing response**: Unread emails, threads where I'm mentioned, time-sensitive requests, meeting invites pending response.
3. **Links**: Extract URLs from email bodies and classify by opportunity type.

List findings in markdown. For each item: subject, sender, date, and why it matters.
{project_context}"""

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "run-deerflow-task.py"), prompt, "--output", str(output_path)],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    print(f"[email-opportunity] Results saved to {output_path}")


if __name__ == "__main__":
    run_email_opportunity_protocol()
