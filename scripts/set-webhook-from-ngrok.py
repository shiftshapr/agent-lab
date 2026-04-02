#!/usr/bin/env python3
"""
Get the current ngrok URL and set it as the Telegram webhook.

Run this after starting ngrok (ngrok http 8080). Requires ngrok to be running
with its local API at http://127.0.0.1:4040.

Usage:
  python scripts/set-webhook-from-ngrok.py
"""

from __future__ import annotations

import json
import os
import sys
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


def get_ngrok_url() -> str | None:
    """Get the current ngrok public URL from the local API."""
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        print(f"Could not reach ngrok API: {e}", file=sys.stderr)
        print("Is ngrok running? Start with: ngrok http 8080", file=sys.stderr)
        return None

    tunnels = data.get("tunnels", [])
    for t in tunnels:
        url = t.get("public_url", "")
        if url.startswith("https://"):
            return url
    return None


def set_webhook(url: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN in .env", file=sys.stderr)
        return False

    import urllib.parse
    webhook_url = f"{url.rstrip('/')}/webhook"
    payload = urllib.parse.urlencode({"url": webhook_url}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/setWebhook",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode())
    except Exception as e:
        print(f"Telegram API error: {e}", file=sys.stderr)
        return False

    if not resp.get("ok"):
        print(f"Telegram API: {resp}", file=sys.stderr)
        return False
    print(f"Webhook set: {webhook_url}")
    return True


def main() -> None:
    load_env()
    url = get_ngrok_url()
    if not url:
        sys.exit(1)
    sys.exit(0 if set_webhook(url) else 1)


if __name__ == "__main__":
    main()
