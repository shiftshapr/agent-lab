#!/usr/bin/env python3
"""
Publish content via DeerFlow (Zoho Publish MCP).

Requires explicit activation: --activate before first use.
Logs all actions to logs/publish_audit.log.

Usage:
  python scripts/publish-via-deerflow.py --activate
  python scripts/publish-via-deerflow.py --email "recipient@example.com" --subject "Hi" --body "Hello"
  python scripts/publish-via-deerflow.py --platform slack --content "Posting to #general"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
LOGS_DIR = AGENT_LAB_ROOT / "logs"
AUDIT_FILE = LOGS_DIR / "publish_audit.log"
STATE_FILE = LOGS_DIR / ".publish_activated"


def load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def is_activated() -> bool:
    return STATE_FILE.exists()


def activate() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(datetime.utcnow().isoformat() + "Z")
    _audit("ACTIVATED", {"by": "human"})
    print("[publish] Activated. Publishing enabled.")


def _audit(action: str, details: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": datetime.utcnow().isoformat() + "Z", "action": action, **details}
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def publish_email(recipient: str, subject: str, body: str) -> None:
    if not is_activated():
        print("[publish] Not activated. Run with --activate first.", file=sys.stderr)
        sys.exit(1)
    prompt = f"""Send this email via Zoho Publish MCP:

To: {recipient}
Subject: {subject}

{body}

Send the email now."""
    _run_deerflow(prompt, platform="email", details={"recipient": recipient, "subject": subject})


def publish_slack(content: str, channel: str | None = None) -> None:
    if not is_activated():
        print("[publish] Not activated. Run with --activate first.", file=sys.stderr)
        sys.exit(1)
    channel_part = f" to {channel}" if channel else ""
    prompt = f"""Post this message to Slack{channel_part} via the Slack MCP:

{content}

Post it now."""
    _run_deerflow(prompt, platform="slack", details={"channel": channel or "default"})


def _run_deerflow(prompt: str, platform: str, details: dict) -> None:
    load_env()
    _audit("PUBLISH_REQUEST", {"platform": platform, **details, "content_preview": prompt[:120]})
    result = __import__("subprocess").run(
        [sys.executable, str(SCRIPT_DIR / "run-deerflow-task.py"), prompt, "--timeout", "120"],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _audit("PUBLISH_FAILED", {"platform": platform, "error": result.stderr[:500]})
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    _audit("PUBLISH_COMPLETED", {"platform": platform})
    print("[publish] Request sent. DeerFlow agent executed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activate", action="store_true", help="Activate publishing (required before first use)")
    parser.add_argument("--email", action="store_true", help="Send email")
    parser.add_argument("--recipient", help="Email recipient")
    parser.add_argument("--subject", default="", help="Email subject")
    parser.add_argument("--body", default="", help="Email body")
    parser.add_argument("--platform", choices=["slack", "email"], help="Platform")
    parser.add_argument("--content", help="Content to post (for Slack)")
    parser.add_argument("--channel", help="Slack channel (optional)")
    args = parser.parse_args()

    if args.activate:
        activate()
        return

    if args.email or (args.platform == "email"):
        if not args.recipient:
            print("[publish] --recipient required for email", file=sys.stderr)
            sys.exit(1)
        body = args.body or (sys.stdin.read() if not sys.stdin.isatty() else "")
        publish_email(args.recipient, args.subject, body)
    elif args.platform == "slack":
        content = args.content or (sys.stdin.read() if not sys.stdin.isatty() else "")
        if not content:
            print("[publish] --content or stdin required for Slack", file=sys.stderr)
            sys.exit(1)
        publish_slack(content, args.channel)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
