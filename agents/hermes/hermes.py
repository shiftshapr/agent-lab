"""
Hermes — Coordination Agent
Produces daily briefs, manages task queues, and orchestrates other agents.

This is a stub. Full implementation follows once the core protocol loop is stable.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

QUEUES_DIR = Path(__file__).parent.parent.parent / "queues"
LOGS_DIR   = Path(__file__).parent.parent.parent / "logs"


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


def run() -> None:
    QUEUES_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    tasks = load_queue()
    brief = build_daily_brief(tasks)
    print(brief)

    log_path = LOGS_DIR / f"hermes_{datetime.now().strftime('%Y%m%d')}.md"
    log_path.write_text(brief, encoding="utf-8")
    print(f"\n[hermes] Brief saved to {log_path}")


if __name__ == "__main__":
    run()
