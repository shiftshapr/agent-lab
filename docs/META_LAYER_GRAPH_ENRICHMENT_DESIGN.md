# Meta-Layer Graph Enrichment — Design Space

Mapping the design space for extracting structured nodes (orgs, reports, concepts, entities) and relationships from ingested content. Designed to work for **any tech article** (AI, governance, infra, product, policy) and to derive **opportunities** for alignment, collaboration, and promotion.

---

## 0. General Applicability (Any Tech Article)

The extraction must be **domain-agnostic**. Same pipeline for:

- Policy reports (Breaking Free, EU AI Act analyses)
- Tech blog posts (Substack, company blogs)
- Academic papers, RFCs, whitepapers
- News (TechCrunch, Ars Technica)
- Podcast transcripts, conference talks

**How:** The LLM prompt uses generic instructions: "Extract organizations, publications, concepts, and people/coalitions. Identify opportunity signals." No hardcoded domains. User context (`meta_layer_lens`, `key_projects`, `priorities`) is passed to the LLM so it can judge **alignment** with the user's interests.

---

## 1. When to Enrich

| Option | Trigger | Pros | Cons |
|--------|---------|------|------|
| **A. Post-ingest (automatic)** | Right after URL/PDF/chunk ingest | Always consistent, no user action | Latency, cost per ingest |
| **B. On-demand (skill)** | User says "enrich graph" or "analyze what I added" | User control, batch when ready | Easy to forget |
| **C. Scheduled (cron)** | e.g. daily, process unenriched chunks | Batched, predictable | Stale until run |
| **D. Lazy (at retrieval)** | When query touches a chunk, enrich then cache | Pay only for what's used | Cold-start latency, complexity |

**Recommendation:** Start with **B** (on-demand skill), add **A** as optional flag ("add to graph and enrich").

---

## 2. What to Extract

### Node types (extend schema)

| Node | Purpose | Example |
|------|---------|---------|
| `MLOrg` | Organizations | Forbrukerradet, Norwegian Consumer Council |
| `MLReport` | Reports, books, publications | "Breaking Free: Pathways to a fair technological future" |
| `MLConcept` | Concepts, themes | enshittification, consumer rights |
| `MLEntity` | People, policymakers, coalitions | EU/EEA policymakers, 70+ consumer groups |
| `MLProject` | Initiatives, campaigns | Breaking Free campaign |
| `MLChunk` | (existing) Raw text | — |

### Relationship types

| Relationship | From → To | Example |
|--------------|-----------|---------|
| `PUBLISHED` | Org → Report | Forbrukerradet -[:PUBLISHED]-> Breaking Free |
| `DISCUSSES` | Report → Concept | Breaking Free -[:DISCUSSES]-> enshittification |
| `ADDRESSES` | Report → Entity | Report -[:ADDRESSES]-> EU policymakers |
| `COLLABORATES_WITH` | Org → Entity | Forbrukerradet -[:COLLABORATES_WITH]-> consumer groups |
| `PART_OF` | Entity → Org | Coalition -[:PART_OF]-> Campaign |
| `INSTANTIATES` | Chunk → Concept/Entity | (existing) Chunk exemplifies concept |
| `DERIVES_FROM` | Concept → Primitive | (existing) enshittification -[:DERIVES_FROM]-> governance |

### Extraction scope (what the LLM is asked to find)

- **Minimal:** Orgs, reports, 3–5 key concepts
- **Standard:** + entities (people, coalitions), relationships between them
- **Full:** + dates, quotes, policy domains, opportunity signals (join? write? engage?)

---

## 3. How to Extract

| Approach | Mechanism | Pros | Cons |
|----------|-----------|------|------|
| **LLM (structured output)** | Prompt + JSON schema, e.g. `{"orgs": [...], "concepts": [...], "relationships": [...]}` | Flexible, handles nuance | Cost, latency, occasional hallucination |
| **LLM (tool use)** | DeerFlow calls `meta_layer_graph_add` for each entity/relationship | Incremental, auditable | Many tool calls, slower |
| **Rules + NER** | Regex, keyword lists, spaCy/transformers NER | Fast, deterministic | Misses nuance, brittle |
| **Hybrid** | Rules for primitives/concepts, LLM for orgs/reports/relationships | Balance of speed and quality | Two code paths |

**Recommendation:** **LLM structured output** — single pass, parse JSON, batch-write to Neo4j. Simpler than tool use, more accurate than rules.

---

## 4. Where It Runs

| Location | Invocation | Dependencies |
|----------|------------|--------------|
| **Shiftshapr** | After `_handle_url_add_to_graph` / `_handle_document` | Subprocess to enrichment script |
| **DeerFlow skill** | "enrich graph" / "analyze and add entities" | MCP + meta_layer_graph_add, or direct Neo4j |
| **Standalone script** | `python scripts/enrich-meta-layer-graph.py [--file path]` | Neo4j, LLM API |
| **Cron** | `0 8 * * * ./scripts/enrich-meta-layer-graph.sh` | Same as script |

**Recommendation:** **Standalone script** as core. Shiftshapr and DeerFlow invoke it (subprocess or `run-deerflow-task` with enrich prompt).

---

## 5. Ingestion Pipeline (Redesigned)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  INPUT: URL | PDF | Paste                                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: Raw Ingest                                                              │
│  • Fetch / extract text                                                           │
│  • Save to knowledge/{urls,docs}/                                                │
│  • Create MLSource + MLChunk(s)                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: Entity Extraction (domain-agnostic)                                     │
│  • MLOrg, MLReport, MLConcept, MLEntity                                          │
│  • Relationships: PUBLISHED, DISCUSSES, ADDRESSES, COLLABORATES_WITH, etc.        │
│  • Input: chunk text + user context (meta_layer_lens, key_projects) for alignment │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: Opportunity Extraction                                                  │
│  • alignment: How does this align with user's interests? (use shiftshapr_context) │
│  • collaboration: Open calls, coalitions, fellowships, working groups             │
│  • promotion: Essay angles, speaking, Substack, podcast, conference               │
│  • Output: MLOpportunity nodes + sync to opportunities.json                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Triggers:**
- **URL/PDF + "add to my graph"** → Stage 1 only (current behavior)
- **URL/PDF + "add to my graph and enrich"** → Stage 1 + 2 + 3
- **"enrich graph"** (on existing chunks) → Stage 2 + 3
- **Cron** (optional) → Stage 2 + 3 on unenriched chunks

**User context for alignment:** Pass `meta_layer_lens`, `key_projects`, `priorities` from `shiftshapr_context.json` into the LLM prompt so it can judge what "aligns" with the user.

---

## 6. Schema Extensions (Concrete)

Add to `meta_layer_schema.md`:

```
MLOrg        {name, url?, country?, notes}
MLReport     {name, url?, year?, author_org?, summary?}
MLEntity     {name, entity_type: person|org|coalition|policymaker, notes}
```

Relationships: `PUBLISHED`, `DISCUSSES`, `ADDRESSES`, `COLLABORATES_WITH`, `PART_OF`.

---

## 7. Opportunity Taxonomy (Core)

Explicit extraction of **three opportunity types**:

| Type | Meaning | Examples |
|------|---------|----------|
| **Alignment** | Content aligns with user's work (meta-layer: infra, governance, coordination) | Report on enshittification ↔ user cares about governance |
| **Collaboration** | Open to join, co-author, partner | "70+ groups sending letters" → coalition to join; fellowship; working group |
| **Promotion** | Angle for writing, speaking, amplifying | Substack essay on report; podcast guest; conference talk |

**Extraction:** LLM is prompted: "For each opportunity type, list concrete signals with evidence from the text (quote or paraphrase)."

**Storage:**
- `MLOpportunity` node: `{type: alignment|collaboration|promotion, description, evidence, source_chunk_id, status: open|pursued|passed}`
- Relationship: `(Chunk)-[:SIGNALS]->(MLOpportunity)`, `(MLOpportunity)-[:RELATES_TO]->(MLOrg|MLReport|MLEntity)`
- Optional sync to `data/opportunities.json` for `/opportunities` and cron

---

## 8. Decision Matrix

| Dimension | Option | Rationale |
|-----------|--------|-----------|
| When | On-demand skill first | User control, simpler |
| What | Orgs, reports, concepts, entities, 6 relationship types | Covers Breaking Free case |
| How | LLM structured output | One pass, good quality |
| Where | Standalone script | Reusable from Shiftshapr, DeerFlow, cron |
| Scope | Standard (orgs, reports, concepts, entities, relationships) | Enough for opportunities + drafting |

---

## 9. Implementation Order

1. **Schema** — Add MLOrg, MLReport, MLOpportunity, extend MLEntity, add relationship types
2. **Script** — `enrich-meta-layer-graph.py` — Stages 2 + 3, takes chunk/source + user context path
3. **Ingestion** — Add "and enrich" trigger to URL/PDF flow; optional `--enrich` flag
4. **Skill** — "enrich graph" invokes script
5. **Opportunities sync** — MLOpportunity → `opportunities.json` (type, notes, source_url)

---

## 10. LLM Prompt Shape (for any tech article)

```
You are analyzing a tech article/report for a user interested in: [meta_layer_lens, key_projects].

Extract in JSON:
1. orgs: [{name, url?, type?}]
2. reports/publications: [{name, url?, author_org?, summary_1line?}]
3. concepts: [{name, definition_1line?}]
4. entities: [{name, type: person|org|coalition|policymaker}]
5. relationships: [{from, to, type: PUBLISHED|DISCUSSES|ADDRESSES|COLLABORATES_WITH}]
6. opportunities:
   - alignment: [{what, why_it_aligns, evidence}]
   - collaboration: [{what, how_to_engage, evidence}]
   - promotion: [{angle, format: substack|podcast|talk, evidence}]

Be concise. Only include what is clearly supported by the text.
```
