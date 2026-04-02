---
name: boc-narrative-layers
description: >-
  Generate multi-lens narratives for Bride of Charlie from structured data
  (episodes, claims, graph, social threads); support claim-constraint
  relaxation for alternate tellings; align book-app chat with meta-layer
  sources. Use when authoring BOC stories, book-app copy, or enabling others
  to narrate from the same evidence base.
---

# Bride of Charlie — narrative layers from data

## Goal

Turn the **evidence base** (transcripts, inscriptions, graph, timestamps, social posts) into **explicit narrative products**. Each product names its **lens** (who tells, what is primary, what is background) so readers never confuse *one telling* with *the only possible truth*.

## Canonical lenses (examples)

Use these as first-class modes; add more as named lenses with the same metadata block.

### Lens A — Candace arc + social reception

- **Spine:** How Candace told the story (sequence, emphasis, phrasing where evidenced).
- **Braid in:** Responses and patterns on X and LinkedIn (quotes, paraphrase with source links, aggregate themes — no fabricated engagement).
- **Tone:** Documentary / media-studies; separate **primary narrative** from **reaction layer** (e.g. section breaks or typographic distinction).

### Lens B — Erika-centered biography (chronological)

- **Opening:** Ground in verified facts (e.g. birth, documented life events as present in your corpus). Expand only where the data supports detail; otherwise mark gaps explicitly (“not established in source set”).
- **Spine:** Detailed telling of her story as supported by episodes, claims, and cited materials — **not** the same ordering or emphasis as Lens A unless the data aligns.
- **Tone:** Long-form literary or biographical; still **cite or tag** claims that anchor each paragraph.

## Required output frontmatter (every generated narrative)

At the top of the narrative (YAML or a fixed header block):

- `lens_id`: e.g. `candace_plus_social`, `erika_chronicle`
- `sources`: list of files, episode IDs, inscription refs, URLs scraped or exported
- `claim_policy`: `strict` (only claims present in source) | `relaxed` (see below)
- `relaxed_claims`: if any — list which assertions are softened, hypothetical, or reordered for story flow
- `generated_at` / `generator`: for provenance when others reuse the pipeline

## Claim relaxation (“what if” narratives)

When the user wants to **experiment** with narrative by relaxing constraints:

1. **Inventory** the claims the strict version depends on (bullet list).
2. **Declare** each change: e.g. “Assume X unproven,” “Reorder events for dramatic effect,” “Omit thread Y.”
3. **Regenerate** the narrative; label the output **`claim_policy: relaxed`** and keep `relaxed_claims` explicit.
4. Never present relaxed output as canonical; prefer a subtitle like *Alternate telling (relaxed constraints)*.

This supports **comparing** narratives side-by-side in a book app without corrupting the integrity view.

## Enabling others to generate from the data

- Publish a **narrative spec template**: lens description, allowed sources, claim policy, output sections, word-count band, citation style.
- Expose **exports** (CSV/JSON of claims, episode manifest, optional graph excerpts) with stable IDs so third-party prompts reference the same rows.
- Document **minimum viable inputs** so external authors know what “grounded” means for your hub.

## Metaweb book app + “talk to a meta-layer expert”

When building or using **conversational** UI on top of the Metaweb book:

- **Ground** answers in `knowledge/metaweb_book.md`, `knowledge/Metaweb Book/*.md`, and `knowledge/meta_layer_schema.md` (retrieve-then-answer pattern).
- **Cite** chapter, section, or schema heading when giving definitions or recommendations.
- **Scope:** If the question is about BOC facts, pull from BOC evidence exports; if about the metalayer vision, prefer Metaweb chapters; do not merge the two without labeling the blend.
- **Persona:** “Meta-layer expert” = helpful explainer of *your* published concepts and schema — not a generic futurist; defer when the corpus is silent.

## Agent workflow (summary)

1. Confirm **lens** and **claim_policy**.
2. Pull relevant structured slices (episodes, claims, social exports, graph summaries).
3. Draft narrative with clear sections and inline anchors to source IDs where useful.
4. Emit **frontmatter** and, if relaxed, the **relaxed_claims** ledger.
5. For chat/RAG: retrieve from Metaweb + schema (+ BOC export if asked), then answer with citations.
