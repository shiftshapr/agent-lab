#!/usr/bin/env python3
"""Open a URL in the session Chrome so you can log in. Then run x-login-via-chrome.py to save."""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "about:blank"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: .venv/bin/pip install playwright")
        sys.exit(1)

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            page.goto(url)
            print(f"Opened {url}")
            print("Log in, then run: .venv/bin/python scripts/x-login-via-chrome.py")
    except Exception as e:
        print(f"Connect to Chrome first: ./scripts/launch-chrome-for-x-login.sh")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
