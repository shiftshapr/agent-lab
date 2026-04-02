#!/usr/bin/env python3
"""
One-time login for LinkedIn and X (Twitter) — save session for Playwright MCP.

Opens LinkedIn, then X, in a headed browser. Log in to both manually (including 2FA).
When both are logged in, press Enter. Saves cookies and localStorage to one file
for reuse by the agent when posting to either platform.

Run from agent-lab root:
  .venv/bin/python scripts/linkedin-login-setup.py

Requires: playwright installed in .venv
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
DATA_DIR = AGENT_LAB_ROOT / "data"
STATE_PATH = DATA_DIR / "linkedin_state.json"  # LinkedIn + X in one file


def _domains_in_storage(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c.get("domain", "").lower() for c in data.get("cookies", [])}


def _has_linkedin(domains: set[str]) -> bool:
    return any("linkedin" in d for d in domains)


def _has_x(domains: set[str]) -> bool:
    return any("twitter" in d or d.endswith("x.com") or ".x.com" in d for d in domains)


def validate_saved_state(path: Path, *, linkedin_only: bool) -> None:
    """Warn if the file is missing expected auth cookies (common silent failure)."""
    try:
        domains = _domains_in_storage(path)
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARNING: Could not read saved state: {e}", file=sys.stderr)
        return
    if not _has_linkedin(domains):
        print(
            "\n*** WARNING: No LinkedIn cookies in the saved file. ***\n"
            "You may not have finished LinkedIn login in this browser, or the wrong file path was used.\n"
            "Fix: log in until you see your feed, then save again. For X issues, use real Chrome:\n"
            "  scripts/launch-chrome-for-x-login.sh  (or Google Chrome + remote debugging)\n"
            "  then: uv run python scripts/x-login-via-chrome.py\n",
            file=sys.stderr,
        )
    elif not linkedin_only and not _has_x(domains):
        print(
            "\n*** WARNING: No X (Twitter) cookies in the saved file. ***\n"
            "LinkedIn looks OK; X often blocks Playwright Chromium. Use Chrome + CDP export:\n"
            "  See scripts/x-login-via-chrome.py (top docstring).\n",
            file=sys.stderr,
        )


def main() -> None:
    # Load .env
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--linkedin-only", action="store_true", help="Skip X — only log into LinkedIn (use if X blocks)")
    args, _ = parser.parse_known_args()

    out_path = os.environ.get("LINKEDIN_STORAGE_STATE") or str(STATE_PATH)
    out_path = Path(out_path).resolve()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install Playwright:", file=sys.stderr)
        print("  .venv/bin/pip install playwright", file=sys.stderr)
        print("  .venv/bin/playwright install chromium", file=sys.stderr)
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Opening browser. Log in to LinkedIn, then X (Twitter).")
    print("1. LinkedIn — log in when the first tab opens")
    print("2. X — a second tab will open; log in there")
    print("3. When both show your feed, return here and press Enter.")
    print("   (X may block Chromium — if so, use --linkedin-only and skip X for now)")
    print()

    with sync_playwright() as p:
        # Use real Chrome if installed — X often blocks Playwright's Chromium
        try:
            browser = p.chromium.launch(headless=False, channel="chrome")
            print("Using Chrome (better for X login)")
        except Exception:
            browser = p.chromium.launch(headless=False)
            print("Using Chromium — X may block login; install Chrome for better success")

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        # Separate tabs: navigating one tab from LinkedIn → X drops the LinkedIn page and
        # confused some saves; cookies should persist either way, but two tabs is clearer.
        page_li = context.new_page()
        page_li.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        input("Press Enter after LinkedIn login... ")
        if not args.linkedin_only:
            import time

            time.sleep(1)
            page_x = context.new_page()
            page_x.goto("https://x.com/home", wait_until="domcontentloaded")
            input("Press Enter after X login (when both feeds work)... ")
        else:
            print("Skipping X (--linkedin-only)")
        context.storage_state(path=str(out_path))
        browser.close()

    print(f"Saved session to {out_path}")
    validate_saved_state(out_path, linkedin_only=args.linkedin_only)
    print()
    print("Add to .env (if not already):")
    print(f'  LINKEDIN_STORAGE_STATE={out_path}')
    print()
    print("The agent can now post to LinkedIn and X. Restart DeerFlow if using the web UI.")


if __name__ == "__main__":
    main()
