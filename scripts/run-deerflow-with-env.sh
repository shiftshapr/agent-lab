#!/usr/bin/env bash
# Run DeerFlow with agent-lab .env loaded (for MCP servers: Slack, Stripe, Phantom, JAUmemory)
# Usage: ./scripts/run-deerflow-with-env.sh [make target]
# Example: ./scripts/run-deerflow-with-env.sh dev

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEER_FLOW_DIR="$AGENT_LAB_ROOT/framework/deer-flow"

# Load agent-lab .env
if [ -f "$AGENT_LAB_ROOT/.env" ]; then
  set -a
  source "$AGENT_LAB_ROOT/.env"
  set +a
  echo "[run-deerflow] Loaded .env from agent-lab root"
else
  echo "[run-deerflow] Warning: No .env found at $AGENT_LAB_ROOT/.env"
fi

# Ensure extensions_config exists
if [ ! -f "$DEER_FLOW_DIR/extensions_config.json" ]; then
  echo "[run-deerflow] Error: extensions_config.json not found at $DEER_FLOW_DIR/extensions_config.json"
  exit 1
fi

cd "$DEER_FLOW_DIR"
TARGET="${1:-dev}"
echo "[run-deerflow] Running: make $TARGET"
make "$TARGET"
