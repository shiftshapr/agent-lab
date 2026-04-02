#!/usr/bin/env python3
"""
Send a brief (daily_prep, weekly_preview, etc.) to Telegram or Slack.

Requires .env:
  - Telegram: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  - Slack: SLACK_DELIVERY_CHANNEL_ID, SLACK_BOT_TOKEN_1 (or SLACK_DELIVERY_TOKEN)

Usage:
  python scripts/send-brief.py logs/daily_prep_20260319.md
  python scripts/send-brief.py logs/daily_prep_20260319.md --telegram
  python scripts/send-brief.py logs/daily_prep_20260319.md --slack
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent

_DEERFLOW_BACKEND = AGENT_LAB_ROOT / "framework" / "deer-flow" / "backend"
if str(_DEERFLOW_BACKEND) not in sys.path:
    sys.path.insert(0, str(_DEERFLOW_BACKEND))

try:
    from app.utils.channel_message_format import format_channel_message
except ImportError:
    # Cron often uses bare `python3` without deer-flow deps; never fail delivery.
    def format_channel_message(text: str) -> str:
        import re

        if not text or not str(text).strip():
            return text
        if os.environ.get("CHANNEL_MESSAGE_RAW", "").strip() in ("1", "true", "yes"):
            return text
        t = re.sub(r"</?(?:think|reasoning|redacted)[^>]*>", "", text, flags=re.I | re.DOTALL)
        t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        t = re.sub(r"`([^`]+)`", r"\1", t)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 — \2", t)
        return re.sub(r"\n{3,}", "\n\n", t).strip()


def load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def send_telegram(content: str, chat_id: str | None = None) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    cid = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not cid:
        print("[send-brief] Telegram: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env", file=sys.stderr)
        return False
    try:
        import urllib.request
        import json as _json
        # Split long messages (Telegram limit ~4096)
        chunks = [content[i : i + 4000] for i in range(0, len(content), 4000)]
        for chunk in chunks:
            data = _json.dumps({"chat_id": cid, "text": chunk}).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status != 200:
                    raise RuntimeError(f"Telegram API: {r.status}")
        print("[send-brief] Sent to Telegram", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[send-brief] Telegram error: {e}", file=sys.stderr)
        return False


def send_slack(content: str, channel_id: str | None = None) -> bool:
    token = os.environ.get("SLACK_DELIVERY_TOKEN") or os.environ.get("SLACK_BOT_TOKEN_1")
    ch = channel_id or os.environ.get("SLACK_DELIVERY_CHANNEL_ID")
    if not token or not ch:
        print("[send-brief] Slack: set SLACK_DELIVERY_CHANNEL_ID and SLACK_BOT_TOKEN_1 (or SLACK_DELIVERY_TOKEN) in .env", file=sys.stderr)
        return False
    try:
        from slack_sdk import WebClient

        client = WebClient(token=token)
        # Plain text sections (markdown already converted for readability in clients)
        blocks = [{"type": "section", "text": {"type": "plain_text", "text": content[:3000], "emoji": True}}]
        if len(content) > 3000:
            blocks.append(
                {"type": "section", "text": {"type": "plain_text", "text": content[3000:6000], "emoji": True}}
            )
        client.chat_postMessage(channel=ch, text=content[:500], blocks=blocks)
        print("[send-brief] Sent to Slack", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[send-brief] Slack error: {e}", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path, help="Brief file to send")
    parser.add_argument("--telegram", action="store_true", help="Send to Telegram")
    parser.add_argument("--slack", action="store_true", help="Send to Slack")
    parser.add_argument("--both", action="store_true", help="Send to both")
    args = parser.parse_args()

    load_env()

    path = args.file if args.file.is_absolute() else AGENT_LAB_ROOT / args.file
    if not path.exists():
        print(f"[send-brief] File not found: {path}", file=sys.stderr)
        sys.exit(1)

    content = format_channel_message(path.read_text(encoding="utf-8"))

    if args.both:
        ok = send_telegram(content) or send_slack(content)
    elif args.telegram:
        ok = send_telegram(content)
    elif args.slack:
        ok = send_slack(content)
    else:
        # Auto: try Telegram first, then Slack
        ok = send_telegram(content) or send_slack(content)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
