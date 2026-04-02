#!/usr/bin/env bash
# Cron: weekly preview (Sunday)
# Add to crontab: 0 18 * * 0 /path/to/agent-lab/scripts/cron-weekly-preview.sh
# Optional: SEND_BRIEF=1 + TELEGRAM_* or SLACK_DELIVERY_* for delivery

set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATE=$(date +%Y%m%d)

cd "$AGENT_LAB_ROOT"
[ -f .env ] && set -a && source .env && set +a
python3 agents/protocol/protocol_agent.py --protocol weekly-preview 2>&1 | tee -a logs/cron-weekly-preview.log

if [ "${SEND_BRIEF:-0}" = "1" ] && [ -f "logs/weekly_preview_${DATE}.md" ]; then
  python3 scripts/send-brief.py "logs/weekly_preview_${DATE}.md" 2>&1 | tee -a logs/cron-weekly-preview.log
fi
