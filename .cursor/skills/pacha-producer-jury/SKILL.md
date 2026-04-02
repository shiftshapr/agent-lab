---
name: pacha-producer-jury
description: >-
  Runs competitive scoring ("jury") across Pacha film producer packets and
  slate timeline / canon coherence in projects/pacha. Use when comparing,
  scoring, picking, or ranking Pacha films or producer drafts, or aligning the
  slate to Pacha's timeline. For partners, outreach, community ops, content
  briefs, or community-input synthesis, use pacha-producer-outreach instead.
---

# Pacha producer jury

## Goal

Help **Producer agents** (and humans) do **two** jobs with a shared rubric:

1. **Jury / compare** development packets for each film in `projects/pacha/` so decisions are explicit.
2. **Align the slate** in **Pacha's timeline** and canon (no silent forks between projects).

For **partners, community management, content briefs**, and **community-input synthesis**, use **`pacha-producer-outreach`**.

## Canonical context (read before big edits)

| Topic | Path (agent-lab root) |
|-------|------------------------|
| Film story canvases | `projects/pacha/*.md` |
| Badge + BRC333 policy | `config/civic_mason_badge.md` |
| Structured lore / entities (if needed) | `knowledge/pacha_schema.md` |

## When to use

- User asks to **compare**, **score**, **pick**, or **rank** Pacha films or producer drafts.
- User mentions **producer agents**, **slate**, **timeline**, **canon**, **Foodlandia**, **SATS**, **Civic Mason** in the context of **evaluation**, not outreach.

## Jury rubric (score each film 1–5 + one-line evidence)

Use the **same** criteria every time so "competition" stays fair.

| Criterion | What "good" looks like |
|-----------|-------------------------|
| **Clarity** | Logline + premise are memorable; audience is specific. |
| **Producibility** | Budget band feels honest; set-pieces are filmable; risks named. |
| **Franchise / slate fit** | Strengthens Pacha IP; doesn't require contradicting other projects. |
| **Canon / timeline** | Placed clearly in Pacha's life arc; ties to dream/blueprint frame where relevant (`civic_mason.md`). |
| **Reputational safety** | No predatory vibes; kid/family tone where applicable; **SATS-adjacent work avoids investment or financial advice** (story and metaphor only). |
| **Badge bridge** | Suggests plausible **badge themes** aligned with `civic_mason_badge.md` (Pacha kid layer vs Civic Mason later). |

Emit a **scorecard table** (films × criteria) + **top 3 strengths / top 3 risks** per film + **single recommendation** (e.g. greenlight depth on X, park Y, merge Z).

## Outputs

1. **Jury scorecard** (markdown table + narrative).
2. **Slate timeline note**: 5–10 bullets on how projects sit together **after** this pass (flag conflicts).

## Workflow

1. Confirm which `projects/pacha/*.md` files are in scope.
2. Pull **non-negotiables** from `config/civic_mason_badge.md` if badges or commerce are involved.
3. Run the rubric; produce scorecard + slate timeline note.
4. End with **decisions to make by humans** (showrunner, legal).

## When NOT to use

- **Partner outreach, community plans, content calendars** → **`pacha-producer-outreach`**.
- Pure screenplay line edits without slate evaluation (writer-led workflow).
- Legal review of contracts or chain of title (surface questions; do not "finalize" legal language).

## Related

- Ops (milestones, GitHub, token budget, JAUmemory, Discord): **`docs/PACHA_AGENT_GOVERNANCE.md`**
