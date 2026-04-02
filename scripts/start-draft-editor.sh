#!/usr/bin/env bash
# Start the draft editor server. Requires DRAFT_EDITOR_PASSWORD in .env.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$AGENT_LAB_ROOT"
[ -f .env ] && set -a && source .env && set +a
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export AGENT_LAB_ROOT
if [ -z "$DRAFT_EDITOR_PASSWORD" ]; then
  echo "Set DRAFT_EDITOR_PASSWORD in .env"
  exit 1
fi
exec .venv/bin/python -m apps.draft_editor.app
