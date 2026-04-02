"""
Hermes — Coordination Agent
Produces daily briefs, manages task queues, and orchestrates other agents.

Runs daily-prep protocol (calendar + email via DeerFlow) and merges with task queue.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).parent.parent.parent
QUEUES_DIR = AGENT_LAB_ROOT / "queues"
LOGS_DIR = AGENT_LAB_ROOT / "logs"
PROTOCOLS_DIR = AGENT_LAB_ROOT / "agents" / "protocol"


def build_daily_brief(tasks: list[dict]) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# Hermes Daily Brief — {date}\n"]
    if not tasks:
        lines.append("No tasks queued.")
    else:
        for t in tasks:
            status = t.get("status", "pending")
            lines.append(f"- [{status.upper()}] {t['description']}")
    return "\n".join(lines)


def load_queue() -> list[dict]:
    queue_path = QUEUES_DIR / "task_queue.json"
    if not queue_path.exists():
        return []
    return json.loads(queue_path.read_text(encoding="utf-8"))


def run_daily_prep_protocol() -> str | None:
    """Run daily-prep protocol; return brief content or None if failed."""
    output_path = LOGS_DIR / f"daily_prep_{datetime.now().strftime('%Y%m%d')}.md"
    result = subprocess.run(
        [sys.executable, str(AGENT_LAB_ROOT / "agents" / "protocol" / "protocol_agent.py"), "--protocol", "daily-prep"],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=True,
        text=True,
        timeout=360,
    )
    if result.returncode != 0:
        print(f"[hermes] daily-prep failed: {result.stderr}", file=sys.stderr)
        return None
    if output_path.exists():
        return output_path.read_text(encoding="utf-8")
    return None


def run() -> None:
    QUEUES_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Run daily-prep protocol (calendar + email via DeerFlow)
    prep_content = run_daily_prep_protocol()

    # Merge with task queue
    tasks = load_queue()
    task_section = build_daily_brief(tasks)

    if prep_content:
        brief = prep_content
        if tasks:
            task_lines = [f"- [{t.get('status', 'pending').upper()}] {t['description']}" for t in tasks]
            brief += "\n\n---\n\n## To-dos\n\n" + "\n".join(task_lines)
    else:
        brief = task_section

    print(brief)

    log_path = LOGS_DIR / f"hermes_{datetime.now().strftime('%Y%m%d')}.md"
    log_path.write_text(brief, encoding="utf-8")
    print(f"\n[hermes] Brief saved to {log_path}")


if __name__ == "__main__":
    run()
