---
name: discord-community-management
description: >-
  Plans and operates Discord for Pacha (family-safe, slate/community) and
  Meta-Layer (governance, DPs, gov hub handoffs): channel maps, mod norms,
  escalation, announcements, and what belongs in Discord vs GitHub. Use when
  the user mentions Discord, server setup, moderation, Pacha Discord,
  meta-layer Discord, community rules, or bot/workflow hooks for servers.
---

# Discord community management (Pacha & Meta-Layer)

## Goal

Help **humans and agents** run **two distinct Discords** (or two clear regions in one server) without mixing norms:

1. **Pacha** — audience, families, story, badges, campaigns; **kid-adjacent safety** and brand tone.
2. **Meta-Layer** — governance, desirable properties, gov hub / GitHub artifacts, agent coordination.

## When to use

- Setting up or revising **channels, roles, or rules**.
- **Moderation** playbooks, escalation, incident response.
- **Announcement** and **event** templates (read-alongs, AMAs, milestone posts).
- Deciding **what to post in Discord** vs **what must live in GitHub** (reviewable, versioned).

## Canonical handoffs

| Surface | Use for |
|---------|---------|
| **Discord** | Timely discussion, hype (bounded), events, quick Q&A, pointing to canonical links. |
| **GitHub** (private producer repos) | Producer packets, approvals, milestone state, drafts that need line-by-line review. |
| **Gov hub / public artifact URLs** | Formal review threads, DP comments, “link your artifact” CTAs (align with `moltbook-presence`, `dp-meta-layer-draft`). |

**Do not** treat Discord reactions alone as **binding governance** unless humans explicitly define that; prefer **GitHub Issues/Discussions** or gov hub for durable decisions.

## Pacha server — norms

- **Tone:** warm, inclusive, age-appropriate; avoid fear-based or medical/healing **claims**; entertainment + care, not therapy or treatment language.
- **SATS / Bitcoin themes:** story and curiosity only—**no investment, price, or “buy/sell” guidance.**
- **Minors:** minimal data collection; clear **guardian** framing for purchases and badges (see `config/civic_mason_badge.md`).
- **UGC:** moderation queue for images/links; zero tolerance for grooming, harassment, doxxing.

## Meta-Layer server — norms

- **Tone:** precise, good-faith, governance-friendly; link to **reviewable** drafts and repos.
- **Invite critique** on DPs and artifacts; avoid vague “join the movement” without a concrete ask.
- **Bridge** to Moltbook / gov hub / app links per existing meta-layer skills—do not invent live URLs.

## Channel map (template — adapt to your server)

**Pacha (example blocks)**

- `#announcements` (slow mode) · `#book-club` · `#badges-help` · `#feast-foodlandia` · `#creator-corner` · `#parents` · `#mod-only`

**Meta-Layer (example blocks)**

- `#announcements` · `#desirable-properties` · `#artifact-links` · `#agent-lab` · `#gov-hub` · `#mod-only`

## Moderation & escalation

1. **Warn** (rule cite) → **timeout** → **ban** (severe: skip steps).
2. **Escalate** safety concerns to designated humans immediately; **do not** debate CSAM, threats, or self-harm in public channels.
3. Log **patterns** (not PII) for JAUmemory when useful: `remember` with tags `discord`, `pacha` or `meta-layer`.

## Roles (suggested)

- **Mods** — enforce rules, timeouts, clean spam.
- **Pacha team** — announcements, official answers (single voice where possible).
- **Meta-Layer stewards** — DP/gov hub pointers, clarify process.
- **Bots** (optional) — ticketing, welcome, link to rules; **no** storing secrets in bot configs in public channels.

## Agent behavior

- Agents **draft** mod posts, announcements, and channel descriptions; **humans** publish sensitive or policy-binding messages.
- After major server policy changes, suggest a **`remember`** to JAUmemory (summary + tags).

## Related skills

- **`pacha-producer-outreach`** — community plans, rituals, content briefs tied to Discord.
- **`moltbook-presence`** — agent-native social handoff to gov hub / DPs.
- **`dp-meta-layer-draft`** — Meta-Layer property drafts.

## When NOT to use

- Legal finalization of terms, privacy policy, or COPPA stance (surface checklist; human/legal owns).
- Technical Discord API bot implementation (this skill is **ops and copy**, not code deployment).
