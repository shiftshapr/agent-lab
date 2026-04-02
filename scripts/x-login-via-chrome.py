#!/usr/bin/env python3
r"""
Log into LinkedIn, X (Twitter), and ChatGPT — save session for Playwright MCP.

Connects to your real Chrome so you log in there, then we save the session.
ChatGPT = image generation via DALL-E (no API key needed).

Steps:
1. Close all Chrome/Chromium windows
2. Run: ./scripts/launch-chrome-for-x-login.sh
3. Log into linkedin.com, x.com, and chat.openai.com
4. Run: .venv/bin/python scripts/x-login-via-chrome.py
5. Session saved — agent can post to LinkedIn/X and generate images via ChatGPT
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
DATA_DIR = AGENT_LAB_ROOT / "data"
STATE_PATH = DATA_DIR / "linkedin_state.json"


def load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def main() -> None:
    load_env()
    out_path = Path(os.environ.get("LINKEDIN_STORAGE_STATE", STATE_PATH)).resolve()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: .venv/bin/pip install playwright", file=sys.stderr)
        sys.exit(1)

    print("Connecting to Chrome on port 9222...")
    print("(Chrome must be running with: --remote-debugging-port=9222)")
    print()

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        except Exception as e:
            print("Could not connect. Make sure Chrome is running with:", file=sys.stderr)
            print("  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222", file=sys.stderr)
            print(file=sys.stderr)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Get default context (your logged-in tabs)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        context.storage_state(path=str(out_path))
        browser.close()

    print(f"Session saved to {out_path}")
    print("You can close the Chrome window you opened with --remote-debugging-port=9222")


if __name__ == "__main__":
    main()
