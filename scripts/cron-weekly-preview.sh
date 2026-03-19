#!/usr/bin/env bash
# Cron: weekly preview (Sunday)
# Add to crontab: 0 18 * * 0 /path/to/agent-lab/scripts/cron-weekly-preview.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$AGENT_LAB_ROOT"
python3 agents/protocol/protocol_agent.py --protocol weekly-preview 2>&1 | tee -a logs/cron-weekly-preview.log
