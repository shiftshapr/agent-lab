# Structured Output and ID Collision Prevention

This document explains how **structured output** (JSON/JSON-LD) helps prevent claim and artifact ID collisions, and how it fits with the other collision-prevention strategies.

---

## JSON-LD and BRC222.org Alignment

Phase 1 entity extraction outputs **JSON-LD** compliant with [BRC222.org](https://brc222.org) for Bitcoin ordinals content bridging. Each output includes:

- **@context**: `https://brc222.org/context/v1` — vocabulary for types and properties
- **@type**: `EpisodeAnalysis` at root; `ArtifactFamily`, `Artifact`, `Claim`, `Person`, `InvestigationTarget` on entities
- **@id**: Canonical identifier for each entity (placeholder refs in Phase 1; real IDs after Phase 2)

A local context definition is in `templates/brc222_context.jsonld` for reference. The schema `entity_schema.json` validates JSON-LD structure.

---

## How Structured Output Helps

### 1. **Controlled ID assignment**

With free-form markdown, the LLM generates IDs inline (e.g. `**C-1000** Some claim`). There is no schema enforcing uniqueness or ordering.

With structured output, the schema can require IDs in a defined shape:

```json
{
  "claims": [
    { "id": "C-1009", "text": "...", "anchored_artifacts": ["A-1005.1"] }
  ]
}
```

IDs become explicit fields. The generation pipeline can:
- Validate IDs against the ledger before accepting output
- Reject or correct invalid IDs before converting to markdown

### 2. **Validation before write**

Structured data can be validated programmatically:

```python
def validate_ids(entities: dict, ledger: dict) -> list[str]:
    errors = []
    for c in entities.get("claims", []):
        cid = int(c["id"].split("-")[1])
        if cid < ledger["next_claim"]:
            errors.append(f"Claim {c['id']} collides with ledger")
    return errors
```

Invalid IDs can be rejected or rewritten before any file is written.

### Phase 1 validation (implemented)

`protocols/episode_analysis/phase1_validation.py`:

1. **JSON Schema** — `templates/entity_schema.json` (Draft 7) after extraction metadata is injected.
2. **Reference integrity** — All `anchored_artifacts`, `related_nodes`, `related_claims`, `contradicts_claim_refs`, `supports_claim_refs`, `same_as_artifact_refs`, and meme `speaker_node_ref` values must point at entities defined in the **same** Phase 1 document.

| Stage | Behavior |
|--------|----------|
| After Phase 1 parse | Run validation; print `[validation] …` lines. |
| **Strict (default)** | `EPISODE_ANALYSIS_STRICT_VALIDATION=1` (default): **do not write** `phase1_output/*.json` if any issue. |
| Non-strict | Set `EPISODE_ANALYSIS_STRICT_VALIDATION=0` to log warnings and still save (recovery / debugging). |
| Phase 2 (`assign_ids.py`) | Re-runs the same checks; fails batch/single-file with exit code 1 unless `--skip-validation`. |

Tests: `scripts/test_phase1_validation.py`.

**Human review queue:** When the project defines `scripts/canonical_nodes.py`, Phase 1 also appends `canonical/edge_cases.jsonl` entries for `phase1_validation` (any validation issues) and `extraction_review` (medium/low confidence or `uncertainty_note` on saved JSON). Disable extraction batching with `EPISODE_ANALYSIS_EXTRACTION_REVIEW=0`. See `CANONICAL_NODES_AND_LEARNING.md` and `IDEMPOTENT_CORRECTIONS.md`.

### 3. **Single source of truth**

In markdown, IDs appear in many places (headers, Related lines, Anchored Artifacts). Parsing is error-prone.

In JSON, each entity has one canonical representation. References use keys (e.g. `"anchored_artifacts": ["ART_1.1"]`) that are resolved in Phase 2. No duplicate ID strings to keep in sync.

### 4. **Post-processing**

JSON can be scanned and corrected for collisions before rendering:

```python
# Scan for collisions
# Rewrite IDs
# Render to markdown
```

The two-phase flow (extract → assign IDs) is a form of this: Phase 1 produces structured entities with placeholders; Phase 2 assigns real IDs from the ledger and renders.

### 5. **Tool use / function calling**

If the model uses tools (e.g. OpenAI function calling), ID assignment can be enforced by the tool interface:

- `create_claim(text, ...)` → backend assigns `C-{next_claim}` and increments
- The model never chooses the ID; the system does

---

## Implementation in Bride of Charlie

| Approach | Status | Location |
|---------|--------|----------|
| **Stronger prompt** | ✅ | `episode_analysis_protocol.py`, `bride_charlie_episode_analysis.md` |
| **Post-processing** | ✅ | `scripts/fix_collisions.py` |
| **Two-phase generation** | ✅ | Phase 1: all episodes → `phase1_output/`. Phase 2: batch assign from central ledger. `EPISODE_ANALYSIS_TWO_PHASE=1` |
| **Structured output** | ✅ | Phase 1 of two-phase outputs JSON; `entity_schema.json` |

---

## JSON-LD Schema (Phase 1 Entity Extraction)

The two-phase flow uses a JSON schema for Phase 1 output. See `../templates/entity_schema.json` for the full schema.

**JSON-LD / BRC222 structure:**
- Root: `@context`, `@type` (EpisodeAnalysis)
- Artifacts: `@type` (ArtifactFamily), `@id`, `family_ref`
- Sub-artifacts: `@type` (Artifact), `@id`, `ref`
- Nodes: `@type` (Person | InvestigationTarget), `@id`, `ref`
- Claims: `@type` (Claim), `@id`, `ref`

Key constraints:
- `artifacts[].family_ref`: string, pattern `ART_\d+`
- `artifacts[].sub_items[].ref`: string, pattern `ART_\d+\.\d+`
- `claims[].ref`: string, pattern `CLAIM_\d+`
- `nodes[].ref`: string, pattern `NODE_\d+` or `NODE_1\d{3}` for investigation targets

Phase 2 replaces placeholder refs with real IDs from the ledger. The protocol ensures `@context` and `@type` are present even if the LLM omits them.
