#!/usr/bin/env python3
"""
Test the Shiftshapr webhook by sending a fake Telegram update.

Usage:
  python scripts/test-shiftshapr-webhook.py                    # localhost:8080
  python scripts/test-shiftshapr-webhook.py https://ngrok-url  # ngrok URL
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent


def test_webhook(base_url: str, chat_id: str = "12345", text: str = "/help") -> bool:
    """Send a fake Telegram update to the webhook."""
    payload = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "from": {"id": 12345, "first_name": "Test", "username": "test"},
            "chat": {"id": int(chat_id) if chat_id.isdigit() else 12345, "type": "private"},
            "date": 1234567890,
            "text": text,
        },
    }
    url = f"{base_url.rstrip('/')}/webhook"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status == 200:
                print(f"✓ Webhook returned 200. Check logs/shiftshapr_audit.log for MESSAGE_RECEIVED")
                return True
            print(f"✗ Unexpected status: {r.status}")
            return False
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP error: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
    text = sys.argv[2] if len(sys.argv) > 2 else "/help"
    print(f"Testing {base}/webhook with text={text!r}")
    ok = test_webhook(base, text=text)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
