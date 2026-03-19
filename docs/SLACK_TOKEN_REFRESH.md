# Slack Token Refresh

Slack user tokens (xoxe.xoxp) expire every 12 hours. This script refreshes them automatically using refresh tokens.

## Setup

### 1. Create slack-tokens.json

```bash
cp scripts/slack-tokens.example.json scripts/slack-tokens.json
```

Edit `scripts/slack-tokens.json`. **No client_id/client_secret needed** — App Configuration Tokens use `tooling.tokens.rotate` which only needs refresh_token:

```json
{
  "workspaces": [
    {
      "name": "Metagov",
      "refresh_token": "xoxe-1-...",
      "team_id": "TMQ3PKXT9"
    },
    {
      "name": "AI alignment",
      "refresh_token": "xoxe-1-...",
      "team_id": "T01641E1H6C"
    }
  ]
}
```

Add one entry per workspace. Get **refresh tokens** from your app's "Your App Configuration Tokens" page (Copy next to Refresh Token).

### 3. Run manually

```bash
python scripts/refresh-slack-tokens.py
```

This updates `.env` with new access tokens and `slack-tokens.json` with new refresh tokens.

### 4. Schedule with cron (every 6 hours)

```bash
crontab -e
```

Add:

```
0 */6 * * * cd /path/to/agent-lab && python scripts/refresh-slack-tokens.py
```

Or use launchd on macOS for a more robust schedule.

## Workspace order

Workspaces in `slack-tokens.json` map to `SLACK_BOT_TOKEN_1`, `SLACK_TEAM_ID_1`, etc. The order must match `extensions_config.json` (slack-1, slack-2, ...).

## Security

- `slack-tokens.json` contains secrets — add to `.gitignore` (already done)
- Never commit tokens to version control
