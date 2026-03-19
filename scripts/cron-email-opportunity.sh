#!/usr/bin/env bash
# Cron: email opportunity search
# Add to crontab: 0 7 * * * /path/to/agent-lab/scripts/cron-email-opportunity.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$AGENT_LAB_ROOT"
python3 agents/protocol/protocol_agent.py --protocol email-opportunity 2>&1 | tee -a logs/cron-email-opportunity.log
