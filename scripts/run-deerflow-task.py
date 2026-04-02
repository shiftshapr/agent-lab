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


def run_task(prompt: str, thread_id: str | None = None, timeout: int = 300) -> str:
    """Invoke DeerFlow agent and return response text."""
    # Set config paths before subprocess
    env = {**os.environ}
    env.setdefault("DEER_FLOW_CONFIG_PATH", str(DEER_FLOW_DIR / "config.yaml"))
    env.setdefault("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(DEER_FLOW_DIR / "extensions_config.json"))
    env["AGENT_LAB_ROOT"] = str(AGENT_LAB_ROOT)  # For shiftshapr_remember tool
    env["DEERFLOW_TASK_PROMPT"] = prompt
    env["DEERFLOW_TASK_THREAD"] = thread_id or f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Run via uv run (backend deps) from backend dir
    import subprocess
    cmd = ["uv", "run", "python", "-c", _TASK_SCRIPT]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"[run-deerflow-task] Timed out after {timeout}s", file=sys.stderr)
        raise RuntimeError(f"DeerFlow task timed out after {timeout}s")
    if result.returncode != 0:
        err = (result.stderr or "").strip()
        out = (result.stdout or "").strip()
        print(f"[run-deerflow-task] exit={result.returncode}", file=sys.stderr)
        if err:
            print(err, file=sys.stderr)
        if out:
            print(f"[run-deerflow-task] stdout:\n{out}", file=sys.stderr)
        # One-line hint for Telegram / callers (avoid useless "failed: 1")
        detail = _summarize_subprocess_failure(err, out)
        raise RuntimeError(f"DeerFlow task failed ({result.returncode}): {detail}")
    return result.stdout.strip()


def _summarize_subprocess_failure(stderr: str, stdout: str) -> str:
    """Pick a short human-readable reason from uv/python stderr."""
    text = (stderr or "") + "\n" + (stdout or "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Prefer common root causes
    for ln in lines:
        low = ln.lower()
        if "modulenotfounderror" in low or "importerror" in low:
            return ln[:300]
        if "connection refused" in low:
            return "Connection refused — is LangGraph (2024) / Gateway (8001) running? Try: framework/deer-flow/scripts/restart-deerflow.sh"
        if "api key" in low or "authentication" in low or "401" in ln or "403" in ln:
            return ln[:300]
    # Last error-ish line before a traceback noise
    for ln in reversed(lines):
        if ln.startswith("Error") or ln.startswith("Exception") or "Error:" in ln:
            return ln[:300]
    if lines:
        return lines[-1][:300]
    return "no stderr — run from agent-lab root: uv sync in framework/deer-flow/backend; check LangGraph is up"


_TASK_SCRIPT = """
import os
import sys
from deerflow.client import DeerFlowClient
from langgraph.checkpoint.memory import InMemorySaver
prompt = os.environ["DEERFLOW_TASK_PROMPT"]
thread_id = os.environ["DEERFLOW_TASK_THREAD"]
recursion_limit = int(os.environ.get("DEERFLOW_TASK_RECURSION_LIMIT", "100"))
# InMemorySaver supports async (astream) — required for MCP tools (Zoho, etc.)
client = DeerFlowClient(checkpointer=InMemorySaver())
out = client.chat(prompt, thread_id=thread_id, recursion_limit=recursion_limit)
if not (out or "").strip():
    print("[run-deerflow-task] WARNING: empty assistant text (raise DEERFLOW_TASK_RECURSION_LIMIT if graph hit step cap)", file=sys.stderr)
print(out)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DeerFlow agent task")
    parser.add_argument("prompt", help="Task prompt for the agent")
    parser.add_argument("--output", "-o", type=Path, help="Write response to file")
    parser.add_argument("--thread-id", help="Thread ID for conversation context")
    parser.add_argument("--timeout", "-t", type=int, default=300, help="Timeout in seconds (default: 300)")
    args = parser.parse_args()

    load_env()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[run-deerflow-task] Running: {args.prompt[:80]}... (timeout: {args.timeout}s)", file=sys.stderr)
    try:
        response = run_task(args.prompt, thread_id=args.thread_id, timeout=args.timeout)
    except RuntimeError as e:
        # Clean exit so subprocess callers get one stderr line, not a duplicate traceback
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(response, encoding="utf-8")
        print(f"[run-deerflow-task] Wrote {len(response)} chars to {args.output}", file=sys.stderr)
    else:
        print(response)


if __name__ == "__main__":
    main()
