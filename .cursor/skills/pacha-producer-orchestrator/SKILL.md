---
name: pacha-producer-orchestrator
description: >-
  Runs one bounded "producer shift": evaluate backlog/context, pick the next
  Pacha slate milestone per the autonomy charter, route to jury or outreach
  work, produce drafts and a human handoff (PR/issue checklist). Use when the
  user wants agent-initiated producer work, a daily/weekly slate ritual,
  autonomous next step, or orchestration across pacha-producer-jury and
  pacha-producer-outreach without merging or publishing externally.
---

# Pacha producer orchestrator (bounded initiative)

## Goal

Operate **one cycle** of **agent-initiated** producer work: **assess → choose → draft → hand off** for human review. This implements **[`docs/PACHA_PRODUCER_AGENT_AUTONOMY_CHARTER.md`](../../../docs/PACHA_PRODUCER_AGENT_AUTONOMY_CHARTER.md)** inside Cursor.

**Not in scope:** merge to `main`, approve milestones, send partner/social emails, spend money, live badge issuance, legal finalization.

## When to use

- User asks for a **producer shift**, **autonomous next step**, **what should we do next**, **run the slate loop**, **morning ritual**, or **orchestrate** jury + outreach.
- User wants the agent to **pick** the next milestone from GitHub context (if user pasted issue/Project state) or from **repo files** when the board is not visible.

## Canonical docs (read order)

1. **[`docs/PACHA_PRODUCER_AGENT_AUTONOMY_CHARTER.md`](../../../docs/PACHA_PRODUCER_AGENT_AUTONOMY_CHARTER.md)** — tiers, pick rules, stop conditions.
2. **[`docs/PACHA_AGENT_GOVERNANCE.md`](../../../docs/PACHA_AGENT_GOVERNANCE.md)** — milestones, Slate stage, budget.
3. **`projects/pacha/*.md`**, **`config/civic_mason_badge.md`**, **`knowledge/pacha_schema.md`** as needed.

## JAUmemory (if MCP available)

- **`recall`** at start (tags: `pacha`, `producer-slate`, `orchestrator`).
- **`remember`** at end of cycle: chosen milestone, outcome, blockers—**no secrets**.

## Orchestrator loop (one shift = one primary deliverable)

### Phase 1 — Situation

- Summarize **what changed** since last run if the user pasted notes or you have file/git context.
- If user provides **GitHub**: infer **Slate stage** of open issues; prefer **Ready** with DoD.
- If no board access: infer from **`pacha-slate-producers`** paths or **`projects/pacha`** and propose the next file-based milestone.

### Phase 2 — Choose (apply charter §3)

- State **one** chosen milestone ID + title + why (2–4 bullets).
- If blocked (charter §6): output **blocker summary** and **questions for showrunner/editor**—stop without inventing canon.

### Phase 3 — Execute (delegate)

- **Jury-shaped** work (scorecard, timeline, canon alignment) → apply the workflow and depth of **`pacha-producer-jury`** (rubric, outputs).
- **Outreach-shaped** work (partners, community, content) → apply **`pacha-producer-outreach`**.
- **Only one** primary deliverable this shift unless the user asked for more.

### Phase 4 — Handoff (required)

Emit a **Handoff block** the human can paste into GitHub:

```markdown
## Orchestrator handoff — <date>
- **Milestone ID:** …
- **Slate stage:** move to → Submitted (after PR opened)
- **PR / branch:** … (or "draft paths only: …")
- **Files touched / suggested paths:** …
- **Needs human (Tier B/C):** … or None
- **Next shift suggestion:** …
```

## Outputs

1. **Situation** (short).
2. **Decision** (chosen milestone + rationale).
3. **Primary artifact** (jury scorecard + timeline **or** outreach/community/content pack—full content per sub-skill).
4. **Handoff block** (markdown as above).

## When NOT to use

- User only wants a **pure score** with no prioritization → **`pacha-producer-jury`** only.
- User only wants **partner email** or **community plan** → **`pacha-producer-outreach`** only.
- **Discord** channel design without slate prioritization → **`discord-community-management`**.

## Related

- **`pacha-producer-jury`** · **`pacha-producer-outreach`** · **`discord-community-management`**
- Private repo: **`pacha-slate-producers`** (see `projects/pacha/README.md`)
