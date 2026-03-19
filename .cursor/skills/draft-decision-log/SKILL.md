---
name: draft-decision-log
description: >-
  Drafts a "conversation → build" log entry for agent-lab from the current chat:
  decision, context, files/commits, follow-ups. Use when the user asks to log
  a decision, draft a build log, record this conversation for the repo, update
  AGENT_AND_MONUMENT_DECISIONS, monument launch notes, or "what we talked about"
  for documentation.
---

# Draft decision log entry

## Goal

Produce **ready-to-paste Markdown** (and optionally apply it) so decisions from the **current conversation** land in the repo’s decision logs without manual re-writing.

## Target files (pick one per entry)

| Scope | File path (from agent-lab root) |
|-------|----------------------------------|
| **Repo-wide** (protocols, skills, multi-monument, tooling) | `docs/AGENT_AND_MONUMENT_DECISIONS.md` → section **Conversation → build log** |
| **Bride of Charlie** (rollout order, monument-only comms, monument pipeline) | `projects/monuments/bride_of_charlie/docs/LAUNCH_AND_COMMS_STRATEGY.md` → section **Conversation → build log** |

If the user does not specify scope, **prefer repo-wide** when the topic is protocols, validation, Neo4j, deer-flow, Cursor skills, or cross-project patterns; **prefer monument** when the topic is inscription timing, gov hub, Substack, video, or Bride-specific content.

**Never** paste secrets (API keys, tokens, private URLs). Redact or omit.

## Output format

Emit **one block** (newest entries go **at the top** of the log section — tell the user to paste **below** the section heading, above older entries):

```markdown
### YYYY-MM-DD — <short title>

- **Source:** Cursor chat / meeting / note (no PII unless user explicitly wants it).
- **Decision:** …
- **Implementation:** paths, files, `git log -1 --oneline` if a commit exists; no secrets.
- **Follow-ups:** … (optional)
```

Use **today’s date** unless the user gives another.

## Workflow

1. Summarize **only what was decided or built** in this thread — not irrelevant tangents.
2. If implementation is unclear, list **probable** paths or say *"verify paths"* — do not invent commits.
3. If the user says **apply** or **add it**, use the edit tool to insert the block **immediately after** the line `## Conversation → build log` (or `###` heading that starts that section), **before** the first existing `###` dated entry. If the section only has placeholder text, replace the placeholder with the new entry + keep `<!-- template ... -->` if present below.

4. Otherwise output the block in chat and say: *Paste at top of the log section, or ask me to apply.*

## Cross-link

Mention the other file when both are relevant (e.g. "Also add a one-liner under Follow-ups in the monument doc").
