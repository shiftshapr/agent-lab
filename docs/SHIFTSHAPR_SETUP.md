# Shiftshapr Setup

Your digital twin via Telegram. Runs on MacMini with webhook. Logs all actions to `logs/shiftshapr_audit.log`.

## Prerequisites

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- Flask: `python3 -m venv .venv && .venv/bin/pip install flask`
- Public HTTPS URL for webhook (ngrok, Cloudflare Tunnel, or your domain)

## 1. Run the webhook server

```bash
cd /path/to/agent-lab
# First time: create venv and install Flask
python3 -m venv .venv && .venv/bin/pip install flask

# Run Shiftshapr (use venv python)
.venv/bin/python agents/shiftshapr/shiftshapr.py --port 8080
```

Or with launchd (see below).

## 2. Expose with ngrok (local dev)

```bash
ngrok http 8080
# Copy the https://xxx.ngrok.io URL
```

## 3. Set the Telegram webhook

```bash
python scripts/set-telegram-webhook.py https://your-ngrok-url.ngrok.io/webhook
```

Or set `SHIFTSHAPR_WEBHOOK_URL` in `.env` and run without args.

## 4. Chat with Shiftshapr

Send messages to your bot in Telegram:

- `/deadlines` — Upcoming deadlines from opportunities ledger
- `/opportunities` — Open opportunities (grants, etc.)
- `/brief` — Run daily prep (calendar + email)
- `/add Name | type | YYYY-MM-DD` — Add opportunity (e.g. `/add XYZ Grant | grant | 2025-04-15`)
- `/remember <note>` — Add to your profile (preferences, how you like things)
- `/help` — List commands
- **PDF + caption** — Send a PDF with caption "add to my graph" to ingest into your meta-layer world model (requires pypdf: `pip install pypdf`)
- **`/bride <YouTube URL>`** — Append a **Bride of Charlie** episode to `projects/monuments/bride_of_charlie/input/youtube_links.txt` and run **`run_full_workflow.py`** on the Mac that hosts the webhook (long: fetch → analysis → Neo4j). You’ll get a Telegram message when it finishes (log tail + `logs/bride_workflow_*.log`). Natural language also works if the message includes **Bride** + **Charlie** and a YouTube link on the **same message**. Set **`BRIDE_TG_RUN_WORKFLOW=0`** in `.env` to only save the link and run the workflow yourself later.
- Free-form — Ask anything; DeerFlow responds with your context

## Long DeerFlow jobs (DP drafts, many MCP steps)

If Telegram shows **"No response."** or nothing useful after a long free-form request:

| Variable | Purpose |
|----------|---------|
| `SHIFTSHAPR_DEERFLOW_TIMEOUT` | Seconds for DeerFlow (default **420**). Use **1200**–**1800** for long desirable-property / multi-tool runs. |
| `DEERFLOW_TASK_RECURSION_LIMIT` | Max LangGraph steps (default **100**). Raise to **200**–**300** if the run stops mid-way without an error. |
| `SHIFTSHAPR_DEERFLOW_ACK` | Set to **1** to send an immediate “Working on it…” so the chat doesn’t look frozen. |

Restart the Shiftshapr webhook after changing `.env`.

DeerFlow’s `chat()` helper now falls back to the **final state** (last AI text, or a preview of the last **tool** output) when the stream never ends with a normal assistant message—so you should get a substantive reply instead of a blank line.

## 5. User context (so it "knows you")

Edit `data/shiftshapr_context.json` or use `/remember`:

```json
{
  "communication_style": "Concise, actionable. Prefer bullet points.",
  "priorities": ["grants", "partnerships"],
  "key_projects": ["Project A", "Project B"],
  "preferences": ["I prefer morning briefs", "Flag deadlines in bold"]
}
```

Shiftshapr includes this in every DeerFlow prompt.

## 6. Opportunities ledger

- **Add manually**: `python scripts/ledger-add.py "Grant Name" --type grant --deadline 2025-04-15`
- **From email**: After `cron-email-opportunity` runs, `python scripts/ledger-from-email.py`
- **Via Telegram**: `/add Name | type | YYYY-MM-DD`

## 7. Audit log

Every action is logged to `logs/shiftshapr_audit.log`:

```json
{"timestamp": "...", "action": "MESSAGE_RECEIVED", "chat_id": "...", "text": "..."}
{"timestamp": "...", "action": "CMD_DEADLINES", ...}
{"timestamp": "...", "action": "REPLY_SENT", "length": 150}
```

## 8. launchd (MacMini — run on boot)

Create `~/Library/LaunchAgents/com.agentlab.shiftshapr.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.agentlab.shiftshapr</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/YOUR_USER/workspace/agent-lab/.venv/bin/python</string>
    <string>/Users/YOUR_USER/workspace/agent-lab/agents/shiftshapr/shiftshapr.py</string>
    <string>--port</string>
    <string>8080</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/YOUR_USER/workspace/agent-lab</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/YOUR_USER/workspace/agent-lab/logs/shiftshapr.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/YOUR_USER/workspace/agent-lab/logs/shiftshapr.err</string>
</dict>
</plist>
```

Replace `YOUR_USER` with your username. Then:

```bash
launchctl load ~/Library/LaunchAgents/com.agentlab.shiftshapr.plist
```

## 9. Restrict to your chat

Set `TELEGRAM_CHAT_ID` in `.env`. Shiftshapr only responds to messages from that chat.

## 10. Cron: sync email opportunities to ledger

Add to crontab after `cron-email-opportunity`:

```bash
# After email opportunity at 7am
5 7 * * * cd /path/to/agent-lab && python scripts/ledger-from-email.py
```
