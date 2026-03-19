# Daily Prep + Messaging Monitor Agent — Plan

## What Exists Today

### 1. Email / Calendar / Day Prep — **Partial**

**Notes:** [`docs/hermes-setup-guide.md`](../docs/hermes-setup-guide.md)

| Component | Status | Notes |
|-----------|--------|-------|
| **Hermes Agent** | Installed | `~/.hermes/hermes-agent` — coordination agent for daily briefs |
| **Morning briefing** | Designed | Cron: "Every morning at 6am, review my calendar for today, prepare briefings for each meeting, list my to-dos, and send me the summary on Telegram" |
| **Calendar** | MCP planned | Zoho Calendar MCP — needs OAuth setup or Zapier MCP |
| **Email** | Not in notes | Hermes guide does **not** mention email — only calendar + to-dos |
| **Delivery** | Telegram | Via `hermes gateway` |
| **Hermes Python stub** | `agents/hermes/hermes.py` | Builds brief from task queue only — no calendar/email integration |

**Gaps:** Hermes guide assumes calendar + to-dos via MCP; email is not specified. Need to add:
- Gmail/Outlook MCP (or similar) for email ingestion
- Unified morning brief that pulls from calendar + email + to-dos

---

### 2. Slack — **Partial**

| Component | Status | Notes |
|-----------|--------|-------|
| **deer-flow Slack channel** | Implemented | `framework/deer-flow/backend/src/channels/slack.py` |
| **Purpose** | IM bridge | Connects DeerFlow agent to Slack — **receive/send** messages, not monitor/aggregate |
| **Config** | `config.yaml` | `bot_token`, `app_token` (Socket Mode) |
| **Monitor agent** | Stub | `agents/monitor/monitor_agent.py` lists X, LinkedIn, Reddit — **not Slack** |

**Gaps:** Slack is an inbound channel for DeerFlow, not a monitored source for digests. To add Slack monitoring:
- Add Slack as a **source** to the monitor agent (read channels, unread DMs, threads)
- Use Slack Events API or Web API for read-only access

---

### 3. Discord — **Not in repo**

| Component | Status | Notes |
|-----------|--------|-------|
| **Discord** | Not present | No Discord channel or monitor in agent-lab or deer-flow |

**Gaps:** Full greenfield — need Discord bot/channel or MCP for monitoring.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Morning Prep Agent (Hermes)                                                 │
│  - Calendar (Zoho MCP)                                                       │
│  - Email (TBD: Gmail/Outlook MCP)                                            │
│  - To-dos (TBD: task queue / Notion / Todoist)                               │
│  → Daily brief → Telegram                                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Messaging Monitor Agent                                                     │
│  - Slack (read channels, DMs, threads) — NEW                                │
│  - Discord (read servers, DMs) — NEW                                         │
│  - X, LinkedIn, Reddit (existing plan in monitor_agent.py)                  │
│  → Digest / candidate replies / opportunity list                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Complete Email + Calendar Day Prep

1. **Add email to Hermes**
   - Add Gmail MCP or Outlook MCP to `~/.hermes/config.yaml`
   - Update Hermes prompt: "Include unread/important emails from today"
   - Test: `hermes` → "What's on my calendar and what emails need attention today?"

2. **Wire Hermes to calendar**
   - Finish Zoho Calendar MCP setup (or Zapier MCP)
   - Ensure Hermes can read today's events and build briefings

3. **Unify brief**
   - Extend `agents/hermes/hermes.py` or Hermes config to pull:
     - Calendar events
     - Email summary
     - To-dos (from queue or external MCP)

4. **Verify cron**
   - Cron at 6am → Hermes → Telegram

---

### Phase 2: Slack Monitoring

1. **Extend monitor agent**
   - Add Slack to `agents/monitor/monitor_agent.py` SOURCES
   - Use `slack-sdk` (already in deer-flow) for read-only access

2. **Slack read scope**
   - Decide: channels only, DMs, threads, or all
   - Use `conversations.history`, `conversations.list`, etc.
   - Filter: unread, mentions, @mentions

3. **Output**
   - Digest: "Unread mentions and threads in Slack"
   - Optional: candidate replies (like X/LinkedIn)

4. **Config**
   - Reuse Slack tokens from deer-flow or add separate monitor config

---

### Phase 3: Discord Monitoring

1. **Discord integration**
   - Option A: Discord MCP (if available)
   - Option B: `discord.py` bot with read-only intents
   - Option C: Discord API + `requests`/`httpx`

2. **Scopes**
   - Servers, channels, DMs
   - Unread, mentions

3. **Add to monitor agent**
   - Add Discord to SOURCES
   - Same output types: digest, candidate replies

---

### Phase 4: Unified Daily Brief (Optional)

- Single morning brief: Calendar + Email + To-dos + Slack/Discord unread summary
- Delivered via Telegram (or Slack DM if preferred)

---

## Meeting & Response Workflow (User Requirements)

### Escalation if Not Acknowledged

- Pre-meeting reminders escalate if user doesn't acknowledge
- Example: 15 min → 5 min → repeat at 5 min if no ack
- Configurable: number of repeats, interval, escalation intensity

### Proposed Responses (Approve / Edit / Deny)

- Agent **proposes** responses for:
  - Meeting conflicts (decline, propose new time, tentative)
  - Email replies
  - Slack/Discord replies
  - Calendar actions (accept, decline, propose alternative)
- User can: **approve**, **edit**, or **deny** each proposal
- No execution until user approves

### Publish Agent — Execution Only When Initiated

- **Publish Agent** (`agents/publish/publish_agent.py`) is the **only** agent with external write capabilities
- All execution flows through it: replies, calendaring, etc.
- **User-initiated only** — no background autonomous publishing
- Flow: Monitor/Hermes proposes → User approves/edits/denies → User explicitly triggers Publish Agent to execute
- Publish Agent must support:
  - Sending replies (email, Slack, Discord)
  - Calendar actions (create event, update, decline, accept)
  - All actions logged to `logs/publish_audit.log`

### Weekly Preview (Sunday)

- **When:** Beginning of week, Sunday
- **Content:** Preview of entire upcoming week
  - All meetings (with briefings for important ones)
  - Key deadlines, milestones
  - Blocked time, travel, etc.
- **Delivery:** Telegram (or preferred channel)

---

## Quick Reference

| Doc | Purpose |
|-----|---------|
| `docs/hermes-setup-guide.md` | Hermes setup, Telegram, Zoho Calendar, morning briefing |
| `agents/hermes/hermes.py` | Hermes Python stub (task-based brief) |
| `agents/monitor/monitor_agent.py` | Monitor stub (X, LinkedIn, Reddit — add Slack/Discord) |
| `agents/publish/publish_agent.py` | Publish Agent — only agent with write; user-initiated execution |
| `framework/deer-flow/backend/src/channels/slack.py` | Slack IM channel (send/receive, not monitor) |
| `framework/deer-flow/extensions_config.json` | MCP servers for PAI agents (Slack, JAUmemory, Stripe, Phantom) |
| `docs/PAI_MCP_SETUP.md` | PAI MCP setup and env vars |
| `docs/EMAIL_OPPORTUNITY_SEARCH_WORKFLOW.md` | Email/link search for opportunities, Zoho View/Publish |

---

## Next Actions

1. [ ] Add email MCP to Hermes and test
2. [ ] Complete Zoho Calendar MCP setup
3. [ ] Extend monitor agent: add Slack as source
4. [ ] Implement Discord integration (MCP or bot)
5. [ ] Decide: single unified brief vs separate morning + messaging digests
6. [ ] Implement escalation for unacknowledged meeting reminders
7. [ ] Add proposed-response flow (approve/edit/deny) to Monitor/Hermes
8. [ ] Extend Publish Agent: replies (email, Slack, Discord), calendar actions
9. [ ] Add Sunday weekly preview cron
