#!/usr/bin/env bash
# Restart DeerFlow (clears ports, starts in background). Run from agent-lab root.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../framework/deer-flow/scripts/restart-deerflow.sh"
