# Messaging integrations (Discord, WhatsApp, Signal)

This document describes how agent-lab relates to **Discord**, **WhatsApp**, and **Signal**, and how **read** vs **post** access is usually separated (same pattern as MCP tools: Zoho read vs publish, Slack scopes, etc.).

## Plain text on all channels

Outbound text from Shiftshapr, `scripts/send-brief.py`, meeting reminders, and DeerFlow’s Telegram/Slack channels **passes through** `format_channel_message()` so markdown tables and tags are not shown raw. See `docs/DELIVERY_SETUP.md` and `framework/deer-flow/backend/app/utils/channel_message_format.py`.

---

## Discord (existing server)

**In repo today:** `framework/deer-flow/extensions_config.json` includes a **`discord`** MCP server (`npx -y discord-mcp@latest`) with `DISCORD_BOT_TOKEN` in `.env`.

**Taking over an existing Discord** (high level):

1. **Create a bot application** in the [Discord Developer Portal](https://discord.com/developers/applications) and copy the **bot token** into `.env` as `DISCORD_BOT_TOKEN`.
2. **Invite the bot** to your server with OAuth2 URL Generator — enable scopes **`bot`** (and **`applications.commands`** if the MCP uses slash commands). Grant permissions your workflows need (e.g. **Read Message History**, **Send Messages**, **Read Messages/View Channels**).
3. **Enable the server** in `extensions_config.json` (`"enabled": true` for `discord`) and restart DeerFlow so agents can call Discord MCP tools.
4. **Read vs post:** the MCP package exposes separate tools (read history vs send message). Use the same pattern as other MCPs: **read-only** tools for monitoring, **write** tools only when posting or replying. Exact tool names depend on `discord-mcp` — inspect the MCP tool list in Cursor/DeerFlow after connect.

**Skills:** `framework/deer-flow/skills/public/discord-digest/SKILL.md` (digest workflow).

---

## WhatsApp

There is **no WhatsApp integration in this repo** yet. Realistic options:

**Phone number for WhatsApp Business / Cloud API:** Meta often **rejects or blocks** registration on **VoIP and virtual numbers** (including many **Google Voice** numbers). For reliable WABA onboarding, use a **standard mobile or landline** that can receive **SMS or voice OTP**. Google Voice may work in rare cases but is **not** dependable for verification.

| Approach | Read | Post | Notes |
|----------|------|------|--------|
| **WhatsApp Business Cloud API** (Meta) | Yes (webhooks) | Yes | Requires Meta Business verification, phone number; official and stable. |
| **Twilio WhatsApp** | Via webhooks | Yes | Business account; official API. |
| **Unofficial “WhatsApp Web” libraries** | Varies | Varies | High ban/TOS risk; not recommended for production. |

**Recommendation:** If you need WhatsApp in agent-lab, add a **small MCP server** (or HTTP bridge) that wraps your chosen **official** API, with **two** clear capabilities: `whatsapp_read_*` (list messages / webhooks) and `whatsapp_send_*` (send template or session message), and register it in `extensions_config.json` like Slack/Discord.

---

## Signal

There is **no Signal integration in this repo** yet. Common self-hosted pattern:

- **[signal-cli](https://github.com/AsamK/signal-cli)** — CLI for register, send, receive.
- **[signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api)** — HTTP wrapper around signal-cli for send/receive from automation.

**Recommendation:** Run signal-cli (or the REST API container) on your MacMini, then add a **thin MCP** or **HTTP tool** in agent-lab with:

- **Read:** poll or webhook endpoint for incoming messages (expose only what you need).
- **Post:** HTTP `POST` to send messages to a number or group.

Keep **read** and **post** as separate tools or separate env flags so agents match your current safety pattern.

---

## Summary

| Channel   | Status in agent-lab | Next step |
|-----------|---------------------|-----------|
| Telegram / Slack | Supported; plain-text formatting enabled | `CHANNEL_MESSAGE_RAW` if debugging |
| Discord   | MCP configured | Bot invite + permissions + restart DeerFlow |
| WhatsApp  | **Hybrid:** Draft Editor (Promos) → destination &ldquo;WhatsApp · hybrid&rdquo; → inline copy/paste + wa.me; API blast not in repo | Optional: official API + MCP later |
| Signal    | Not implemented | signal-cli-rest-api + MCP or HTTP bridge |

If you want a concrete WhatsApp or Signal MCP scaffold (stdio server stub + `extensions_config.json` snippet), say which API (Meta Cloud vs Twilio vs signal-cli-rest-api) you plan to use.
