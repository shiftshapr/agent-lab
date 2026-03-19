#!/usr/bin/env bash
# Cron: daily prep (calendar + email brief)
# Add to crontab: 0 6 * * * /path/to/agent-lab/scripts/cron-daily-prep.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$AGENT_LAB_ROOT"
python3 agents/protocol/protocol_agent.py --protocol daily-prep 2>&1 | tee -a logs/cron-daily-prep.log
