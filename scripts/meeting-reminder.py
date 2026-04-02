#!/usr/bin/env python3
"""
Meeting reminder with escalation: 15 min → 5 min if no ack.

Fetches today's calendar via DeerFlow (Zoho View MCP), sends reminders at 15 min
and 5 min before each meeting. If user acks the 15-min reminder, the 5-min
reminder is skipped.

State: logs/meeting_reminder_state.json
Ack: run `python scripts/ack-meeting.py "Meeting Title"` or reply "ack" to Telegram.

Requires: TELEGRAM_* or SLACK_DELIVERY_* in .env (same as send-brief).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
LOGS_DIR = AGENT_LAB_ROOT / "logs"
STATE_FILE = LOGS_DIR / "meeting_reminder_state.json"

_DEERFLOW_BACKEND = AGENT_LAB_ROOT / "framework" / "deer-flow" / "backend"
if str(_DEERFLOW_BACKEND) not in sys.path:
    sys.path.insert(0, str(_DEERFLOW_BACKEND))

try:
    from app.utils.channel_message_format import format_channel_message
except ImportError:
    def format_channel_message(text: str) -> str:
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


def _key(title: str, start: str) -> str:
    return f"{start}|{title}"


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def fetch_calendar() -> list[tuple[str, str]]:
    """Fetch today's events as (HH:MM, title) via DeerFlow."""
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""List today's calendar events ({today}) with start times.

For each event, output exactly one line in this format:
HH:MM | Event Title

Use 24-hour time (e.g. 09:30, 14:00). Only include events that haven't started yet.
Output nothing else — just the lines."""

    env = {**os.environ}
    env.setdefault("DEER_FLOW_CONFIG_PATH", str(AGENT_LAB_ROOT / "framework" / "deer-flow" / "config.yaml"))
    env.setdefault("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(AGENT_LAB_ROOT / "framework" / "deer-flow" / "extensions_config.json"))

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "run-deerflow-task.py"), prompt, "--timeout", "120"],
            cwd=str(AGENT_LAB_ROOT),
            capture_output=True,
            text=True,
            env=env,
            timeout=130,
        )
    except subprocess.TimeoutExpired:
        print("[meeting-reminder] DeerFlow timed out", file=sys.stderr)
        return []

    if result.returncode != 0:
        print(f"[meeting-reminder] DeerFlow failed: {result.stderr[:300]}", file=sys.stderr)
        return []

    events: list[tuple[str, str]] = []
    # Parse lines like "09:30 | Standup" or "14:00 | Client call"
    for line in result.stdout.strip().split("\n"):
        m = re.match(r"(\d{1,2}:\d{2})\s*[|\-–]\s*(.+)", line.strip())
        if m:
            events.append((m.group(1), m.group(2).strip()))
    return events


def minutes_until(hhmm: str) -> int | None:
    """Minutes until HH:MM today. Returns None if already passed."""
    try:
        h, m = map(int, hhmm.split(":"))
        target = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        delta = (target - datetime.now()).total_seconds() / 60
        return int(delta) if delta > 0 else None
    except (ValueError, TypeError):
        return None


def send_reminder(message: str) -> bool:
    """Send via Telegram or Slack (same as send-brief)."""
    message = format_channel_message(message)
    # Use send-brief logic inline to avoid writing to file
    token_tg = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_tg = os.environ.get("TELEGRAM_CHAT_ID")
    if token_tg and chat_tg:
        try:
            import urllib.request
            import json as _json
            data = _json.dumps({"chat_id": chat_tg, "text": message}).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token_tg}/sendMessage",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 200:
                    return True
        except Exception as e:
            print(f"[meeting-reminder] Telegram error: {e}", file=sys.stderr)

    token_slack = os.environ.get("SLACK_DELIVERY_TOKEN") or os.environ.get("SLACK_BOT_TOKEN_1")
    ch_slack = os.environ.get("SLACK_DELIVERY_CHANNEL_ID")
    if token_slack and ch_slack:
        try:
            from slack_sdk import WebClient
            client = WebClient(token=token_slack)
            client.chat_postMessage(channel=ch_slack, text=message)
            return True
        except Exception as e:
            print(f"[meeting-reminder] Slack error: {e}", file=sys.stderr)

    return False


def run() -> None:
    load_env()
    state = load_state()
    events = fetch_calendar()

    if not events:
        return

    now = datetime.now()
    today_key = now.strftime("%Y-%m-%d")

    for hhmm, title in events:
        mins = minutes_until(hhmm)
        if mins is None:
            continue

        key = _key(title, hhmm)
        if key not in state:
            state[key] = {"sent_15": False, "acked": False, "sent_5": False, "date": today_key}

        entry = state[key]
        if entry.get("date") != today_key:
            entry["sent_15"] = False
            entry["acked"] = False
            entry["sent_5"] = False
            entry["date"] = today_key

        # 15 min reminder
        if 14 <= mins <= 16 and not entry["sent_15"]:
            msg = f"📅 Meeting in ~15 min: **{title}** at {hhmm}\nReply 'ack' to skip the 5-min reminder."
            if send_reminder(msg):
                entry["sent_15"] = True
                state["_last_reminder_key"] = key  # For Telegram ack polling
                print(f"[meeting-reminder] Sent 15-min: {title}", file=sys.stderr)

        # 5 min reminder (only if no ack)
        elif 4 <= mins <= 6 and not entry["acked"] and not entry["sent_5"]:
            msg = f"⚠️ Meeting in ~5 min: **{title}** at {hhmm}"
            if send_reminder(msg):
                entry["sent_5"] = True
                print(f"[meeting-reminder] Sent 5-min (escalation): {title}", file=sys.stderr)

    save_state(state)


if __name__ == "__main__":
    run()
