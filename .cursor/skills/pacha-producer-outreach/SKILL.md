---
name: pacha-producer-outreach
description: >-
  Partner identification and outreach, social community planning, content
  briefs, and community-input synthesis for Pacha's film slate and badges.
  Use when the user asks for partners, outreach emails/DMs, community
  management, campaigns, content calendar, UGC rituals, or community signal for
  decisions—not for competitive film scoring (use pacha-producer-jury).
---

# Pacha producer outreach & community

## Goal

Support **Producer agents** (and humans) on:

1. **Partners & comms**: identify potential partners; draft outreach that is accurate and on-brand.
2. **Social communities** (plan-level): guidelines, rituals, moderation/ambassador framing.
3. **Content**: campaign briefs and calendars (not final legal copy).
4. **Community input**: synthesize signal for slate/badge decisions (optional input to the **producer jury** process).

## Canonical context

| Topic | Path (agent-lab root) |
|-------|------------------------|
| Film story canvases | `projects/pacha/*.md` |
| Badge + BRC333 policy | `config/civic_mason_badge.md` |
| Structured lore / entities (if needed) | `knowledge/pacha_schema.md` |

## When to use

- **Partners**: targets, pitch angles, outreach drafts, follow-ups.
- **Community**: mod guidelines, weekly rhythm, rituals, ambassador notes, minors/guardians safety.
- **Content**: pillars, hooks, formats, CTAs, cross-links to book/badges/programs.
- **Community jury input**: polls, comment themes, synthesis mapped to films and badges.

## When NOT to use

- **Comparing or scoring** films with a rubric → use **`pacha-producer-jury`**.
- Legal finalization of contracts or chain of title (surface questions only).
- Pure screenplay or scene rewriting without outreach/community context.

## Cross-link

- For **competitive scorecards** and **slate timeline coherence** after canon review, use **`pacha-producer-jury`**.

---

## Partners: identify and communicate

**Identify**

- List **partner types** (distributors, educators, food/culture orgs, family media, festivals—match the film).
- For each lead: **why them**, **what we offer**, **what we need**, **risk** (reputation, exclusivity, kids' data).

**Communicate**

- Draft **short outreach** (email or DM skeleton): subject, 3–5 sentences, one clear ask, link to safe public materials.
- **Never** imply signed deals, funding, or release dates that are not true.
- Flag items that need **legal** or **showrunner** approval before send.

## Social communities: manage (plan-level)

- **Guidelines**: tone, escalation (spam, harassment, political flame), how to handle minors and guardians.
- **Rituals**: repeatable events (read-along, feast share, builder prompt) tied to badges where appropriate.
- **Roles**: moderator brief, ambassador script outline, "what not to do" for official accounts.

Do not present as **medical, therapeutic, or investment** guidance.

## Content: create (briefs, not final legal copy)

- **Pillar + hook** per film or per month; **formats** (short video, carousel, UGC prompt).
- **CTA** that matches age and policy (parent gate for purchases).
- **Cross-link** to book, programs, and badge campaigns without overpromising the movie.

**SATS-adjacent**: story and metaphor only; **no financial or investment advice**.

## Community input (for slate / jury / badges)

When the showrunner wants **community-weighted** direction:

1. **Define the question** (one sentence): e.g. "Which theme should lead the next read-along?"
2. **Channel**: where input is collected (poll, comments, partner classroom, ambassador circle)—keep **minor safety** and **moderation** in view.
3. **Synthesis**: summarize themes (not individual minors' PII); map results to **films** and **badge lines**.
4. **Weighting**: state whether community signal is **advisory** vs **binding** for the showrunner.

Output a short **"community jury summary"**: question → participation level (if known) → themes → suggested slate/badge actions.

If the user also wants **scores**, run **`pacha-producer-jury`** separately or hand off the synthesis document to that workflow.

## Outputs (pick what the user asked for)

1. **Partner list + outreach draft** (one partner or a short list).
2. **Community plan** (weekly rhythm + one community-jury question).
3. **Content brief** (one campaign or one week).

## Workflow

1. Confirm which `projects/pacha/*.md` files and which **film(s)** are in scope.
2. If badges or commerce are involved, respect **`config/civic_mason_badge.md`**.
3. Deliver the requested output(s); flag **human approvals** (legal, showrunner, guardian-facing product).

## Related

- Ops (milestones, GitHub, token budget, JAUmemory, Discord): **`docs/PACHA_AGENT_GOVERNANCE.md`**
- Discord channel/mod patterns: **`discord-community-management`**
