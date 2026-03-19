# Neo4j Integration Summary — Bride of Charlie

## What Was Added

Neo4j graph database integration for the Bride of Charlie investigative analysis pipeline.

---

## Files Created

### 1. `docker-compose.yml` (workspace/agent-lab/)
Neo4j 5.18 container configuration with:
- APOC plugin enabled
- Persistent volumes for data/logs
- Ports: 7474 (HTTP), 7687 (Bolt)
- Credentials: `neo4j` / `openclaw`
- Memory: 512MB initial, 2GB max heap

### 2. `scripts/neo4j_ingest.py`
Markdown parser that extracts OpenClaw entities and loads them into Neo4j:
- Parses `**A-XXXX**`, `**C-XXXX**`, `**N-X**` patterns from episode drafts
- Extracts timestamps, confidence levels, related IDs
- Creates nodes: `Episode`, `ArtifactFamily`, `Artifact`, `Claim`, `Person`, `InvestigationTarget`
- Creates relationships: `CONTAINS_FAMILY`, `HAS_ARTIFACT`, `ANCHORS`, `INVOLVES`, `FROM_EPISODE`, `APPEARS_IN`
- Enforces uniqueness constraints at DB level (prevents ID collisions)
- Supports `--force` flag to clear and re-ingest

### 3. `scripts/neo4j_validate.py`
Integrity validation script with Cypher queries:
- **Claims without artifact anchor** (CRITICAL) — violates Artifact Anchor Test
- **Artifacts without relationships** (WARNING) — violates Cross-Reference Rule
- **Nodes without evidence** (WARNING) — orphaned nodes
- **Claims without nodes** (CRITICAL) — violates protocol requirement
- **Broken artifact references** (CRITICAL) — dangling references
- **Broken node references** (CRITICAL) — dangling references
- Computes **Investigative Pressure** from graph edges (artifacts + claims × 2 + episodes)
- Displays graph statistics (episode count, artifact/claim/node counts, relationship counts)
- Shows ID ranges for all entity types

### 4. `NEO4J_SETUP.md`
Comprehensive setup guide with:
- Why Neo4j (benefits, error prevention)
- Prerequisites (Docker Desktop, Colima, OrbStack)
- Step-by-step setup instructions
- Usage examples (Cypher queries, validation, re-ingestion)
- Troubleshooting section
- Architecture diagram
- Graph schema documentation

### 5. `NEO4J_INTEGRATION_SUMMARY.md` (this file)
Implementation summary and usage guide.

---

## Files Modified

### 1. `protocols/episode_analysis/episode_analysis_protocol.py`
Added Neo4j integration to ledger scanning:
- **`scan_output_for_ids_neo4j()`** — queries Neo4j for max A-/C-/N- IDs via Cypher
- **`scan_output_for_ids_regex()`** — original regex-based file scanner (renamed)
- **`scan_output_for_ids()`** — smart dispatcher: tries Neo4j first, falls back to regex
- **`ingest_episode_to_neo4j()`** — post-run hook to auto-ingest new episodes
- Respects `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_AUTO_INGEST` env vars
- Prints which method is used: "Using Neo4j for ledger state" or "Using regex file scan"

### 2. `scripts/run_workflow.py`
Added validation step:
- **`step_validate()`** — runs `neo4j_validate.py` (skips if `NEO4J_URI` not set)
- Added `validate` step to workflow: `fetch | episodes | verify | cross | validate | all`
- Added `--validate` flag to run validation after `all` workflow completes
- Updated docstring with new step and flags

### 3. `.env.example`
Added Neo4j configuration template:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
NEO4J_AUTO_INGEST=true
```

### 4. `README.md`
Added Neo4j integration section:
- Benefits overview
- Quick start instructions
- Configuration guide
- Link to `NEO4J_SETUP.md`

---

## Graph Schema

```
Episode
  ├─[:CONTAINS_FAMILY]→ ArtifactFamily
  │                       └─[:HAS_ARTIFACT]→ Artifact
  │                                           ├─[:ANCHORS]→ Claim
  │                                           └─[:INVOLVES]→ Person | InvestigationTarget
  │
  └─[:FROM_EPISODE]← Claim
                      └─[:INVOLVES]→ Person | InvestigationTarget
                                      └─[:APPEARS_IN]→ Episode
```

**Node properties:**
- `ArtifactFamily`: `id`, `name`, `episode_num`
- `Artifact`: `id`, `description`, `event_ts`, `source_ts`, `video_ts`, `discovery_ts`, `confidence`, `episode_num`
- `Claim`: `id`, `label`, `claim_text`, `claim_ts`, `investigative_direction`, `episode_num`
- `Person`: `id`, `name`, `description`
- `InvestigationTarget`: `id`, `name`, `description`
- `Episode`: `episode_num`, `filename`

**Uniqueness constraints:**
- `Artifact.id`, `ArtifactFamily.id`, `Claim.id`, `Person.id`, `InvestigationTarget.id`, `Episode.episode_num`

---

## How It Prevents Errors

### 1. ID Collision Prevention
**Before:** Regex scanner could miss IDs in malformed markdown or skip files.
**After:** Uniqueness constraints at DB level — attempting to create `A-1007` when it exists raises immediately.

### 2. Orphaned Claims
**Before:** Manual inspection or custom scripts to find claims with no artifact anchor.
**After:** One Cypher query: `MATCH (c:Claim) WHERE NOT (:Artifact)-[:ANCHORS]->(c) RETURN c`

### 3. Dangling References
**Before:** Markdown could reference `Related: A-9999` when A-9999 doesn't exist — no validation.
**After:** Ingest script attempts to create relationship, fails if target doesn't exist (can be caught and logged).

### 4. Investigative Pressure Drift
**Before:** Manually maintained counters (`Evidence Count: 2`, `Claim Count: 3`) could become stale.
**After:** Computed from real edges: `count(DISTINCT artifacts) + count(DISTINCT claims) * 2 + count(DISTINCT episodes)`

### 5. Missing Bidirectional Links
**Before:** Protocol requires `C-1009 → N-2` and `N-2 → C-1009`, but no enforcement.
**After:** Can query: "Find claims that reference N-2 but N-2 doesn't reference back" — reveals asymmetry.

### 6. Cross-Episode Continuity
**Before:** Regex scan could fail if output directory structure changes or files are renamed.
**After:** Neo4j is the source of truth — query `max(A-ID)` always returns correct next ID regardless of file state.

---

## Usage Patterns

### Pattern 1: Existing workflow (no Neo4j)
```bash
python scripts/run_workflow.py all
```
- Uses regex file scanning for ledger state
- No validation step
- Works exactly as before

### Pattern 2: Neo4j for validation only
```bash
docker compose up -d
uv add neo4j
python scripts/neo4j_ingest.py          # One-time ingest
python scripts/run_workflow.py all --validate
```
- Uses regex for ledger state during episode analysis
- Ingests drafts to Neo4j after workflow completes
- Runs validation checks

### Pattern 3: Neo4j as source of truth (recommended)
Add to `.env`:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
NEO4J_AUTO_INGEST=true
```

```bash
docker compose up -d
uv add neo4j
python scripts/neo4j_ingest.py --force  # Initial load
python scripts/run_workflow.py all --validate
```
- Queries Neo4j for max IDs (no regex scanning)
- Auto-ingests each episode after analysis
- Runs validation at end
- Neo4j becomes the ledger

---

## Testing the Integration

### 1. Start Neo4j
```bash
cd ~/workspace/agent-lab
docker compose up -d
docker compose logs -f neo4j  # Wait for "Started."
```

### 2. Install driver
```bash
uv add neo4j
```

### 3. Ingest existing episodes
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py
```

Expected output:
```
[neo4j-ingest] Connecting to bolt://localhost:7687...
[neo4j-ingest] Ingesting 7 episode(s)...
  [1/7] episode_001_episode_001_ZAsV0fHGBiM.md
       OK (Episode 1)
  ...
[neo4j-ingest] Done. View graph at http://localhost:7474
```

### 4. Validate
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py
```

Expected: `RESULT: ALL CHECKS PASSED ✓`

### 5. View graph
Open [http://localhost:7474](http://localhost:7474)
Login: `neo4j` / `openclaw`

Try:
```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
```

### 6. Test ledger query
Add to `.env`:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
```

Run a dummy episode analysis:
```bash
EPISODE_ANALYSIS_PROJECT=bride_of_charlie \
EPISODE_ANALYSIS_INPUT=transcripts \
EPISODE_ANALYSIS_OUTPUT=drafts \
python protocols/episode_analysis/episode_analysis_protocol.py
```

Look for: `[episode-analysis] Using Neo4j for ledger state`

---

## Rollback / Disable Neo4j

To disable Neo4j and revert to regex scanning:

1. Remove `NEO4J_URI` from `.env`
2. Stop Neo4j: `docker compose down`

The protocol automatically falls back to regex scanning when `NEO4J_URI` is not set.

To completely remove:
```bash
docker compose down -v  # Remove volumes
rm docker-compose.yml
uv remove neo4j
```

---

## Next Steps

1. **User must start Docker** — Docker Desktop, Colima, or OrbStack
2. Run `docker compose up -d` to start Neo4j
3. Run `uv add neo4j` to install Python driver
4. Run `python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py` to load existing episodes
5. Run `python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py` to verify integrity
6. Add Neo4j config to `.env` to enable Neo4j-backed ledger queries

See `NEO4J_SETUP.md` for detailed instructions.

---

## Files Summary

**Created:**
- `workspace/agent-lab/docker-compose.yml`
- `projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py`
- `projects/monuments/bride_of_charlie/scripts/neo4j_validate.py`
- `projects/monuments/bride_of_charlie/NEO4J_SETUP.md`
- `projects/monuments/bride_of_charlie/NEO4J_INTEGRATION_SUMMARY.md`

**Modified:**
- `protocols/episode_analysis/episode_analysis_protocol.py`
- `projects/monuments/bride_of_charlie/scripts/run_workflow.py`
- `workspace/agent-lab/.env.example`
- `projects/monuments/bride_of_charlie/README.md`

**Total:** 9 files (5 created, 4 modified)
