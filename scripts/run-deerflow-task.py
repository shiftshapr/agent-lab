#!/usr/bin/env python3
"""
Run a one-shot DeerFlow agent task (e.g. for cron).

Loads agent-lab .env, invokes DeerFlowClient with the given prompt,
and writes output to logs or stdout.

Usage:
  python scripts/run-deerflow-task.py "What's on my calendar today?"
  python scripts/run-deerflow-task.py "Search my emails for opportunities" --output logs/daily_prep.md

Requires: DeerFlow backend deps (run from agent-lab root; script sets paths).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
DEER_FLOW_DIR = AGENT_LAB_ROOT / "framework" / "deer-flow"
BACKEND_DIR = DEER_FLOW_DIR / "backend"
LOGS_DIR = AGENT_LAB_ROOT / "logs"


def load_env() -> None:
    """Load agent-lab .env into environment."""
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
        print(f"[run-deerflow-task] Loaded .env from {env_path}", file=sys.stderr)
    else:
        print(f"[run-deerflow-task] Warning: No .env at {env_path}", file=sys.stderr)


def run_task(prompt: str, thread_id: str | None = None) -> str:
    """Invoke DeerFlow agent and return response text."""
    # Set config paths before subprocess
    env = {**os.environ}
    env.setdefault("DEER_FLOW_CONFIG_PATH", str(DEER_FLOW_DIR / "config.yaml"))
    env.setdefault("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(DEER_FLOW_DIR / "extensions_config.json"))
    env["DEERFLOW_TASK_PROMPT"] = prompt
    env["DEERFLOW_TASK_THREAD"] = thread_id or f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Run via uv run (backend deps) from backend dir
    import subprocess
    cmd = ["uv", "run", "python", "-c", _TASK_SCRIPT]
    result = subprocess.run(
        cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"DeerFlow task failed: {result.returncode}")
    return result.stdout.strip()


_TASK_SCRIPT = """
import os
from src.client import DeerFlowClient
prompt = os.environ["DEERFLOW_TASK_PROMPT"]
thread_id = os.environ["DEERFLOW_TASK_THREAD"]
client = DeerFlowClient()
print(client.chat(prompt, thread_id=thread_id))
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DeerFlow agent task")
    parser.add_argument("prompt", help="Task prompt for the agent")
    parser.add_argument("--output", "-o", type=Path, help="Write response to file")
    parser.add_argument("--thread-id", help="Thread ID for conversation context")
    args = parser.parse_args()

    load_env()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[run-deerflow-task] Running: {args.prompt[:80]}...", file=sys.stderr)
    response = run_task(args.prompt, thread_id=args.thread_id)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(response, encoding="utf-8")
        print(f"[run-deerflow-task] Wrote {len(response)} chars to {args.output}", file=sys.stderr)
    else:
        print(response)


if __name__ == "__main__":
    main()
