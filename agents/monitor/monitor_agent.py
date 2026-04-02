"""
Monitor Agent — runs protocols for Email, Calendar, Slack.
Produces digests, opportunity lists. Read-only; no external write.

Runs: daily-prep, email-opportunity, slack-digest via protocol_agent.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).parent.parent.parent
LOGS_DIR = AGENT_LAB_ROOT / "logs"

SOURCES = [
    "Email (Zoho View MCP)",
    "Calendar (Zoho View MCP)",
    "Slack",
    "X (Twitter)",
    "LinkedIn",
    "Reddit",
    "Substack",
    "Grant / Fellowship databases",
]

OUTPUT_TYPES = [
    "daily_digest",
    "candidate_replies",
    "opportunity_list",
    "trend_summary",
]


def _run_protocol(name: str) -> str | None:
    """Run protocol; return output path content or None."""
    result = subprocess.run(
        [sys.executable, str(AGENT_LAB_ROOT / "agents" / "protocol" / "protocol_agent.py"), "--protocol", name],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=True,
        text=True,
        timeout=360,
    )
    if result.returncode != 0:
        print(f"[monitor] {name} failed: {result.stderr}", file=sys.stderr)
        return None
    date_str = datetime.now().strftime("%Y%m%d")
    path = LOGS_DIR / f"{name.replace('-', '_')}_{date_str}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def run(mode: str = "daily") -> None:
    """Run monitor: daily (all), email-only, slack-only."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if mode == "daily":
        prep = _run_protocol("daily-prep")
        email = _run_protocol("email-opportunity")
        slack = _run_protocol("slack-digest")
        # Combine into digest
        parts = []
        if prep:
            parts.append("## Daily Prep\n\n" + prep)
        if email:
            parts.append("\n\n## Email Opportunities\n\n" + email)
        if slack:
            parts.append("\n\n## Slack Digest\n\n" + slack)
        if parts:
            combined = "# Monitor Digest — " + datetime.now().strftime("%Y-%m-%d") + "\n\n" + "\n".join(parts)
            out_path = LOGS_DIR / f"monitor_digest_{datetime.now().strftime('%Y%m%d')}.md"
            out_path.write_text(combined, encoding="utf-8")
            print(f"[monitor] Digest saved to {out_path}")
        else:
            print("[monitor] No outputs produced")
    elif mode == "email":
        _run_protocol("email-opportunity")
    elif mode == "slack":
        _run_protocol("slack-digest")
    else:
        print(f"[monitor] Unknown mode: {mode}. Use daily, email, or slack.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mode", default="daily", choices=["daily", "email", "slack"])
    run(mode=p.parse_args().mode)


if __name__ == "__main__":
    run()
