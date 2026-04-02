#!/usr/bin/env bash
# Setup Shiftshapr as a launchd service on MacMini.
# Run from agent-lab root: ./scripts/setup-shiftshapr-launchd.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_SRC="$AGENT_LAB_ROOT/agents/shiftshapr/com.agentlab.shiftshapr.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.agentlab.shiftshapr.plist"

echo "Agent-lab root: $AGENT_LAB_ROOT"

# Ensure .venv exists
if [ ! -f "$AGENT_LAB_ROOT/.venv/bin/python" ]; then
  echo "Creating .venv and installing Flask..."
  python3 -m venv "$AGENT_LAB_ROOT/.venv"
  "$AGENT_LAB_ROOT/.venv/bin/pip" install flask
fi

# Ensure logs dir exists (launchd needs it)
mkdir -p "$AGENT_LAB_ROOT/logs"

# Update plist with actual path (in case agent-lab is elsewhere)
sed "s|/Users/shiftshapr/workspace/agent-lab|$AGENT_LAB_ROOT|g" "$PLIST_SRC" > "$PLIST_DEST"
echo "Installed plist to $PLIST_DEST"

# Unload if already loaded
launchctl bootout "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || true

# Load
echo "Loading launchd service..."
if launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"; then
  echo "Shiftshapr is running. Logs: $AGENT_LAB_ROOT/logs/shiftshapr.log"
else
  echo "Bootstrap failed. Try: launchctl bootstrap gui/\$(id -u) $PLIST_DEST"
  echo "Or run manually: nohup $AGENT_LAB_ROOT/.venv/bin/python $AGENT_LAB_ROOT/agents/shiftshapr/shiftshapr.py --port 8080 > $AGENT_LAB_ROOT/logs/shiftshapr.log 2>&1 &"
  exit 1
fi
