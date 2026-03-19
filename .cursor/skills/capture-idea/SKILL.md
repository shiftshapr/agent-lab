---
name: capture-idea
description: >-
  Captures a product, agent, or monument idea into the repo ideas backlog from
  the current chat. Use when the user asks to capture an idea, park an idea,
  idea backlog, brain dump, feature wishlist, "note this for later", or
  similar—without turning it into a full decision log entry.
---

# Capture idea (backlog)

## Goal

Draft a **short, durable idea record** the user can paste into—or the agent can append to—the ideas ledger.

## Canonical file

**`docs/IDEAS_BACKLOG.md`** (agent-lab root). If missing, create it from the template in that file’s top comment or the structure below.

## Output format

One entry (newest at **top** of the `## Ideas` list unless user asks to append at bottom):

```markdown
### YYYY-MM-DD — <5–8 word title>

- **Idea:** One tight paragraph: what and why it might matter.
- **Tags:** e.g. `agent`, `monument`, `neo4j`, `comms`, `skill` (optional)
- **Inspired by:** This Cursor chat / meeting / reading (optional)
- **Next step:** One concrete next action, or "TBD"
```

No secrets. No client PII unless user explicitly wants it.

## When NOT to use this skill

- The user is locking in a **decision** and implementation details → use **draft-decision-log** instead (or do both: idea here, decision there).

## Workflow

1. Extract the **core idea** from the current message thread (last user turn + immediate context).
2. Infer **tags** from keywords (agent, workflow, inscription, Substack, validation, etc.).
3. Output the markdown block in chat.
4. If the user says **apply**, **add to backlog**, or **append**: read `docs/IDEAS_BACKLOG.md`, insert the new `###` block **immediately after** `## Ideas` (before older `###` entries), save.

## Optional split

If the idea is **only** about Bride of Charlie monument narrative or rollout, offer a path under `projects/monuments/bride_of_charlie/docs/IDEAS_BACKLOG.md` **instead** or **in addition**—only if the user wants monument-local ideas separated.
