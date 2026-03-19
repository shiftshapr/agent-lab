# PAI Agents — MCP Setup

The agent-lab PAI (Personal AI) agents run on DeerFlow and use MCP servers configured in `framework/deer-flow/extensions_config.json`. This gives them access to Slack, JAUmemory, Stripe, and Phantom.

## Configured MCPs

| MCP | Purpose | Env vars |
|-----|---------|----------|
| **Zoho View** | Search emails, read calendar, extract links (drafter) | `ZOHO_VIEW_MCP_URL` |
| **Zoho Publish** | Send emails, create/update calendar (publisher) | `ZOHO_PUBLISH_MCP_URL` |
| **Slack (multi-workspace)** | Read channels, threads, send messages | `SLACK_BOT_TOKEN_N`, `SLACK_TEAM_ID_N`, `SLACK_CHANNEL_IDS_N` per workspace |
| **JAUmemory** | Persistent memory for agents | (auth via JAUmemory if required) |
| **Stripe** | Customers, payments, invoices, subscriptions | `STRIPE_SECRET_KEY` |
| **Phantom** | Wallet addresses, balances, transfers, signing | `PHANTOM_APP_ID` |

## Setup

### 1. Add env vars to `.env`

Copy from `.env.example` and fill in:

```bash
# Slack (from api.slack.com/apps)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_TEAM_ID=T01234567
SLACK_CHANNEL_IDS=C01234567,C76543210

# Stripe (use Restricted API Key from dashboard.stripe.com/apikeys)
STRIPE_SECRET_KEY=sk_live_...

# Phantom (from phantom.com/portal → Create App → App ID)
PHANTOM_APP_ID=your_app_id
```

### 2. Slack setup (multi-workspace)

**One app, install in each workspace.** Each workspace gets its own token and team ID.

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From scratch.
2. Add OAuth scopes: `channels:history`, `channels:read`, `chat:write`, `groups:history`, `im:history`, `mpim:history`.
3. **For each workspace** you want to monitor:
   - Install the app to that workspace (Install App → Install to [Workspace Name]).
   - Copy the **Bot User OAuth Token** (`xoxb-...`) → `SLACK_BOT_TOKEN_1`, `SLACK_BOT_TOKEN_2`, etc.
   - Get **Team ID** from workspace URL (`app.slack.com/client/T01234567/...`) → `SLACK_TEAM_ID_1`, etc.
   - Optionally set **Channel IDs** (comma-separated) → `SLACK_CHANNEL_IDS_1`, etc.
4. Add each workspace to `extensions_config.json` as `slack-1`, `slack-2`, ... Enable only the ones you've configured.
5. To add more workspaces: copy a `slack-N` block, increment N, add env vars to `.env`, set `enabled: true`.

### 3. Stripe setup

Use a [Restricted API Key](https://docs.stripe.com/keys#create-restricted-api-secret-key) to limit what the agent can do. Create one at [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys).

### 4. Phantom setup

1. Go to [phantom.com/portal](https://phantom.com/portal) and sign in.
2. Create App → add redirect URL `http://localhost:8080/callback`.
3. Copy the **App ID** from the Phantom Connect tab.

### 5. JAUmemory

No extra env vars needed if you use the default setup. If JAUmemory requires auth, add credentials to its `env` block in `extensions_config.json`.

## Load env when running DeerFlow

DeerFlow resolves `$VAR` in `extensions_config.json` via `os.getenv`. Use the helper script to load agent-lab `.env`:

```bash
# From agent-lab root:
./scripts/run-deerflow-with-env.sh dev
```

Or manually:

```bash
cd framework/deer-flow
set -a && source ../../.env && set +a
make dev
```

## Config location

- **File:** `framework/deer-flow/extensions_config.json`
- DeerFlow looks for it in the project root (parent of `backend/`).
- To disable an MCP, set `"enabled": false` for that server.

## Verifying

After starting DeerFlow, the MCP tools should appear in the agent's tool list. Check logs for:

```
Initializing MCP client with 4 server(s)
Successfully loaded N tool(s) from MCP servers
```
