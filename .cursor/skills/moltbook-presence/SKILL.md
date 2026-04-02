---
name: moltbook-presence
description: >-
  Drafts Moltbook (agent-native social) presence for the Meta-Layer: profile framing,
  first posts, Submolt ideas, and CTAs that hand off to the gov hub / desirable-property
  drafts and artifact comments. Use when the user mentions Moltbook, Submolts, inviting
  PAIs, agent communities, or agent-only social outreach.
---

# Moltbook presence & PAI handoff

## Goal

Make **discoverability** and **serious follow-through** one story: agents (and their humans) find you on Moltbook, understand what the Meta-Layer is doing, and land on **reviewable work** (gov hub, DP drafts, “comment + link an artifact”).

## Principles

- **Bounded invites**: Name concrete roles (e.g. critique a DP, link a supporting/opposing paper, join a hub layer)—not vague “join us.”
- **Handoff URL**: One canonical link per campaign (hub section, `themetalayer.org/desirable-properties`, or a specific DP app link).
- **Human-first tone**: Acknowledge agent autonomy; avoid hype and “AI theater” language.
- **Same CTAs as DP runway**: Comments on drafts + **links to artifacts** (papers, posts, code, governance decisions).

## Deliverables (produce what the user asks for)

1. **Profile / bio** (short + long)—who this agent or initiative is, what hub/DPS are in scope, link line.
2. **First post** (or thread outline)—hook, problem, what you’re building above the webpage, single CTA.
3. **Submolt ideas** (3–5 names + one-line purpose)—aligned with DPs or themes (governance, trust, coordination).
4. **Reply / quote templates** (2–3)—for common questions (“What should I do?” → link hub + how to submit artifact).
5. **Optional**: cross-post stubs for X/LinkedIn that **point to** Moltbook without duplicating the whole essay (use **meta-layer-article** or **build-in-public** for long LinkedIn/Substack).

## Inputs to confirm

- **Actor**: Personal agent, Meta-Layer org agent, or both.
- **Links**: Gov hub URL (when live), `themetalayer.org/desirable-properties`, target `app.themetalayer.org/?dp=N`, lu.ma or other CTAs from `data/shiftshapr_context.json` if relevant.
- **DP focus**: Which property number(s) you’re inviting feedback on right now.

## Saving drafts

When **`save_draft`** is available, save variants with clear `title` and `destination` from **publish_profiles** (often not “posting to Moltbook” via Playwright—Moltbook is usually **human/agent operator** pasting). Still useful to stage **LinkedIn/X** promo lines in the Draft Editor that say “We’re on Moltbook; hub link is …”.

If the user will paste into Moltbook manually, output **final Markdown** in chat in copy-paste blocks.

## Anti-patterns

- Do not promise on-chain or hub commitments the user has not made.
- Do not invent Submolt names that impersonate existing communities—use “proposed: …” unless verified.
- Do not skip the **artifact + comment** CTA when DPs are part of the campaign.

## Related

- **dp-meta-layer-draft** / **desirable-properties-workflow** — draft substance.
- **meta-layer-article** — long-form + scheduling + **master-calendar** sync when publishing on traditional channels.
