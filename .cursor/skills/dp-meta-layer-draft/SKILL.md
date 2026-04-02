---
name: dp-meta-layer-draft
description: >-
  Drafts Desirable Property text and inscription-ready variants from app.themetalayer.org
  DP sources, applying the full meta-layer lens. Saves outputs to the agent-lab Draft Editor
  via save_draft when available. Produces article-first or video-first companion assets and
  CTAs for comments and supporting/opposing artifacts. Use when working on DP drafts,
  on-chain inscription text, gov hub copy, meta-layer properties, Draft Editor, or
  "draft DPn / desirable property / inscription."
---

# Desirable Property — meta-layer draft & inscription

## Goal

Turn **existing DP material** (typically `https://app.themetalayer.org/?dp=N` plus optional pasted notes) into:

1. A **full property draft** suitable for the **gov hub** (clear, reviewable).
2. An **inscription draft** — a tighter, commitment-oriented variant for **on-chain** or equivalent publication (user confirms chain/tool constraints).
3. **Comms runway**: article and/or video-oriented copy that invites **feedback** and **linked artifacts**.

## When to use

- User names a DP number or link (`dp=1` … `dp=21`).
- User asks for inscription text, gov hub draft, or meta-layer-aligned rewrite of a property.
- User points at [examples/dp1-reference.md](examples/dp1-reference.md) as the style anchor (DP1 reference is the default depth model).

## Inputs

1. **DP source URL** — fetch `app.themetalayer.org/?dp=N` (and `themetalayer.org/desirable-properties` for category context if useful).
2. **Optional:** user paste, meeting notes, or challenge context (e.g. external critique).
3. **Style anchor:** [examples/dp1-reference.md](examples/dp1-reference.md) is **populated** (full DP1 ML-Draft). **Match its structure and depth** for DP2–DP21 unless the user asks for a shorter pass.

## Meta-layer lens

Read and apply [meta-layer-lens.md](meta-layer-lens.md) as a **full pass**: identity/agency, sovereignty, interoperability, AI governance, trust/provenance/sustainability, community feedback. Surface tradeoffs and open questions explicitly.

## Comms order (two modes)

| Mode | Order | Use when |
|------|--------|----------|
| **Runway (default)** | **Article → video** | Building initial library; article grounds the draft; video amplifies. |
| **Video-first** | **Video → article** | Higher video volume; short-form leads; article becomes expanded record. |

State which mode applies in the deliverable header. User can override per request.

## Deliverables

Produce all of the following unless the user restricts scope:

### A. Full property draft (gov hub)

- Title line: `DPn — [short name]`
- **Summary** (2–4 sentences)
- **Statement of the property** (precise, implementable where possible)
- **Rationale** — why this matters for a human-first meta-layer
- **Implications** — builders, users, governance
- **Open questions / iteration** — what feedback would change the draft

### B. Inscription draft

- **Standalone** text that can ship as a single inscription (no reliance on unstated context).
- **Shorter** than the full draft; **commitment tone** (what is being claimed or recorded).
- If character/word limits are unknown, produce **one primary** + **one ultra-tight** variant and note "trim to chain limits."
- Mark status: e.g. `draft for review` — final wording is human-approved before inscription.

### C. Article companion (runway)

- **Title options** (2)
- **Lead** (2–3 paragraphs) usable in Substack or site
- **CTA block** (must include):
  - Invite **comments** on the draft
  - Invite **links to supporting or opposing artifacts** (papers, posts, code, governance decisions) with short guidance on what makes a useful link

### D. Video companion (runway or video-first)

- **60–90s beats**: hook → what this DP is → why it matters → what feedback we need
- **On-screen title** suggestion
- **Spoken CTA**: comment + link an artifact (same intent as article)

### E. Cross-DP consistency

- Name **adjacent DPs** that this draft touches or must stay aligned with (same page/category).

## Draft Editor (agent-lab)

**Yes —** these drafts belong in the **Draft Editor** the same way other agent output does. The DeerFlow `save_draft` tool writes to `data/draft_store/`; the UI (typically `http://localhost:8081`) lists them for review and publish.

### When `save_draft` is available

Use **one `save_draft` call per logical artifact** (do not cram unrelated variants into one draft). Typical mapping:

| Artifact | `platform` | `destination` | `title` (short label) |
|----------|------------|---------------|------------------------|
| Full gov-hub draft (A) | `substack` | `Substack · metaweb` | `DPn — full draft (gov hub)` |
| Inscription draft (B) | `substack` or `linkedin` | Same family as above, or org LinkedIn if inscription is staged as a post | `DPn — inscription draft` |
| Article companion (C) | `substack` | `Substack · metaweb` | `DPn — article / Substack` |
| Video beats (D) | `linkedin` | `LinkedIn · Meta-Layer Initiative` or personal — pick one | `DPn — video beats` |

Use **`metadata_json`** so the editor and future you can filter. Merge with any other metadata keys the tool expects; at minimum include:

```json
{
  "title": "<same as save_draft title param>",
  "draft_type": "desirable_property",
  "dp_number": <integer>,
  "variant": "full_gov_hub | inscription | article | video_beats"
}
```

Optional: `"source_url": "https://app.themetalayer.org/?dp=N"`.

**Publish profiles:** Use the exact `destination` strings from the user’s `data/shiftshapr_context.json` → `publish_profiles` (or the agent context block) — same as meta-layer-article / event promo flows.

After saving, tell the user: **Review in Draft Editor** (local URL if known).

### When `save_draft` is not available

(e.g. Cursor without DeerFlow / `AGENT_LAB_ROOT` unset)

1. **Preferred:** Run the same workflow through **Shiftshapr / DeerFlow** so `save_draft` executes in agent-lab context.
2. **Fallback:** From the **agent-lab repo root**, with `PYTHONPATH` including the project root, the agent may call `apps.draft_editor.store.create_draft` in a short script — only if the user wants files landed without DeerFlow; otherwise output Markdown in chat for manual paste.

## Workflow

1. Fetch DP source; extract claims, lists, and definitions.
2. Apply **meta-layer-lens.md**; note gaps vs. lens.
3. If **dp1-reference.md** is populated, align structure to it.
4. Draft **A → B → C → D** in that order (inscription after full draft so it stays faithful).
5. Add **CTA** blocks to C and D as specified.
6. If **`save_draft` is available**, persist A–D (and any promo variants) to the Draft Editor per the table above; include `metadata_json` for `desirable_property` drafts.

## Anti-patterns

- Do not invent Meta-Layer Initiative commitments the user did not state.
- Do not skip the **artifact CTA** — it is part of the program.
- Do not merge inscription and long draft into one blob without a labeled inscription section.
