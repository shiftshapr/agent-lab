#!/usr/bin/env bash
# Cron: check LinkedIn replies and send digest to Telegram
# Add to crontab: 0 9,14,18 * * * /path/to/agent-lab/scripts/cron-linkedin-replies.sh
# Runs at 9am, 2pm, 6pm — adjust as needed

set -e
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LAB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATE=$(date +%Y%m%d)
TIME=$(date +%H%M)

cd "$AGENT_LAB_ROOT"
[ -f .env ] && set -a && source .env && set +a

# Skip if no LinkedIn session
if [ -z "$LINKEDIN_STORAGE_STATE" ] || [ ! -f "$LINKEDIN_STORAGE_STATE" ]; then
  echo "[cron-linkedin-replies] No LINKEDIN_STORAGE_STATE — run scripts/linkedin-login-setup.py first" >> logs/cron-linkedin-replies.log
  exit 0
fi

OUTPUT="logs/linkedin_replies_${DATE}_${TIME}.md"
python3 scripts/run-deerflow-task.py \
  "Use the linkedin-replies skill: check my LinkedIn feed for replies and comments on my recent posts. Summarize who commented and what they said. Flag any that need a response." \
  --output "$OUTPUT" \
  --timeout 300 \
  2>&1 | tee -a logs/cron-linkedin-replies.log

# Send to Telegram if configured
if [ "${SEND_BRIEF:-0}" = "1" ] && [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ] && [ -f "$OUTPUT" ]; then
  python3 scripts/send-brief.py "$OUTPUT" --telegram 2>&1 | tee -a logs/cron-linkedin-replies.log
fi
