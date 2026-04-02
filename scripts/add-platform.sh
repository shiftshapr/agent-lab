#!/usr/bin/env bash
# Add a new platform to your session (LinkedIn, X, ChatGPT, etc.).
#
# Usage:
#   ./scripts/add-platform.sh [URL]
#
# Examples:
#   ./scripts/add-platform.sh                    # Launch Chrome only
#   ./scripts/add-platform.sh https://chat.openai.com
#   ./scripts/add-platform.sh https://github.com
#
# Flow: Chrome opens (or reuses existing). If URL given, opens it. Log in, then run:
#   .venv/bin/python scripts/x-login-via-chrome.py

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILE_DIR="${HOME}/Library/Application Support/AgentLabChrome"
URL="${1:-}"

# Launch Chrome if not already running on 9222
if ! curl -s http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
  echo "Starting Chrome (profile persists — existing logins preserved)..."
  mkdir -p "$PROFILE_DIR"
  CHROME=$(find ~/Library/Caches/ms-playwright -name "Google Chrome for Testing" -path "*/MacOS/*" 2>/dev/null | head -1)
  if [ -n "$CHROME" ]; then
    "$CHROME" --remote-debugging-port=9222 --user-data-dir="$PROFILE_DIR" &
    sleep 3
  else
    echo "Chrome for Testing not found. Run: ./scripts/launch-chrome-for-x-login.sh"
    exit 1
  fi
else
  echo "Chrome already running."
fi

if [ -n "$URL" ]; then
  cd "$AGENT_LAB_ROOT"
  .venv/bin/python scripts/add-platform.py "$URL"
fi

echo ""
echo "When done logging in, run:"
echo "  .venv/bin/python scripts/x-login-via-chrome.py"
echo ""
