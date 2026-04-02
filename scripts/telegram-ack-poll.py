#!/usr/bin/env python3
"""
Poll Telegram for "ack" replies and mark the last reminded meeting as acked.

Run alongside cron-meeting-reminder (or every minute) when using Telegram.
Requires: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID in .env
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
LOGS_DIR = AGENT_LAB_ROOT / "logs"
STATE_FILE = LOGS_DIR / "meeting_reminder_state.json"
OFFSET_FILE = LOGS_DIR / ".telegram_ack_offset"


def load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def poll_and_ack() -> bool:
    """Check Telegram for 'ack' replies; mark meeting as acked. Returns True if acked."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False

    offset = 0
    if OFFSET_FILE.exists():
        try:
            offset = int(OFFSET_FILE.read_text().strip())
        except Exception:
            pass

    try:
        import urllib.request
        import json as _json
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=5"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = _json.loads(r.read().decode())
    except Exception as e:
        print(f"[telegram-ack] Poll error: {e}", file=sys.stderr)
        return False

    if not data.get("ok") or not data.get("result"):
        return False

    state = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    last_key = state.get("_last_reminder_key")
    if not last_key or last_key.startswith("_"):
        return False

    ack_words = {"ack", "ok", "got it", "gotit", "👍", "✓"}
    max_update_id = offset

    for upd in data["result"]:
        max_update_id = max(max_update_id, upd["update_id"] + 1)
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            continue
        if str(msg.get("chat", {}).get("id")) != str(chat_id):
            continue
        text = (msg.get("text") or "").strip().lower()
        if text in ack_words or any(w in text for w in ["ack", "acknowledged"]):
            if last_key in state and isinstance(state[last_key], dict):
                state[last_key]["acked"] = True
                STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
                OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
                OFFSET_FILE.write_text(str(max_update_id), encoding="utf-8")
                print(f"[telegram-ack] Marked as acked: {last_key}", file=sys.stderr)
                return True

    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(max_update_id), encoding="utf-8")
    return False


def main() -> None:
    load_env()
    poll_and_ack()


if __name__ == "__main__":
    main()
