# Phase 1: Entity Extraction (No IDs)

Extract entities from the episode transcript. Use PLACEHOLDER references only.
Do NOT use real A-, C-, N- IDs. Use [ART_n], [ART_n.m], [CLAIM_n], [NODE_n] instead.

Example: First artifact family = [ART_1], [ART_1.1], [ART_1.2]. First claim = [CLAIM_1].
IDs will be assigned in Phase 2 from the central ledger.

**Output must be JSON-LD compliant, aligned with BRC222.org** (https://brc222.org) for Bitcoin ordinals content bridging. Include @context and @type on the root and each entity.

---

## Output Format (JSON-LD)

Output valid JSON-LD only. No markdown, no commentary.

```json
{
  "@context": "https://brc222.org/context/v1",
  "@type": "EpisodeAnalysis",
  "meta": {
    "episode": 1,
    "source": "Candace Owens YouTube",
    "video_timestamp_range": "00:01:00–01:03:57",
    "extraction_timestamp": "2026-03-18T12:00:00Z",
    "model_version": "gpt-4o",
    "transcript_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  },
  "executive_summary": "2-4 sentences. Artifact-anchored only.",
  "artifacts": [
    {
      "@type": "ArtifactFamily",
      "@id": "ART_1",
      "family_ref": "ART_1",
      "bundle_name": "Birth Announcement Bundle",
      "sub_items": [
        {
          "@type": "Artifact",
          "@id": "ART_1.1",
          "ref": "ART_1.1",
          "description": "Newspaper Birth Announcement",
          "event_timestamp": "December 6, 1988",
          "source_timestamp": "November 20, 1988",
          "video_timestamp": "22:04–22:17",
          "discovery_timestamp": "2026-03-11",
          "related_claims": ["CLAIM_1"],
          "related_nodes": ["NODE_2", "NODE_1000"],
          "tags": ["public_record"],
          "transcript_snippet": "Here's the birth announcement from the newspaper—November 22, 1988.",
          "confidence": "high"
        },
        {
          "@type": "Artifact",
          "@id": "ART_1.2",
          "ref": "ART_1.2",
          "description": "Same announcement shown again later in episode",
          "video_timestamp": "45:00–45:10",
          "related_claims": ["CLAIM_1"],
          "related_nodes": ["NODE_2"],
          "same_as_artifact_refs": ["ART_1.1"]
        }
      ]
    }
  ],
  "nodes": [
    {
      "@type": "Person",
      "@id": "NODE_1",
      "ref": "NODE_1",
      "name": "Charlie Kirk",
      "type": "person",
      "description": "Primary subject.",
      "related_artifacts": ["ART_1.1"],
      "related_claims": ["CLAIM_1"],
      "tags": ["key_figure"]
    },
    {
      "@type": "Person",
      "@id": "NODE_2",
      "ref": "NODE_2",
      "name": "Candace Owens",
      "type": "person",
      "description": "Host.",
      "related_artifacts": ["ART_1.1"],
      "related_claims": ["CLAIM_1", "CLAIM_2"],
      "tags": ["host"]
    },
    {
      "@type": "Topic",
      "@id": "NODE_1000",
      "ref": "NODE_1000",
      "name": "Date of Birth Discrepancy",
      "type": "topic",
      "topic_kind": "discrepancy",
      "description": "Persistent inconsistency.",
      "related_artifacts": ["ART_1.1"],
      "related_claims": ["CLAIM_1"],
      "tags": ["discrepancy_target"],
      "confidence": "high"
    }
  ],
  "memes": [
    {
      "@type": "MemeAnalysis",
      "@id": "M-1",
      "ref": "M-1",
      "canonical_term": "Term from canonical dictionary",
      "type": "meme",
      "occurrences": [
        {
          "episode": 1,
          "video_timestamp": "12:34",
          "quote": "Exact transcript snippet (verbatim when possible)",
          "speaker_node_ref": "NODE_1",
          "context": "Surrounding context",
          "tags": ["political"],
          "confidence": "medium",
          "uncertainty_note": "Could be sarcastic; context ambiguous."
        }
      ],
      "context": "How it's used in this episode"
    }
  ],
  "claims": [
    {
      "@type": "Claim",
      "@id": "CLAIM_1",
      "ref": "CLAIM_1",
      "label": "DOB Listed as November 22, 1988",
      "claim_timestamp": "22:04",
      "claim": "One-sentence neutral description.",
      "anchored_artifacts": ["ART_1.1"],
      "related_nodes": ["NODE_2", "NODE_1000"],
      "investigative_direction": "Obtain certified copies.",
      "tags": ["falsifiable"],
      "transcript_snippet": "The birth announcement lists November 22, 1988 as the date.",
      "confidence": "high"
    },
    {
      "@type": "Claim",
      "@id": "CLAIM_2",
      "ref": "CLAIM_2",
      "label": "Alternate date cited elsewhere",
      "claim_timestamp": "30:00",
      "claim": "A different document suggests another birth date.",
      "anchored_artifacts": ["ART_1.2"],
      "related_nodes": ["NODE_2", "NODE_1000"],
      "investigative_direction": "Compare primary sources.",
      "tags": ["contradiction"],
      "transcript_snippet": "But this other listing says December 6.",
      "contradicts_claim_refs": ["CLAIM_1"],
      "supports_claim_refs": [],
      "confidence": "medium",
      "uncertainty_note": "Second document not fully legible on screen."
    }
  ]
}
```

---

## Nodes: people, topics, organizations, and places

- **People** (`@type` **`Person`**, `type`: **`person`**): `NODE_1` … `NODE_999` (placeholders before Phase 2).
- **Topics** (`@type` **`Topic`**, `type`: **`topic`**): `NODE_1000`, `NODE_1001`, … — discrepancies, verification threads, narrative patterns, thematic investigation rows. Set **`topic_kind`** when useful (e.g. `discrepancy`, `verification_thread`, `narrative_pattern`, `program_reference`, `other`). Legacy Phase 1 may still emit **`InvestigationTarget`** / **`investigation_target`**; the pipeline maps those to **Topic** in Neo4j unless they are clearly institutions (see below).
- **Organizations** (`@type` **`Organization`**, `type`: **`organization`** or legacy **`institution`**): companies, schools as entities, nonprofits, government agencies, political groups, media outlets, named programs treated as org-like. Set **`organization_kind`** when useful (e.g. `educational_institution`, `government_agency`, `program_or_initiative`, `other`). **One substantive mention is enough** — recurrence across episodes is not required.
- **Places** (`@type` **`Place`**, `type`: **`place`**): cities, regions, countries, venues, addresses when they are **first-class graph entities** (not every geographic mention). Set **`place_kind`** when useful (e.g. `city`, `region`, `country`, `venue`, `other`).
- **Memes** (`memes`): Use for **rhetorical pattern / euphemism / code** analysis. **Do not** put a named real-world program, institution, or place **only** under `memes` — it must also have a **node** when it is an investigable entity. Memes may **complement** nodes (e.g. linking two proper names rhetorically).

**Canonical naming:** Use correct **proper-name spellings** in `name` when established (e.g. **Tesseract School** for the school). Put caption/STT variants (**Tesaract**, **Tesseract**) in **`also_known_as`** on the same node so one node covers all spellings.

---

## Investigative graph extensions (optional top-level arrays)

Use these when the episode supports them; all cross-refs must point at `nodes` / `claims` / `artifacts` / `memes` defined in the **same** JSON.

- **`qualifies_claim_refs`** (on a **claim**): other `CLAIM_n` rows this claim narrows or conditions (Neo4j `QUALIFIES`).
- **`sensitive_topic_tags`** (on a **claim**): e.g. `fraud`, `trafficking` — **must** pair with non-empty **`anchored_artifacts`** (evidence-backed only).
- **`legal_matters`**: `{ "ref": "CASE_1", "name", "description?", "artifact_refs", "party_node_refs", "place_node_refs" }` — Phase 2 assigns global `LM-*` ids.
- **`organization_relationships`**: `{ "from_org_ref", "to_org_ref", "relation" }` with `relation` one of: `subsidiary_of`, `affiliated_with`, `contractor_for`, `funded_by`, `donated_to`, `parent_of`, `same_enterprise_as`.
- **`role_assertions`**: `{ "person_node_ref", "org_node_ref", "role_edge": "holds_role"|"member_of"|"chair_of", "role_title?" }`.
- **`node_equivalences`**: `{ "node_ref_a", "node_ref_b" }` — same entity, different names (Neo4j `SAME_AS`).
- **`provenance_links`**: `{ "from_ref": "CLAIM_n"|"ART_n.m", "to_ref": "ART_n.m", "relation": "cites_source"|"derived_from"|"recording_of" }`.
- **`topic_mentions`**: `{ "claim_ref", "topic_node_ref" }` — claim invokes a **Topic** (or legacy thematic node); Neo4j `MENTIONS_TOPIC`.
- **`meme_links`**: `{ "meme_ref": "M-1", "link_type": "invoked_by_claim"|"invoked_by_speaker"|"targets_node", plus the matching ref field }` — define the meme in **`memes`** first.

**Claim–claim logic:** Populate **`contradicts_claim_refs`** / **`supports_claim_refs`** whenever the episode juxtaposes incompatible or reinforcing statements — do not leave them empty by default when a contradiction is explicit.

---

Rules:
- Root: include "@context": "https://brc222.org/context/v1" and "@type": "EpisodeAnalysis".
- Each entity: include @type (ArtifactFamily, Artifact, Claim, Person, Topic, Organization, Place; legacy InvestigationTarget still accepted) and @id (same as ref).
- Use ART_1, ART_2, ... for artifact families. Sub-items: ART_1.1, ART_1.2.
- Use CLAIM_1, CLAIM_2, ... for claims.
- Use NODE_1, NODE_2, ... for people (N-1..N-999). Use NODE_1000, NODE_1001, ... for investigation targets.
- All refs must be consistent (e.g. if claim references ART_1.1, that ref must exist in artifacts).
- Memes: each occurrence must have episode, video_timestamp, quote (exact transcript snippet), speaker_node_ref (who said it). Add tags when useful.
- Quote anchoring: Include transcript_snippet on claims and artifacts, and quote (verbatim) on meme occurrences. Enables verification against source.
- Tags: optional arrays on nodes, artifacts, claims, and meme occurrences. Use suggested tags or add custom ones.
- Cross-references: On claims, use `contradicts_claim_refs`, `supports_claim_refs`, and `qualifies_claim_refs` (arrays of CLAIM_n in this episode). On artifact sub_items, use `same_as_artifact_refs` (ART_n.m) when the same underlying item appears twice.
- Confidence: Optional `confidence` = `high` | `medium` | `low` on claims, artifact sub_items, nodes, and meme occurrences. Optional `uncertainty_note` (string) when attribution or evidence is ambiguous.
- Extraction metadata: Pipeline sets `meta.extraction_timestamp` (UTC ISO), `meta.model_version`, and `meta.transcript_sha256` when saving Phase 1; you may omit these in LLM output—they are injected automatically.
