# Tags, Meme Occurrences & Quote Anchoring

Design for enriched meme analysis, cross-cutting tags, and source verification.

---

## Meme Occurrences (per-episode)

Each meme reference in an episode records:

| Field | Purpose |
|-------|---------|
| `episode` | Episode number |
| `video_timestamp` | When in the video (HH:MM:SS) |
| `quote` | Exact or near-exact quote where meme appears |
| `speaker_node_ref` | Who said it (N-1, N-2, etc.) — the node (person) who uttered it |
| `context` | Surrounding context or how it's used |
| `tags` | Analysis tags (see below) |

**Future analysis:** Enables queries like "when did N-2 use M-3?" or "all occurrences of M-1 in episode 4" or "memes used by host vs. quoted sources."

---

## Quote Anchoring

Store exact transcript snippets for verification:

| Entity | Field | Purpose |
|--------|-------|---------|
| Claims | `transcript_snippet` | Exact words from transcript that support this claim |
| Artifacts | `transcript_snippet` | Exact words where this artifact was referenced |
| Meme occurrences | `quote` | Exact transcript snippet (verbatim when possible) |

Enables re-verification against source and detection of hallucinated or misattributed quotes.

---

## Cross-reference IDs

Explicit links between entities in the **same episode** (Phase 2 remaps placeholders to A-/C-/N- IDs).

| Field | On | Purpose |
|-------|-----|---------|
| `contradicts_claim_refs` | Claim | Array of `CLAIM_n` this claim contradicts |
| `supports_claim_refs` | Claim | Array of `CLAIM_n` this claim supports or reinforces |
| `same_as_artifact_refs` | Artifact sub_item | Array of `ART_n.m` for duplicate display / same underlying document |

---

## Confidence & uncertainty

Optional on **claims**, **artifact sub_items**, **nodes**, and **meme occurrences**:

| Field | Purpose |
|-------|---------|
| `confidence` | `"high"` \| `"medium"` \| `"low"` — extractor confidence in attribution or reading |
| `uncertainty_note` | Short text when evidence is ambiguous, partial, or open to interpretation |

Use for triage, review queues, and avoiding overstated certainty in downstream analysis.

---

## Extraction metadata (`meta`)

Set automatically when Phase 1 JSON is saved (pipeline; not required from the LLM):

| Field | Purpose |
|-------|---------|
| `extraction_timestamp` | UTC ISO 8601 (e.g. `2026-03-18T12:00:00Z`) |
| `model_version` | LLM model id (best-effort from client / env) |
| `transcript_sha256` | SHA-256 (hex) of UTF-8 transcript used for that run |

Detects transcript changes and supports reproducibility / regression comparison.

---

## Tags

Tags enable filtering, grouping, and cross-cutting analysis. Apply to memes, nodes, artifacts, and claims.

### Meme tags (suggested)
- `coded_language` — Deliberately obscure
- `euphemism` — Softened substitute
- `derogatory` — Pejorative usage
- `insider` — Requires in-group knowledge
- `political` — Political framing
- `religious` — Religious context
- `historical` — References past events/movements
- `ironic` — Ironic or sarcastic use

### Node tags (suggested)
- `key_figure` — Central to investigation
- `witness` — Provides testimony/evidence
- `institution` — Organization, not person
- `discrepancy_target` — Subject of verification
- `host` — Episode host/presenter
- `quoted` — Quoted by host, not present

### Artifact tags (suggested)
- `court_filing` — Legal document
- `social_media` — Post, story, etc.
- `interview` — Interview clip/transcript
- `public_record` — Government/official record
- `screenshot` — Image capture
- `verbal_only` — Referenced but not shown

### Claim tags (suggested)
- `falsifiable` — Directly verifiable
- `contradiction` — Contradicts another claim
- `timeline` — About dates/sequence
- `identity` — About person's identity
- `financial` — Money, transactions
- `framing_premise` — Narrative framing (not evidence-backed)

**Usage:** Tags are arrays of strings. Use suggested tags when they fit; add custom tags as needed. Tags are optional.
