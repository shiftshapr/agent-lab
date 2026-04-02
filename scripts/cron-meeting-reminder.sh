#!/usr/bin/env bash
# Cron: meeting reminders (15 min → 5 min if no ack)
# Add to crontab: */5 6-22 * * * /path/to/agent-lab/scripts/cron-meeting-reminder.sh
# Runs every 5 min between 6am–10pm

set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$AGENT_LAB_ROOT"
[ -f .env ] && set -a && source .env && set +a
python3 scripts/meeting-reminder.py 2>&1 | tee -a logs/cron-meeting-reminder.log
# Poll Telegram for "ack" replies (skips 5-min escalation)
python3 scripts/telegram-ack-poll.py 2>&1 | tee -a logs/cron-meeting-reminder.log
