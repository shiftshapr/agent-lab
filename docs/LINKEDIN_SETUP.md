# LinkedIn & X Setup (Posting & Reply Monitoring)

Agent Lab can post to LinkedIn and X (Twitter) and monitor replies via Playwright browser automation.

## 0. Playwright MCP browsers (required for DeerFlow / `npx @playwright/mcp`)

The MCP server uses `npx -y @playwright/mcp@latest`, which pins its own Playwright version. **System Chrome is not used** — you must download the matching Chromium build once (and again when `@playwright/mcp` bumps its Playwright dependency). The ensure script uses a small local package at `scripts/playwright-mcp-browsers/` so installs stay fast and avoid npm’s “install dependencies first” warning.

From the agent-lab root:

```bash
./scripts/ensure-playwright-mcp-browsers.sh
```

`./scripts/restart-deerflow.sh` runs this automatically before starting DeerFlow.

If this step is skipped, tools fail with errors like “browser not found” or “Chrome not found” even when Google Chrome is installed.

## 1. One-time login (session persistence)

Run the login script to save your LinkedIn and X session:

```bash
cd /path/to/agent-lab
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python scripts/linkedin-login-setup.py
```

- A browser opens to linkedin.com — log in (including 2FA)
- Press Enter, then a second tab opens to x.com — log in
- When both show your feed, press Enter again
- Session is saved to `data/linkedin_state.json` (one file for both)

## 2. Configure .env

Ensure these are in `.env` (paths may already be set):

```
PLAYWRIGHT_MCP_WRAPPER=/path/to/agent-lab/scripts/playwright-mcp-with-linkedin.sh
LINKEDIN_STORAGE_STATE=/path/to/agent-lab/data/linkedin_state.json
```

Use full absolute paths. The login script prints the storage state path after saving.

## 3. Add people to tag

Via Telegram:

- `/add_mention John Smith` — add someone to your LinkedIn tagging list
- `/linkedin_mentions` — list current mentions

Or edit `data/shiftshapr_context.json` and add to `linkedin_mentions`:

```json
"linkedin_mentions": ["John Smith", "Jane Doe"]
```

## 4. Schedule reply monitoring

Add to crontab (runs at 9am, 2pm, 6pm):

```bash
0 9,14,18 * * * cd /path/to/agent-lab && ./scripts/cron-linkedin-replies.sh
```

Or copy from `scripts/crontab.example`:

```bash
(crontab -l 2>/dev/null; grep linkedin scripts/crontab.example) | crontab -
```

Set `SEND_BRIEF=1` and Telegram credentials in `.env` to receive the digest.

## 5. Restart DeerFlow (if using UI)

If you use the DeerFlow web UI, restart so Playwright loads the session:

```bash
./scripts/restart-deerflow.sh
```

For Telegram/Shiftshapr, no restart needed — each request loads config fresh.

## Usage

- **Post**: "Post this to LinkedIn: [your text]" — agent uses Playwright to post
- **Check replies**: "Check my LinkedIn replies" or "Use linkedin-replies skill"
- **Tag**: When posting, the agent sees `linkedin_mentions` and can @mention those people

## Adding new platforms

To add another site (e.g. GitHub, another social network):

```bash
./scripts/add-platform.sh https://example.com
```

Chrome opens with the URL. Log in, then run:

```bash
.venv/bin/python scripts/x-login-via-chrome.py
```

The persistent profile keeps existing logins (LinkedIn, X, ChatGPT) — you only log into the new site.

## Re-login when session expires

LinkedIn sessions expire. Re-run the flow when posting fails or you get logged out.
