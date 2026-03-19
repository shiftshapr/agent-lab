# Hermes Agent Setup Guide

Morning briefing + social monitoring workflow.

## What's Installed

- **Hermes Agent** at `~/.hermes/hermes-agent`
- **Config** at `~/.hermes/config.yaml`
- **Secrets** at `~/.hermes/.env` (Ollama local — MiniMax had insufficient balance)

## Next Steps (Manual)

### 1. Add Hermes to PATH

```bash
# Quick start (from agent-lab):
./scripts/hermes-start.sh chat    # Interactive chat
./scripts/hermes-start.sh gateway # Start Telegram gateway
./scripts/hermes-start.sh doctor  # Diagnose

# Or add to ~/.zshrc:
echo 'export PATH="$HOME/.hermes/hermes-agent/venv/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 2. Configure Telegram

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram, then:

```bash
# Add to ~/.hermes/.env:
TELEGRAM_BOT_TOKEN=your_token_here

# Set your Telegram user ID (required for delivery)
# Send /start to your bot, then get your ID via @userinfobot
TELEGRAM_ALLOWED_USERS=your_telegram_user_id
```

Then run:

```bash
hermes gateway setup   # Interactive — select Telegram
hermes gateway        # Start the gateway (keeps running)
```

### 3. Create Morning Briefing Cron Job

Once the gateway is running, in Telegram (or CLI) say:

> Every morning at 6am, review my calendar for today, prepare briefings for each meeting, list my to-dos, and send me the summary on Telegram.

Or create via CLI:

```bash
hermes chat
# Then: Schedule a cron job for 6am daily that sends a morning briefing to Telegram.
```

### 4. Add Zoho Calendar (MCP)

1. Get Zoho OAuth credentials from [Zoho API Console](https://api-console.zoho.com/)
2. Add to `~/.hermes/config.yaml` under `mcp_servers`:

```yaml
mcp_servers:
  zoho_calendar:
    command: npx
    args: ["-y", "zoho-mcp-server"]  # or use Zapier MCP for Zoho
    env:
      ZOHO_CLIENT_ID: ""
      ZOHO_CLIENT_SECRET: ""
```

Or use [Zapier MCP](https://zapier.com/mcp/zoho-calendar-1) for easier setup.

### 5. Set Up XRSS (X/Twitter)

XRSS is free, self-hosted. Converts X feeds to RSS.

```bash
git clone https://github.com/Thytu/XRSS.git
cd XRSS
# Follow XRSS README — requires X credentials (login, not API)
# Output: RSS feed at http://localhost:8000/feed.xml
```

Then add an RSS MCP to Hermes so it can read the feed.

### 6. Set Up Social Monitoring Cron

In Hermes or Telegram:

> Every hour, check for new content on X, LinkedIn, and Reddit that I should comment on for thought leadership. Also find grants, fellowships, and hackathons in my areas of interest. Prepare draft replies and meta-layer directions for opportunities.

## Quick Test

```bash
hermes
# Then: What's on my calendar today?
```

## Files

| File | Purpose |
|-----|---------|
| `~/.hermes/config.yaml` | Model, terminal, toolsets |
| `~/.hermes/.env` | API keys, Telegram token |
| `~/.hermes/cron/` | Scheduled jobs (created on first use) |

## Slack CLI

Installed via `curl -fsSL https://downloads.slack-edge.com/slack-cli/install.sh | bash`. Add to PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
slack login
```

## Troubleshooting

- `hermes doctor` — diagnose issues
- `hermes config` — view current config
- `hermes config edit` — edit config
