#!/usr/bin/env bash
# Kill any existing draft editor on DRAFT_EDITOR_PORT (default 8081), then start it.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$AGENT_LAB_ROOT"
[ -f .env ] && set -a && source .env && set +a
PORT="${DRAFT_EDITOR_PORT:-8081}"
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "Killing process on port $PORT..."
  lsof -ti:"$PORT" | xargs kill 2>/dev/null || true
  sleep 1
fi
echo "Starting draft editor on port $PORT (background)..."
nohup "$SCRIPT_DIR/start-draft-editor.sh" > /tmp/draft-editor.log 2>&1 &
echo "Draft editor started. Logs: /tmp/draft-editor.log"
