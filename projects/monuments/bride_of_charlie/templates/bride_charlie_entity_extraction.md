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
      "@type": "InvestigationTarget",
      "@id": "NODE_1000",
      "ref": "NODE_1000",
      "name": "Date of Birth Discrepancy",
      "type": "investigation_target",
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

## Nodes: people, investigations, institutions, and programs

- **People** (`type`: `person`): `NODE_1` … `NODE_999` (placeholders before Phase 2).
- **Investigation targets** (`type`: `investigation_target`): `NODE_1000`, `NODE_1001`, … — discrepancies, verification goals, **named schools under investigation**, etc.
- **Institutions / government programs** (same bucket as investigation targets when not a natural person): Create a **`InvestigationTarget`** (or `institution` when using that type) **whenever** the episode **substantively names** e.g.:
  - a **government or military program** (e.g. **MK Ultra**, a named **CIA** program such as **Project Looking Glass**),
  - a **regulatory or legislative program** referred to as a proper name,
  - a **school or company** as an investigable entity.
  **Do not** require the topic to recur in other episodes. **One mention is enough** if it is developed beyond a passing word.
- **Memes** (`memes`): Use for **rhetorical pattern / euphemism / code** analysis. **Do not** put a named real-world program or institution **only** under `memes` — it must also have a **node** if it is an investigable entity. Memes may **complement** nodes (e.g. linking two proper names rhetorically).

**Canonical naming:** Use correct **proper-name spellings** in `name` when established (e.g. **Tesseract School** for the school). Put caption/STT variants (**Tesaract**, **Tesseract**) in **`also_known_as`** on the same node so one node covers all spellings.

---

Rules:
- Root: include "@context": "https://brc222.org/context/v1" and "@type": "EpisodeAnalysis".
- Each entity: include @type (ArtifactFamily, Artifact, Claim, Person, InvestigationTarget) and @id (same as ref).
- Use ART_1, ART_2, ... for artifact families. Sub-items: ART_1.1, ART_1.2.
- Use CLAIM_1, CLAIM_2, ... for claims.
- Use NODE_1, NODE_2, ... for people (N-1..N-999). Use NODE_1000, NODE_1001, ... for investigation targets.
- All refs must be consistent (e.g. if claim references ART_1.1, that ref must exist in artifacts).
- Memes: each occurrence must have episode, video_timestamp, quote (exact transcript snippet), speaker_node_ref (who said it). Add tags when useful.
- Quote anchoring: Include transcript_snippet on claims and artifacts, and quote (verbatim) on meme occurrences. Enables verification against source.
- Tags: optional arrays on nodes, artifacts, claims, and meme occurrences. Use suggested tags or add custom ones.
- Cross-references: On claims, use `contradicts_claim_refs` and `supports_claim_refs` (arrays of CLAIM_n in this episode). On artifact sub_items, use `same_as_artifact_refs` (ART_n.m) when the same underlying item appears twice.
- Confidence: Optional `confidence` = `high` | `medium` | `low` on claims, artifact sub_items, nodes, and meme occurrences. Optional `uncertainty_note` (string) when attribution or evidence is ambiguous.
- Extraction metadata: Pipeline sets `meta.extraction_timestamp` (UTC ISO), `meta.model_version`, and `meta.transcript_sha256` when saving Phase 1; you may omit these in LLM output—they are injected automatically.
