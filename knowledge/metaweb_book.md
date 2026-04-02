# Metaweb Book — Overview

This file provides an overview of the canonical Metaweb book and how it integrates with the agent knowledge base.

**Book Location:** The complete Metaweb book chapters are located in `./Metaweb Book/` (ch01.md through ch16.md)

**Purpose:** This book is the foundational text for understanding the metalayer vision - a multi-layered web experience that enables contextual overlays, stigmergic collaboration, and collective intelligence above today's flat webpages.

**Key Concepts:** The book covers the transition from Web 1.0 → Web 2.0 → Metaweb, introducing concepts like smart tags, bridges, canopi (presence layers), and attention-triggered interfaces.

This file shapes how Shiftshapr and subagents reason about infrastructure, governance, and coordination in the context of the metalayer worldview.

## Tying the metaweb *narrative* to the hub UI (sketch)

The Bride hub today is **operational** (files, episodes, diffs, optional Neo4j). A **book-facing** layer could sit beside it without replacing inscription JSON:

1. **Reading spine** — A route such as `/bride-of-charlie/read` (or `/metaweb/read`) renders Markdown chapters from `knowledge/Metaweb Book/` directory; sidebar = episode list or TOC from structured frontmatter.
2. **Concept rails** — Glosses pulled from this file + `meta_layer_schema.md` as **inline tooltips**, a right-hand “Concepts” drawer, or footnotes keyed by stable IDs (e.g. `[[Concept:ledger]]`).
3. **Episode framing** — Short **curated lead** per episode (1–2 paragraphs + “what to verify”) stored in MD/YAML; hub **episode** page shows that block above file links so the *story* and the *evidence paths* stay co-located.
4. **Graph as argument** — Neo4j **Graph** page (or embedded widget) highlights “pressure” nodes and open integrity issues; narrative copy explains *why* those checks matter (protocol language → reader language).
5. **Agent handoff** — Same Markdown sources feed **DeerFlow** prompts and **Draft Editor** copy so book, UI, and agents share one text base.

Start minimal: **(3) episode framing MD** + **(1) single `/read` page** that lists links to chapters; expand to glossaries and graph copy later.
