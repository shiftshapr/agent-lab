# Brief Delivery Setup

Send daily prep and weekly preview to Telegram or Slack.

## Readable text (markdown → plain)

Briefs and agent replies are **converted from markdown to plain text** before sending (tables become lines with ` · ` between cells, links show as `label (https://…)`, model tags like `<think>` are stripped). See `app/utils/channel_message_format.py` in DeerFlow. To debug with raw markdown, set `CHANNEL_MESSAGE_RAW=1` in `.env`.

**Cron / system `python3`:** `cron-daily-prep.sh` → `send-brief.py` needs the same packages as that formatter (or it falls back to a simpler strip). On macOS with Homebrew Python, install once: `python3 -m pip install -r requirements-cron.txt` (you may need `--break-system-packages` per PEP 668), or rely on the built-in fallback so **Telegram delivery still runs** even without `bs4`.

## Telegram

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Get your chat ID (send /start to your bot, then use [@userinfobot](https://t.me/userinfobot))
3. Add to `.env`:

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Slack

1. Use an existing Slack app token (e.g. SLACK_BOT_TOKEN_1) or create a dedicated one
2. Get the channel ID for delivery (right-click channel → View channel details → copy ID)
3. Add to `.env`:

```
SLACK_DELIVERY_CHANNEL_ID=C01234567
SLACK_DELIVERY_TOKEN=xoxb-...   # or use SLACK_BOT_TOKEN_1
```

## Enable Delivery in Cron

Add to `.env`:

```
SEND_BRIEF=1
```

Then the cron-daily-prep script will send the brief after generating it (to Telegram first if configured, else Slack).

## Manual Send

```bash
python3 scripts/send-brief.py logs/daily_prep_20260319.md --telegram
python3 scripts/send-brief.py logs/daily_prep_20260319.md --slack
python3 scripts/send-brief.py logs/daily_prep_20260319.md --both
```
