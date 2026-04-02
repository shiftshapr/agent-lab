#!/usr/bin/env python3
"""
Set Telegram webhook URL. Call this after exposing your server (ngrok, etc.).

Usage:
  python scripts/set-telegram-webhook.py https://your-domain.com/webhook
  python scripts/set-telegram-webhook.py  # Uses SHIFTSHAPR_WEBHOOK_URL from .env
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent


def load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def set_webhook(url: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN in .env", file=sys.stderr)
        return False
    if not url.startswith("https://"):
        print("Webhook URL must use HTTPS", file=sys.stderr)
        return False
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/setWebhook",
        data=urllib.parse.urlencode({"url": url}).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    if not data.get("ok"):
        print(f"Telegram API: {data}", file=sys.stderr)
        return False
    print(f"Webhook set: {url}")
    return True


if __name__ == "__main__":
    load_env()
    url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SHIFTSHAPR_WEBHOOK_URL")
    if not url:
        print("Usage: set-telegram-webhook.py <https://your-url/webhook>", file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if set_webhook(url) else 1)
