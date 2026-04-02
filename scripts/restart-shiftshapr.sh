#!/usr/bin/env bash
# Restart Shiftshapr (launchd). Run from agent-lab root: ./scripts/restart-shiftshapr.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.agentlab.shiftshapr.plist"

if [ ! -f "$PLIST" ]; then
  echo "Shiftshapr plist not found. Run ./scripts/setup-shiftshapr-launchd.sh first."
  exit 1
fi

echo "Restarting Shiftshapr..."
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Done. Logs: $AGENT_LAB_ROOT/logs/shiftshapr.log"
