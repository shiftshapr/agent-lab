# Agent Lab Scaffolding

Scaffolding for daily prep, weekly preview, email opportunity search, and Slack digest.

## What Exists

### Protocols (run via `protocol_agent.py`)

| Protocol | Purpose | Output |
|----------|---------|--------|
| `daily-prep` | Morning brief: calendar, emails, to-dos | `logs/daily_prep_YYYYMMDD.md` |
| `weekly-preview` | Sunday preview of upcoming week | `logs/weekly_preview_YYYYMMDD.md` |
| `email-opportunity` | Search emails for opportunities & items needing response | `logs/email_opportunity_YYYYMMDD.md` |
| `slack-digest` | Unread/mentions across Slack workspaces | `logs/slack_digest_YYYYMMDD.md` |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run-deerflow-task.py` | One-shot DeerFlow agent invocation (loads .env, uses MCP) |
| `scripts/cron-daily-prep.sh` | Cron wrapper for daily prep |
| `scripts/cron-weekly-preview.sh` | Cron wrapper for weekly preview |
| `scripts/cron-email-opportunity.sh` | Cron wrapper for email opportunity search |

### Config

| File | Purpose |
|------|---------|
| `config/project_tags.yaml` | Project keywords for opportunity classification |

## Usage

### Run protocols manually

```bash
cd /path/to/agent-lab

# List protocols
python3 agents/protocol/protocol_agent.py --list

# Run daily prep
python3 agents/protocol/protocol_agent.py --protocol daily-prep

# Run weekly preview
python3 agents/protocol/protocol_agent.py --protocol weekly-preview

# Run email opportunity search
python3 agents/protocol/protocol_agent.py --protocol email-opportunity

# Run Slack digest
python3 agents/protocol/protocol_agent.py --protocol slack-digest
```

### Run DeerFlow task directly

```bash
python3 scripts/run-deerflow-task.py "What's on my calendar today?"
python3 scripts/run-deerflow-task.py "Search emails for grants" --output logs/custom.md
```

### Cron setup

```bash
# Edit crontab
crontab -e

# Add (adjust path to your agent-lab):
# Daily prep at 6am
0 6 * * * cd /Users/shiftshapr/workspace/agent-lab && ./scripts/cron-daily-prep.sh

# Email opportunity at 7am
0 7 * * * cd /Users/shiftshapr/workspace/agent-lab && ./scripts/cron-email-opportunity.sh

# Weekly preview Sunday 6pm
0 18 * * 0 cd /Users/shiftshapr/workspace/agent-lab && ./scripts/cron-weekly-preview.sh
```

## Requirements

- **DeerFlow backend deps**: Protocols use `run-deerflow-task.py` which invokes DeerFlowClient via `uv run`. Ensure `framework/deer-flow/backend` has deps installed (`uv sync`).
- **.env**: Agent-lab `.env` must have ZOHO_VIEW_MCP_URL, ZOHO_PUBLISH_MCP_URL, SLACK_BOT_TOKEN_1–7, etc.
- **DeerFlow config**: `framework/deer-flow/config.yaml` and `extensions_config.json` must exist.
- **MCP connectivity**: Zoho and Slack MCP servers must be reachable. If MCP fails to load, the task runner may exit with an error.

## Next Steps (not yet implemented)

1. **Hermes integration**: Wire Hermes to call daily-prep protocol or DeerFlowClient for unified brief.
2. **Proposed responses**: Approve/edit/deny flow for agent-drafted replies.
3. **Publish Agent**: Wire to Zoho Publish MCP; user-initiated execution only.
4. **Risk Reviewer**: LLM-based review before publish.
5. **Delivery**: Telegram/Slack DM delivery of briefs (Hermes gateway).
6. **Discord**: Add Discord monitoring if MCP available.
