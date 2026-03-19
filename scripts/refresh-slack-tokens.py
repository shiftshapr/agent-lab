#!/usr/bin/env python3
"""
Refresh Slack App Configuration tokens before they expire.

Uses tooling.tokens.rotate (for App Configuration Tokens from api.slack.com).
No client_id/client_secret needed — only refresh_token.

Run: python3 scripts/refresh-slack-tokens.py
Cron: 0 */6 * * * (every 6 hours) to stay ahead of 12h expiry
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
TOKENS_FILE = AGENT_LAB_ROOT / "scripts" / "slack-tokens.json"
ENV_FILE = AGENT_LAB_ROOT / ".env"


def load_tokens() -> dict:
    if not TOKENS_FILE.exists():
        print(f"Error: {TOKENS_FILE} not found.")
        print("Copy scripts/slack-tokens.example.json to slack-tokens.json and fill in.")
        sys.exit(1)
    with open(TOKENS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_tokens(data: dict) -> None:
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def refresh_single(refresh_token: str) -> tuple[str, str, str | None]:
    """Call tooling.tokens.rotate, return (access_token, new_refresh_token, team_id)."""
    body = f"refresh_token={urllib.parse.quote(refresh_token)}"
    req = urllib.request.Request(
        "https://slack.com/api/tooling.tokens.rotate",
        data=body.encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

    access_token = data.get("token")
    new_refresh = data.get("refresh_token") or refresh_token
    team_id = data.get("team_id")
    if not access_token:
        raise RuntimeError("No token in response")
    return access_token, new_refresh, team_id


def read_env() -> str:
    if not ENV_FILE.exists():
        return ""
    return ENV_FILE.read_text(encoding="utf-8")


def update_env_var(content: str, key: str, value: str) -> str:
    """Update or add .env line for KEY=value."""
    pattern = re.compile(rf"^({re.escape(key)})=.*$", re.MULTILINE)
    new_line = f"{key}={value}"
    if pattern.search(content):
        return pattern.sub(new_line, content, count=1)
    return content.rstrip() + "\n" + new_line + "\n"


def main() -> None:
    cfg = load_tokens()
    workspaces = cfg.get("workspaces", [])
    if not workspaces:
        print("Error: no workspaces in slack-tokens.json")
        sys.exit(1)

    env_content = read_env()
    updated_workspaces = False

    for i, ws in enumerate(workspaces, start=1):
        refresh_token = ws.get("refresh_token")
        team_id = ws.get("team_id")
        name = ws.get("name", f"workspace-{i}")
        if not refresh_token:
            print(f"  [{name}] Skipping: no refresh_token")
            continue

        try:
            access_token, new_refresh, resp_team_id = refresh_single(refresh_token)
            env_content = update_env_var(
                env_content, f"SLACK_BOT_TOKEN_{i}", access_token
            )
            team_id = resp_team_id or team_id
            if team_id:
                env_content = update_env_var(
                    env_content, f"SLACK_TEAM_ID_{i}", team_id
                )
            ws["refresh_token"] = new_refresh
            ws["team_id"] = team_id or ws.get("team_id")
            updated_workspaces = True
            print(f"  [{name}] Refreshed (team_id={team_id})")
        except Exception as e:
            print(f"  [{name}] Failed: {e}")

    if updated_workspaces:
        save_tokens(cfg)
        ENV_FILE.write_text(env_content, encoding="utf-8")
        print(f"Updated {ENV_FILE} and {TOKENS_FILE}")
    else:
        print("No tokens refreshed.")


if __name__ == "__main__":
    main()
