#!/usr/bin/env bash
# Launch Chrome for Testing with remote debugging and persistent profile.
# Logins (LinkedIn, X, ChatGPT) persist between runs — no re-login each time.
# Run this, log in to any new sites, then: .venv/bin/python scripts/x-login-via-chrome.py

PROFILE_DIR="${HOME}/Library/Application Support/AgentLabChrome"
mkdir -p "$PROFILE_DIR"

CHROME=$(find ~/Library/Caches/ms-playwright -name "Google Chrome for Testing" -path "*/MacOS/*" 2>/dev/null | head -1)
if [ -n "$CHROME" ]; then
  echo "Launching Chrome for Testing (profile: $PROFILE_DIR)"
  echo "LinkedIn/X/ChatGPT logins persist — add new sites as needed, then save."
  "$CHROME" --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR"
else
  echo "Chrome for Testing not found. Try: open -a 'Google Chrome' --args --remote-debugging-port=9222 --user-data-dir=$PROFILE_DIR"
  exit 1
fi
