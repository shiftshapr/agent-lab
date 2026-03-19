# Email & Link Opportunity Search Workflow

Uses **Zoho View MCP** (drafter) and **Zoho Publish MCP** (publisher) for calendar and emails. Search emails and links for project opportunities and items needing response.

## Components

| MCP | Role | Capabilities |
|-----|------|--------------|
| **Zoho View** (`ZOHO_VIEW_MCP_URL`) | Drafter / Read | Search emails, read calendar, extract links |
| **Zoho Publish** (`ZOHO_PUBLISH_MCP_URL`) | Publisher / Write | Send emails, create/update calendar events |

## Workflow: Search Emails for Opportunities

### 1. Search emails

Use Zoho View MCP to:
- Search inbox by keyword, sender, date range
- Filter unread / important
- Extract links from email bodies

### 2. Extract and classify links

From search results:
- Parse URLs from email content
- Optionally fetch link metadata (title, description)
- Classify by project (e.g. grants, partnerships, product, community)

### 3. Identify opportunities

Per project, flag:
- Grants, fellowships, hackathons
- Partnership / collaboration requests
- Product feedback or feature requests
- Community or speaking opportunities
- Deadlines and follow-ups

### 4. Identify items needing response

- Unread emails with no reply
- Threads where you're mentioned
- Time-sensitive requests
- Meeting invites pending response

### 5. Draft responses (via Publish Agent)

- Agent proposes replies using Zoho View context
- You approve / edit / deny
- **Publish Agent** (Zoho Publish MCP) executes only when you initiate

## Project tags

Define project tags so the agent can classify opportunities:

```
projects:
  - name: grants
    keywords: [grant, fellowship, funding, RFP, proposal]
  - name: partnerships
    keywords: [partnership, collaborate, integrate, pilot]
  - name: product
    keywords: [feedback, feature, bug, support]
  - name: community
    keywords: [speaking, panel, webinar, conference]
```

Store in `~/.hermes/config.yaml` or a project config file the agent reads.

## Example prompts (for Hermes / DeerFlow)

- *"Search my emails from the last 7 days for opportunities matching my projects: grants, partnerships, product feedback. List links mentioned and flag items I need to respond to."*
- *"Find unread emails with links. Extract the URLs and classify by opportunity type."*
- *"What emails need my response today? Draft replies for the top 3."*

## Slack CLI

Slack CLI is installed at `~/.local/bin/slack`. Add to PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Then authorize:

```bash
slack login
```

Use Slack CLI for scripting (e.g. post digests to a channel, trigger workflows).

## Cron / scheduled runs

To run the opportunity search daily:

```bash
# Add to crontab (e.g. 7am):
0 7 * * * cd /path/to/agent-lab && ./scripts/run-deerflow-with-env.sh dev --task "Search emails for opportunities and items needing response"
```

Or use Hermes cron: *"Every morning at 7am, search my emails for opportunities and things I need to respond to. Send the digest to Telegram."*

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Zoho View MCP (Drafter)                                         │
│  - Search emails                                                 │
│  - Read calendar                                                 │
│  - Extract links from content                                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Monitor / Hermes Agent                                          │
│  - Classify opportunities by project                              │
│  - Flag items needing response                                   │
│  - Propose draft replies                                         │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  Publish Agent (Zoho Publish MCP)                                │
│  - Send emails (user-initiated)                                  │
│  - Create/update calendar (user-initiated)                       │
└─────────────────────────────────────────────────────────────────┘
```
