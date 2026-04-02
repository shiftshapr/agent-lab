#!/usr/bin/env bash
# Cron: daily prep (calendar + email brief)
# Add to crontab: 0 6 * * * /path/to/agent-lab/scripts/cron-daily-prep.sh
# Optional: set SEND_BRIEF=1 and TELEGRAM_* or SLACK_DELIVERY_* in .env to deliver

set -e
# Cron has minimal PATH; ensure uv, python3 are found
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATE=$(date +%Y%m%d)

cd "$AGENT_LAB_ROOT"
[ -f .env ] && set -a && source .env && set +a
python3 agents/protocol/protocol_agent.py --protocol daily-prep 2>&1 | tee -a logs/cron-daily-prep.log

# Optional delivery (if SEND_BRIEF=1 and Telegram/Slack configured)
if [ "${SEND_BRIEF:-0}" = "1" ] && [ -f "logs/daily_prep_${DATE}.md" ]; then
  python3 scripts/send-brief.py "logs/daily_prep_${DATE}.md" 2>&1 | tee -a logs/cron-daily-prep.log
fi
