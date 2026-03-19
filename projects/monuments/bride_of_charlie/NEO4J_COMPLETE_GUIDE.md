# Neo4j Complete Implementation Guide — Bride of Charlie

All high-impact enhancements are now implemented! This guide shows you how to use everything.

---

## What Was Built

### Core Infrastructure ✓
1. **Docker setup** — Neo4j 5.18 with APOC
2. **Ingest script** — Parses markdown → graph
3. **Validation script** — Integrity checks
4. **Numbering helper** — Cross-episode continuity

### High-Impact Enhancements ✓
5. **Name correction dictionary** — Auto-fix transcripts
6. **Context injection** — Help LLM reuse nodes
7. **Pattern detection** — Auto-generate insights
8. **Quality metrics** — Track improvement
9. **Investigative assistant** — Answer questions with citations

---

## Complete Workflow (With All Enhancements)

### Stage 1: Prepare Transcripts

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie

# 1. Fetch transcripts (if needed)
python scripts/fetch_transcripts.py

# 2. Build name correction dictionary from previous episodes
python scripts/neo4j_corrections.py import-from-verify

# 3. Apply corrections to all transcripts
python scripts/neo4j_corrections.py apply-dir transcripts/

# Output: Corrected transcripts with verified spellings
```

---

### Stage 2: Generate Episodes

```bash
cd ~/workspace/agent-lab

# Clear Neo4j for fresh start
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force

# Run episode analysis (with context injection!)
python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes --force

# What happens:
# - Each episode gets cross-episode context (recurring nodes)
# - LLM reuses existing node IDs instead of creating duplicates
# - Fuzzy matching merges similar names automatically
# - Neo4j tracks ledger state
```

---

### Stage 3: Verify & Validate

```bash
# 1. Verify names (with caching)
python projects/monuments/bride_of_charlie/scripts/verify_drafts.py

# 2. Ingest to Neo4j (with fuzzy matching)
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force

# 3. Merge any remaining duplicates
python projects/monuments/bride_of_charlie/scripts/neo4j_merge.py --auto

# 4. Validate integrity
python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py
```

---

### Stage 4: Cross-Episode Analysis

```bash
# 1. Run pattern detection
python projects/monuments/bride_of_charlie/scripts/neo4j_patterns.py all \
  --output drafts/patterns_report.md

# 2. Run quality metrics
python projects/monuments/bride_of_charlie/scripts/neo4j_quality.py \
  --output drafts/quality_report.md

# 3. Generate cross-episode synthesis (existing script)
python projects/monuments/bride_of_charlie/scripts/cross_episode_analysis.py
```

---

### Stage 5: Interactive Investigation

```bash
# Start investigative assistant
python projects/monuments/bride_of_charlie/scripts/investigative_assistant.py
```

**Example session:**
```
Q: person Erica

Found 1 person(s):
  N-2: Erica Kirk (aliases: Erica France Kirk, Erica France)

Q: report N-2

# Erica Kirk

**ID:** N-2
**Aliases:** Erica France Kirk, Erica France
**Episodes:** 1, 2, 3, 4, 5, 6, 7
**Evidence:** 15 artifacts, 23 claims

## Claims (23)

### C-1001: Birth Date Discrepancy
**Episode 1** (Timestamp: 22:04)

The episode presents that Erica's DOB appears as November 22, 1988...

**Anchored Artifacts:** A-1001.1, A-1000.1
**Investigative Direction:** Obtain certified birth certificate...

[... full report with all claims, artifacts, timeline ...]

Q: contradictions N-2

Found 2 potential contradiction(s):

About: Erica Kirk
  C-1001 (Episode 1): DOB is November 22, 1988
  C-1023 (Episode 3): DOB is November 20, 1988
  Similarity: 87%
```

---

## Tool Reference

### 1. Name Corrections (`neo4j_corrections.py`)

```bash
# Add correction manually
python scripts/neo4j_corrections.py add "Tyler Boyer" "Tyler Bowyer" --confidence high

# List all corrections
python scripts/neo4j_corrections.py list

# Import from verified nodes
python scripts/neo4j_corrections.py import-from-verify

# Apply to single file
python scripts/neo4j_corrections.py apply transcripts/episode_001.txt

# Apply to all transcripts
python scripts/neo4j_corrections.py apply-dir transcripts/
```

---

### 2. Investigative Assistant (`investigative_assistant.py`)

```bash
# Interactive mode
python scripts/investigative_assistant.py

# Export person report
python scripts/investigative_assistant.py --export person --id N-2 \
  --output reports/erica_kirk.md

# Export investigation targets
python scripts/investigative_assistant.py --export targets
```

**Interactive commands:**
- `person <name>` — Search for person
- `claims <keyword>` — Search claims
- `contradictions` — Find contradictions
- `targets` — List investigation targets
- `report <person_id>` — Generate full report
- `quit` — Exit

---

### 3. Pattern Detection (`neo4j_patterns.py`)

```bash
# Run all analyses
python scripts/neo4j_patterns.py all --output patterns_report.md

# Specific analyses
python scripts/neo4j_patterns.py co-occurrence
python scripts/neo4j_patterns.py contradictions --keyword "DOB"
python scripts/neo4j_patterns.py network
python scripts/neo4j_patterns.py summary
```

**Detects:**
- Co-occurrence (who appears together)
- Contradictions (conflicting claims)
- Network centrality (most connected)
- Episode summaries

---

### 4. Quality Metrics (`neo4j_quality.py`)

```bash
# Generate quality report
python scripts/neo4j_quality.py --output quality_report.md

# Compare two episodes
python scripts/neo4j_quality.py --compare 1 7
```

**Tracks:**
- Protocol compliance score per episode
- Evidence density (artifacts per claim)
- Node reuse rate
- Error trends over time

---

### 5. Numbering Helper (`neo4j_numbering.py`)

```bash
# Get next available IDs
python scripts/neo4j_numbering.py next

# Validate episode sequence
python scripts/neo4j_numbering.py validate --episode 3

# Generate numbering report
python scripts/neo4j_numbering.py report --episode 3

# Show node reuse
python scripts/neo4j_numbering.py reuse
```

---

### 6. Node Merge Tool (`neo4j_merge.py`)

```bash
# Interactive mode
python scripts/neo4j_merge.py

# Auto-merge
python scripts/neo4j_merge.py --auto

# Dry-run
python scripts/neo4j_merge.py --dry-run --threshold 2
```

---

## Example: Full Run-Through

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie

# ===== STAGE 1: PREPARE =====

# Backup existing drafts
mv drafts drafts_backup_$(date +%Y%m%d)
mkdir drafts

# Build correction dictionary
python scripts/neo4j_corrections.py import-from-verify

# Apply corrections to transcripts
python scripts/neo4j_corrections.py apply-dir transcripts/

# ===== STAGE 2: GENERATE =====

# Clear Neo4j
python scripts/neo4j_ingest.py --force

# Run episode analysis (with context injection)
cd ~/workspace/agent-lab
python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes --force

# ===== STAGE 3: VERIFY =====

cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie

# Verify names (builds cache)
python scripts/verify_drafts.py

# Ingest with fuzzy matching
python scripts/neo4j_ingest.py --force

# Merge duplicates
python scripts/neo4j_merge.py --auto

# Validate
python scripts/neo4j_validate.py

# ===== STAGE 4: ANALYZE =====

# Generate pattern report
python scripts/neo4j_patterns.py all --output drafts/patterns_report.md

# Generate quality report
python scripts/neo4j_quality.py --output drafts/quality_report.md

# Run cross-episode synthesis
cd ~/workspace/agent-lab
python projects/monuments/bride_of_charlie/scripts/cross_episode_analysis.py

# ===== STAGE 5: INVESTIGATE =====

cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie

# Start assistant
python scripts/investigative_assistant.py

# Or export specific reports
python scripts/investigative_assistant.py --export person --id N-2 \
  --output reports/erica_kirk_dossier.md
```

---

## Investigative Assistant Examples

### Search for a Person

```
Q: person Erica

Found 1 person(s):
  N-2: Erica Kirk (aliases: Erica France Kirk, Erica France)
```

### Get Full Report

```
Q: report N-2

# Erica Kirk

**ID:** N-2
**Aliases:** Erica France Kirk, Erica France
**Episodes:** 1, 2, 3, 4, 5, 6, 7
**Evidence:** 15 artifacts, 23 claims

## Claims (23)

### C-1001: Birth Date Discrepancy
**Episode 1** (Timestamp: 22:04)

The episode presents that Erica's DOB appears as November 22, 1988...

**Anchored Artifacts:** A-1001.1, A-1000.1
**Investigative Direction:** Obtain certified birth certificate...

[... continues with all claims, artifacts, connections, timeline ...]
```

### Search Claims

```
Q: claims birth date

Found 3 claim(s):

  C-1001 (Episode 1): Birth Date Discrepancy Between Newspaper and Divorce Filing
    Entities: Erica Kirk, Date of Birth Discrepancy
    The episode presents that Erica's DOB appears as November 22, 1988...

  C-1023 (Episode 3): Birth Date Listed as November 20, 1988
    Entities: Erica Kirk, Date of Birth Discrepancy
    Court filing shows DOB as November 20, 1988...
```

### Find Contradictions

```
Q: contradictions

Found 2 potential contradiction(s):

About: Erica Kirk
  C-1001 (Episode 1): The episode presents that Erica's DOB appears as November 22, 1988
  C-1023 (Episode 3): Court filing shows DOB as November 20, 1988
  Similarity: 87%
```

### List Investigation Targets

```
Q: targets

Investigation Targets (8):

  N-1000: Date of Birth Discrepancy
    Pressure Score: 45 (8 artifacts, 12 claims, 7 episodes)
    Persistent inconsistency between documented DOB and publicly used DOB.

  N-1001: Educational Timeline Gap
    Pressure Score: 28 (5 artifacts, 7 claims, 4 episodes)
    Missing documentation for education claims.
```

---

## Cypher Queries for Investigation

### Find All Claims About a Topic

```cypher
MATCH (c:Claim)
WHERE c.claim_text CONTAINS "birth" OR c.label CONTAINS "birth"
RETURN c.id, c.label, c.claim_text, c.episode_num
ORDER BY c.episode_num
```

### Show Evidence Trail for a Person

```cypher
MATCH (p:Person {id: "N-2"})
MATCH (a:Artifact)-[:INVOLVES]->(p)
MATCH (a)-[:ANCHORS]->(c:Claim)
RETURN a.id AS artifact,
       a.description,
       a.episode_num,
       collect(c.id) AS claims_supported
ORDER BY a.episode_num
```

### Find Weakly Supported Claims

```cypher
MATCH (c:Claim)
OPTIONAL MATCH (a:Artifact)-[:ANCHORS]->(c)
WITH c, count(a) AS artifact_count
WHERE artifact_count <= 1
RETURN c.id, c.label, artifact_count, c.episode_num
ORDER BY artifact_count, c.episode_num
```

### Timeline for a Person

```cypher
MATCH (p:Person {id: "N-2"})
MATCH (c:Claim)-[:INVOLVES]->(p)
WHERE c.claim_ts IS NOT NULL
RETURN c.episode_num, c.claim_ts, c.claim_text
ORDER BY c.episode_num, c.claim_ts
```

---

## Configuration

### .env File

```bash
# LLM
OPENAI_BASE_URL=http://localhost:11434/v1
MODEL_NAME=qwen2.5:7b

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
NEO4J_AUTO_INGEST=true
```

---

## Files Created (Total: 14)

### Core (4)
1. `docker-compose.yml`
2. `scripts/neo4j_ingest.py`
3. `scripts/neo4j_validate.py`
4. `scripts/neo4j_numbering.py`

### Enhancements (5)
5. `scripts/neo4j_corrections.py` — Name correction dictionary
6. `scripts/investigative_assistant.py` — Q&A with citations
7. `scripts/neo4j_patterns.py` — Pattern detection
8. `scripts/neo4j_quality.py` — Quality metrics
9. `protocols/episode_analysis/neo4j_context.py` — Context injection

### Documentation (5)
10. `NEO4J_SETUP.md`
11. `NEO4J_ENHANCEMENTS_README.md`
12. `NEO4J_COMPLETE_GUIDE.md` (this file)
13. `NEO4J_QUICK_REFERENCE.md`
14. `PRE_RUN_CHECKLIST.md`

### Files Modified (5)
1. `protocols/episode_analysis/episode_analysis_protocol.py` — Context injection
2. `scripts/verify_drafts.py` — Verification caching
3. `scripts/run_workflow.py` — Validation step
4. `templates/bride_charlie_episode_analysis.md` — Fixed node format
5. `.env.example` — Neo4j config

---

## Quick Start

```bash
# 1. Start Neo4j
cd ~/workspace/agent-lab
docker compose up -d

# 2. Backup existing drafts
cd projects/monuments/bride_of_charlie
mv drafts drafts_backup_$(date +%Y%m%d)
mkdir drafts

# 3. Clear Neo4j
python scripts/neo4j_ingest.py --force

# 4. Run workflow
cd ~/workspace/agent-lab
python projects/monuments/bride_of_charlie/scripts/run_workflow.py episodes --force

# 5. Verify & validate
cd projects/monuments/bride_of_charlie
python scripts/verify_drafts.py
python scripts/neo4j_ingest.py --force
python scripts/neo4j_merge.py --auto
python scripts/neo4j_validate.py

# 6. Generate reports
python scripts/neo4j_patterns.py all --output drafts/patterns.md
python scripts/neo4j_quality.py --output drafts/quality.md

# 7. Investigate
python scripts/investigative_assistant.py
```

---

## Key Benefits

### Before Neo4j
- Manual ID tracking (regex file scanning)
- No name standardization
- No verification caching
- Manual cross-episode analysis
- No quality metrics
- No way to query the data

### After Neo4j
✅ **Automatic ID management** — graph is source of truth  
✅ **Name standardization** — fuzzy matching + aliases  
✅ **Verification caching** — no re-searching  
✅ **Context injection** — LLM reuses nodes correctly  
✅ **Pattern detection** — auto-generates insights  
✅ **Quality tracking** — measures improvement  
✅ **Interactive investigation** — Q&A with citations  

---

## Investigative Assistant Capabilities

The assistant can answer:

**"What do we know about Erica Kirk's birth date?"**
→ Returns all claims about DOB with artifact anchors and episode references

**"Who appears most frequently across episodes?"**
→ Returns people ranked by episode count

**"What are the contradictions in the investigation?"**
→ Returns conflicting claims with similarity scores

**"Show me the timeline for Erica Kirk"**
→ Returns chronological events with episode and timestamp

**"Who is connected to Tyler Bowyer?"**
→ Returns people who co-appear in episodes

**"What are the highest-pressure investigation targets?"**
→ Returns targets ranked by evidence accumulation

**"Generate a full report on N-2"**
→ Exports comprehensive markdown dossier with all claims, artifacts, connections, timeline

---

## Advanced Queries

### Find Claim Chains

```cypher
// Find claims that reference each other
MATCH (c1:Claim)-[:INVOLVES]->(n)<-[:INVOLVES]-(c2:Claim)
WHERE c1.episode_num < c2.episode_num
RETURN c1.id, c1.label, c1.episode_num,
       n.canonical_name,
       c2.id, c2.label, c2.episode_num
ORDER BY c1.episode_num, c2.episode_num
```

### Evidence Strength by Claim

```cypher
MATCH (c:Claim)
OPTIONAL MATCH (a:Artifact)-[:ANCHORS]->(c)
WITH c, count(a) AS artifact_count,
     avg(CASE a.confidence 
         WHEN 'High' THEN 3 
         WHEN 'Medium' THEN 2 
         WHEN 'Low' THEN 1 
         ELSE 0 END) AS avg_confidence
RETURN c.id, c.label, artifact_count, 
       round(artifact_count * avg_confidence, 2) AS strength_score
ORDER BY strength_score DESC
LIMIT 20
```

### Artifact Usage

```cypher
// Find artifacts used in multiple claims
MATCH (a:Artifact)-[:ANCHORS]->(c:Claim)
WITH a, collect(c.id) AS claims
WHERE size(claims) >= 2
RETURN a.id, a.description, size(claims) AS claim_count, claims
ORDER BY claim_count DESC
```

---

## Troubleshooting

### "APOC procedure not found"

Restart Neo4j:
```bash
docker compose down
docker compose up -d
```

### Context injection not working

Check that `neo4j_context.py` is importable:
```bash
cd ~/workspace/agent-lab
python -c "from protocols.episode_analysis.neo4j_context import get_episode_context; print('OK')"
```

### Assistant returns "No results"

Make sure data is ingested:
```bash
python scripts/neo4j_ingest.py --force
```

---

## Next Steps

1. **Backup drafts** ✓
2. **Fix template** ✓ (already done)
3. **Clear Neo4j** — `python scripts/neo4j_ingest.py --force`
4. **Run episodes** — `python scripts/run_workflow.py episodes --force`
5. **Validate** — `python scripts/neo4j_validate.py`
6. **Investigate** — `python scripts/investigative_assistant.py`

---

## Summary

Neo4j is now a **complete investigative platform**:

✅ Ledger management  
✅ Name standardization  
✅ Verification caching  
✅ Context injection  
✅ Pattern detection  
✅ Quality metrics  
✅ Interactive Q&A  

The graph is your **investigative memory** that gets smarter with each episode!
