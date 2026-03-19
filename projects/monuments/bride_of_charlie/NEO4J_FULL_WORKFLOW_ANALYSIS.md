# Neo4j Across the Full OpenClaw Workflow

A comprehensive analysis of how Neo4j can enhance every stage of the investigative pipeline.

---

## Current Workflow Stages

1. **Fetch Transcripts** (YouTube → text)
2. **Fix Name Spellings** (transcript correction)
3. **Episode Analysis** (transcript → draft inscription)
4. **Verification** (numbering + name spelling)
5. **Cross-Episode Analysis** (synthesis across episodes)
6. **Review & Approval** (human review)
7. **Publish Inscriptions** (drafts → output)
8. **Feedback & Improvement** (protocol refinement)

Let's examine each stage...

---

## 1. Fetch Transcripts

### Current Process
```bash
python scripts/fetch_transcripts.py
# Downloads from YouTube
# Saves to transcripts/episode_001_*.txt
```

### What Neo4j Can Add

#### A. Transcript Metadata Storage

**Store:**
- YouTube URL
- Video title
- Upload date
- Duration
- Fetch timestamp
- Transcript quality score

**Schema:**
```cypher
CREATE (t:Transcript {
  id: "episode_001",
  youtube_url: "https://youtube.com/watch?v=...",
  title: "Bride of Charlie Episode 1",
  duration: "01:03:59",
  fetched_at: datetime(),
  quality_score: 0.95,  // Based on timestamp coverage
  word_count: 15000,
  has_timestamps: true
})
```

**Benefits:**
- Track which episodes have been fetched
- Re-fetch if quality is low
- Detect missing episodes
- Store video metadata for reference

**Query:**
```cypher
// Find episodes without transcripts
MATCH (e:Episode)
WHERE NOT EXISTS {
  MATCH (t:Transcript {id: "episode_" + toString(e.episode_num)})
}
RETURN e.episode_num AS missing
```

---

#### B. Transcript Change Tracking

**Problem:** If you re-fetch a transcript, how do you know what changed?

**Solution:**
```cypher
CREATE (t:Transcript {id: "episode_001", version: 2})
CREATE (t)-[:REPLACES]->(old:Transcript {id: "episode_001", version: 1})
SET t.changes = "Fixed speaker labels, corrected timestamps"
```

**Benefits:**
- Audit trail of transcript corrections
- Can roll back if needed
- Track improvement over time

---

## 2. Fix Name Spellings in Transcript

### Current Process
- Manual find/replace in transcript files
- Or: hope the LLM gets it right during analysis

### What Neo4j Can Add

#### A. Name Correction Dictionary

**Store verified spellings:**
```cypher
CREATE (nc:NameCorrection {
  incorrect: "Tyler Boyer",
  correct: "Tyler Bowyer",
  source: "DuckDuckGo + Wikipedia",
  confidence: "high",
  verified_date: date(),
  context: "Turning Point USA"
})
```

**Auto-apply to transcripts:**
```python
def correct_transcript_names(transcript_text: str, session) -> str:
    """Apply all verified name corrections to transcript."""
    corrections = session.run("""
        MATCH (nc:NameCorrection)
        WHERE nc.confidence IN ['high', 'medium']
        RETURN nc.incorrect, nc.correct
    """)
    
    for record in corrections:
        transcript_text = transcript_text.replace(
            record["incorrect"], 
            record["correct"]
        )
    
    return transcript_text
```

**Benefits:**
- Consistent corrections across all transcripts
- Build correction dictionary over time
- Auto-correct new transcripts
- Track correction confidence

---

#### B. Transcript Annotation

**Mark uncertain names in transcript:**
```cypher
CREATE (ta:TranscriptAnnotation {
  transcript_id: "episode_001",
  position: 1234,  // Character offset
  original_text: "Tyler Boyer",
  annotation_type: "name_uncertainty",
  suggested_correction: "Tyler Bowyer",
  confidence: "medium",
  created_by: "verify_drafts.py",
  created_at: datetime()
})
```

**Benefits:**
- Flag uncertain names for human review
- Track which corrections were applied
- Generate correction reports

---

## 3. Episode Analysis (Transcript → Draft)

### Current Process
```bash
python protocols/episode_analysis/episode_analysis_protocol.py
# LLM processes transcript → markdown draft
```

### What Neo4j Can Add

#### A. Real-Time Validation During Generation

**Problem:** LLM generates claim with non-existent artifact anchor. We only catch this later.

**Solution: Streaming Validation**

```python
def validate_claim_during_generation(claim_data: dict, session) -> list[str]:
    """Validate claim as LLM generates it."""
    errors = []
    
    # Check artifact exists
    for artifact_id in claim_data.get("anchored_artifacts", []):
        result = session.run(
            "MATCH (a:Artifact {id: $id}) RETURN count(a) AS count",
            id=artifact_id
        )
        if result.single()["count"] == 0:
            errors.append(f"Artifact {artifact_id} does not exist")
    
    # Check node exists
    for node_id in claim_data.get("related_nodes", []):
        result = session.run(
            "MATCH (n) WHERE n.id = $id RETURN count(n) AS count",
            id=node_id
        )
        if result.single()["count"] == 0:
            errors.append(f"Node {node_id} does not exist")
    
    # Check claim has artifact anchor
    if not claim_data.get("anchored_artifacts"):
        errors.append("Claim has no artifact anchor (protocol violation)")
    
    return errors
```

**Integration:**
```python
# In episode_analysis_protocol.py
for claim in parsed_claims:
    errors = validate_claim_during_generation(claim, neo4j_session)
    if errors:
        # Reject claim or flag for review
        print(f"⚠️  Claim {claim['id']}: {errors}")
```

**Benefits:**
- Catch errors during generation (not after)
- Reduce re-work
- Higher quality drafts
- Faster feedback loop

---

#### B. Suggested Node Reuse

**Problem:** LLM creates "N-15 Erica France Kirk" when "N-2 Erica Kirk" already exists.

**Solution: Query Before Creating**

```python
def suggest_existing_node(name: str, session) -> dict | None:
    """Check if similar node exists before creating new one."""
    result = session.run("""
        MATCH (n)
        WHERE (n:Person OR n:InvestigationTarget)
          AND (n.canonical_name = $name 
               OR $name IN n.aliases
               OR apoc.text.levenshteinDistance(n.canonical_name, $name) <= 2)
        RETURN n.id AS id, n.canonical_name AS name
        LIMIT 1
    """, name=name)
    
    record = result.single()
    return dict(record) if record else None
```

**Prompt enhancement:**
```
Before creating a new node, check if this person already exists:
- N-2: Erica Kirk (aliases: Erica France Kirk, Erica France)
- N-1: Charlie Kirk
- N-15: Tyler Bowyer (aliases: Tyler Boyer)

If the person exists, REUSE the existing node ID.
```

**Benefits:**
- Fewer duplicate nodes
- Better cross-episode continuity
- Less manual merging needed

---

#### C. Context Injection

**Provide LLM with cross-episode context:**

```python
def get_episode_context(episode_num: int, session) -> str:
    """Get context from previous episodes."""
    
    # Get recurring nodes
    recurring = session.run("""
        MATCH (n)-[:APPEARS_IN]->(e:Episode)
        WHERE e.episode_num < $episode_num
          AND (n:Person OR n:InvestigationTarget)
        WITH n, count(DISTINCT e) AS appearances
        WHERE appearances >= 2
        RETURN n.id, n.canonical_name, n.aliases, appearances
        ORDER BY appearances DESC
        LIMIT 10
    """, episode_num=episode_num)
    
    context = ["RECURRING ENTITIES (reuse these IDs):"]
    for record in recurring:
        aliases = ", ".join(record["aliases"] or [])
        context.append(
            f"- {record['id']}: {record['canonical_name']} "
            f"(appears in {record['appearances']} episodes)"
        )
        if aliases:
            context.append(f"  Aliases: {aliases}")
    
    return "\n".join(context)
```

**Add to system prompt:**
```python
system_prompt = build_system_prompt(
    protocol_md, 
    template_md, 
    ledger_context,
    episode_context=get_episode_context(episode_num, session)  # NEW
)
```

**Benefits:**
- LLM knows which nodes to reuse
- Better name consistency
- Fewer duplicates

---

## 4. Verification (Numbering + Names)

### Current Process
```bash
python scripts/verify_drafts.py
# Checks numbering + verifies names via DuckDuckGo
```

### What Neo4j Can Add (Already Implemented!)

✅ **Verification caching** — stores results  
✅ **Name standardization** — canonical names + aliases  
✅ **Cross-episode validation** — checks references  

**Additional Enhancement: Verification Confidence Scoring**

```cypher
// Calculate verification confidence based on multiple sources
MATCH (p:Person {id: "N-2"})
WITH p,
     CASE 
       WHEN p.verification_source CONTAINS 'Wikipedia' THEN 3
       WHEN p.verification_source CONTAINS 'DuckDuckGo' THEN 2
       ELSE 1
     END AS source_score,
     CASE
       WHEN size(p.aliases) = 0 THEN 3  // No variants = high confidence
       WHEN size(p.aliases) <= 2 THEN 2
       ELSE 1
     END AS consistency_score
SET p.verification_confidence_score = source_score + consistency_score
RETURN p.canonical_name, p.verification_confidence_score
```

**Benefits:**
- Prioritize low-confidence names for review
- Track verification quality over time

---

## 5. Cross-Episode Analysis

### Current Process
```bash
python scripts/cross_episode_analysis.py
# Synthesizes patterns across all episodes
```

### What Neo4j Can REALLY Shine

#### A. Pattern Detection Queries

**Co-occurrence Analysis:**
```cypher
// Find people who appear together frequently
MATCH (p1:Person)-[:APPEARS_IN]->(e:Episode)<-[:APPEARS_IN]-(p2:Person)
WHERE p1.id < p2.id
WITH p1, p2, collect(DISTINCT e.episode_num) AS episodes
WHERE size(episodes) >= 3
RETURN p1.canonical_name AS person1,
       p2.canonical_name AS person2,
       size(episodes) AS episodes_together,
       episodes
ORDER BY episodes_together DESC
```

**Output:**
```
Erica Kirk, Charlie Kirk: 5 episodes [1,2,3,5,7]
Erica Kirk, Tyler Bowyer: 3 episodes [2,3,4]
```

---

**Claim Clustering:**
```cypher
// Find claims about the same topic
MATCH (c:Claim)-[:INVOLVES]->(n:InvestigationTarget)
WITH n, collect(c) AS claims
WHERE size(claims) >= 3
RETURN n.canonical_name AS topic,
       size(claims) AS claim_count,
       [c IN claims | c.id] AS claim_ids
ORDER BY claim_count DESC
```

**Output:**
```
Date of Birth Discrepancy: 8 claims [C-1001, C-1009, C-1023, ...]
Educational Timeline Gap: 5 claims [C-1006, C-1015, C-1034, ...]
```

---

**Evidence Accumulation:**
```cypher
// Show how evidence builds over episodes
MATCH (n:Person {id: "N-2"})-[:APPEARS_IN]->(e:Episode)
OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(n)
OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(n)
WHERE a.episode_num <= e.episode_num
  AND c.episode_num <= e.episode_num
WITH e.episode_num AS episode,
     count(DISTINCT a) AS cumulative_artifacts,
     count(DISTINCT c) AS cumulative_claims
RETURN episode, cumulative_artifacts, cumulative_claims
ORDER BY episode
```

**Output:**
```
Episode 1: 2 artifacts, 3 claims
Episode 2: 5 artifacts, 8 claims
Episode 3: 8 artifacts, 12 claims
...
```

---

#### B. Contradiction Detection

```cypher
// Find conflicting claims about the same person
MATCH (c1:Claim)-[:INVOLVES]->(p:Person)<-[:INVOLVES]-(c2:Claim)
WHERE c1.id < c2.id
  AND c1.claim_text CONTAINS "DOB"
  AND c2.claim_text CONTAINS "DOB"
  AND c1.claim_text <> c2.claim_text
RETURN p.canonical_name,
       c1.id, c1.claim_text, c1.episode_num,
       c2.id, c2.claim_text, c2.episode_num
```

**Output:**
```
Erica Kirk:
  C-1001: "DOB is November 22, 1988" (Episode 1)
  C-1023: "DOB is November 20, 1988" (Episode 3)
```

**Benefits:**
- Auto-generate contradiction reports
- Flag for human review
- Track resolution over time

---

#### C. Timeline Reconstruction

```cypher
// Build chronological timeline for a person
MATCH (p:Person {id: "N-2"})<-[:INVOLVES]-(c:Claim)
WHERE c.claim_ts IS NOT NULL
WITH p, c
ORDER BY c.episode_num, c.claim_ts
RETURN c.episode_num AS episode,
       c.claim_ts AS timestamp,
       c.claim_text AS event
```

**Export to timeline visualization:**
```json
{
  "person": "Erica Kirk",
  "events": [
    {"date": "1988-11-20", "event": "Birth date (disputed)", "episode": 1},
    {"date": "1995", "event": "Attended Tesaract School", "episode": 1},
    {"date": "2019", "event": "Applied for Swedish citizenship", "episode": 1}
  ]
}
```

---

#### D. Network Analysis

```cypher
// Calculate centrality scores
CALL gds.pageRank.stream({
  nodeProjection: ['Person', 'InvestigationTarget'],
  relationshipProjection: {
    INVOLVES: {orientation: 'UNDIRECTED'}
  }
})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).canonical_name AS person,
       score
ORDER BY score DESC
LIMIT 10
```

**Output:**
```
Erica Kirk: 0.85
Charlie Kirk: 0.72
Tyler Bowyer: 0.45
...
```

**Benefits:**
- Identify central figures
- Prioritize investigation targets
- Visualize network structure

---

## 6. Review & Approval

### Current Process
- Human reviews drafts manually
- Moves approved files to output/

### What Neo4j Can Add

#### A. Review Workflow Tracking

```cypher
CREATE (r:Review {
  episode_num: 3,
  reviewer: "human_reviewer",
  status: "approved",
  reviewed_at: datetime(),
  notes: "Minor corrections needed in C-1025",
  corrections: ["Fixed spelling of 'Tesaract' to 'Tesseract'"]
})

MATCH (e:Episode {episode_num: 3})
CREATE (r)-[:REVIEWS]->(e)
```

**Benefits:**
- Track who reviewed what
- Store review notes
- Audit trail for corrections

---

#### B. Review Checklist Validation

```cypher
// Auto-generate review checklist
MATCH (e:Episode {episode_num: 3})
OPTIONAL MATCH (c:Claim)-[:FROM_EPISODE]->(e)
WHERE NOT (:Artifact)-[:ANCHORS]->(c)
WITH e, collect(c.id) AS claims_without_anchors

OPTIONAL MATCH (n)-[:APPEARS_IN]->(e)
WHERE (n:Person OR n:InvestigationTarget)
  AND n.verified_spelling IS NULL
WITH e, claims_without_anchors, collect(n.id) AS unverified_names

RETURN {
  episode: e.episode_num,
  claims_without_anchors: claims_without_anchors,
  unverified_names: unverified_names,
  ready_for_approval: size(claims_without_anchors) = 0 
                      AND size(unverified_names) = 0
}
```

**Output:**
```json
{
  "episode": 3,
  "claims_without_anchors": ["C-1025"],
  "unverified_names": ["N-18", "N-20"],
  "ready_for_approval": false
}
```

---

#### C. Diff Tracking

**Store what changed during review:**

```cypher
MATCH (c:Claim {id: "C-1025"})
CREATE (ch:Change {
  entity_type: "Claim",
  entity_id: "C-1025",
  field: "claim_text",
  old_value: "Erica attended Tesaract School",
  new_value: "Erica attended Tesseract School",
  changed_by: "human_reviewer",
  changed_at: datetime(),
  reason: "Spelling correction"
})
CREATE (ch)-[:MODIFIES]->(c)
```

**Benefits:**
- Audit trail of all corrections
- Learn from human corrections
- Improve LLM prompts based on patterns

---

## 7. Publish Inscriptions

### Current Process
```bash
# Manual: mv drafts/episode_003_*.md output/
```

### What Neo4j Can Add

#### A. Publication Status Tracking

```cypher
MATCH (e:Episode {episode_num: 3})
SET e.status = "published",
    e.published_at = datetime(),
    e.published_by = "human_reviewer"

CREATE (p:Publication {
  episode_num: 3,
  format: "markdown",
  location: "output/episode_003_final.md",
  published_at: datetime(),
  version: 1
})
CREATE (p)-[:PUBLISHES]->(e)
```

**Query publication status:**
```cypher
MATCH (e:Episode)
RETURN e.episode_num,
       e.status,
       e.published_at
ORDER BY e.episode_num
```

**Output:**
```
Episode 1: published (2026-03-10)
Episode 2: published (2026-03-11)
Episode 3: in_review
Episode 4: draft
```

---

#### B. Export Templates

**Generate publication-ready markdown from graph:**

```python
def export_person_dossier(person_id: str, session) -> str:
    """Generate markdown dossier for a person from Neo4j."""
    
    result = session.run("""
        MATCH (p:Person {id: $id})
        OPTIONAL MATCH (p)-[:APPEARS_IN]->(e:Episode)
        OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(p)
        OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(p)
        RETURN p,
               collect(DISTINCT e.episode_num) AS episodes,
               collect(DISTINCT {
                 id: c.id, 
                 label: c.label, 
                 text: c.claim_text,
                 episode: c.episode_num
               }) AS claims,
               collect(DISTINCT {
                 id: a.id, 
                 desc: a.description,
                 episode: a.episode_num
               }) AS artifacts
    """, id=person_id)
    
    record = result.single()
    
    # Generate markdown
    md = f"# {record['p']['canonical_name']}\n\n"
    md += f"**ID:** {record['p']['id']}\n"
    md += f"**Episodes:** {', '.join(map(str, record['episodes']))}\n\n"
    
    md += "## Claims\n\n"
    for claim in sorted(record['claims'], key=lambda x: x['episode']):
        md += f"- **{claim['id']}** (Episode {claim['episode']}): {claim['text']}\n"
    
    md += "\n## Evidence\n\n"
    for artifact in sorted(record['artifacts'], key=lambda x: x['episode']):
        md += f"- **{artifact['id']}** (Episode {artifact['episode']}): {artifact['desc']}\n"
    
    return md
```

**Benefits:**
- Auto-generate person dossiers
- Create investigation summaries
- Export to different formats (markdown, JSON, HTML)

---

#### C. Version Control

```cypher
// Track publication versions
MATCH (e:Episode {episode_num: 3})
CREATE (p:Publication {
  episode_num: 3,
  version: 2,
  published_at: datetime(),
  changes: "Corrected spelling errors, added C-1026"
})
CREATE (p)-[:PUBLISHES]->(e)
CREATE (p)-[:SUPERSEDES]->(old:Publication {episode_num: 3, version: 1})
```

**Benefits:**
- Track publication history
- Roll back if needed
- Compare versions

---

## 8. Feedback & Improvement

### Current Process
- Manual notes in protocol_updates/
- Ad-hoc protocol refinements

### What Neo4j Can Add

#### A. Error Pattern Analysis

```cypher
// Find most common validation errors
MATCH (ch:Change)
WHERE ch.reason CONTAINS "protocol violation"
RETURN ch.entity_type, ch.field, ch.reason, count(*) AS frequency
ORDER BY frequency DESC
LIMIT 10
```

**Output:**
```
Claim, anchored_artifacts, "Missing artifact anchor": 15
Node, canonical_name, "Duplicate node created": 8
Artifact, family_id, "Mixed evidentiary sources": 5
```

**Benefits:**
- Identify protocol weak points
- Prioritize improvements
- Measure improvement over time

---

#### B. Protocol Evolution Tracking

```cypher
CREATE (pr:ProtocolRevision {
  version: "2.1",
  date: date(),
  changes: [
    "Added requirement for Investigative Direction in claims",
    "Clarified artifact family bundling rules"
  ],
  reason: "15 claims lacked artifact anchors in episodes 1-3",
  impact: "Expected to reduce validation errors by 40%"
})

MATCH (pr_old:ProtocolRevision {version: "2.0"})
CREATE (pr)-[:SUPERSEDES]->(pr_old)
```

**Query protocol history:**
```cypher
MATCH (pr:ProtocolRevision)
RETURN pr.version, pr.date, pr.changes
ORDER BY pr.date DESC
```

---

#### C. Quality Metrics Over Time

```cypher
// Track quality improvement
MATCH (e:Episode)
OPTIONAL MATCH (c:Claim)-[:FROM_EPISODE]->(e)
WHERE NOT (:Artifact)-[:ANCHORS]->(c)
WITH e, count(c) AS claims_without_anchors

OPTIONAL MATCH (e2:Episode)
MATCH (c2:Claim)-[:FROM_EPISODE]->(e2)
WITH e, claims_without_anchors, count(c2) AS total_claims

RETURN e.episode_num AS episode,
       claims_without_anchors,
       total_claims,
       round(100.0 * claims_without_anchors / total_claims, 2) AS error_rate
ORDER BY e.episode_num
```

**Output:**
```
Episode 1: 5 errors / 12 claims = 41.67% error rate
Episode 2: 3 errors / 15 claims = 20.00% error rate
Episode 3: 1 error / 18 claims = 5.56% error rate
```

**Benefits:**
- Measure protocol effectiveness
- Track improvement over time
- Justify protocol changes with data

---

## Summary: Neo4j Across the Full Workflow

| Stage | Current | Neo4j Enhancement | Impact |
|-------|---------|-------------------|--------|
| **1. Fetch Transcripts** | Download → save | Store metadata, track versions, detect missing | Medium |
| **2. Fix Names** | Manual corrections | Auto-apply verified corrections, build dictionary | High |
| **3. Episode Analysis** | LLM generates draft | Real-time validation, suggest node reuse, inject context | Very High |
| **4. Verification** | Check numbering + names | ✅ Already enhanced (caching, standardization) | High |
| **5. Cross-Episode** | Manual synthesis | Pattern detection, contradiction finding, timeline export | Very High |
| **6. Review** | Manual review | Track workflow, auto-checklist, diff tracking | Medium |
| **7. Publish** | Manual file move | Status tracking, version control, auto-export | Medium |
| **8. Feedback** | Manual notes | Error analysis, protocol evolution, quality metrics | High |

---

## Highest Impact Enhancements

### 1. Real-Time Validation During Generation (Stage 3)
**Impact:** Catch errors immediately, reduce re-work by 50%+

### 2. Cross-Episode Pattern Detection (Stage 5)
**Impact:** Auto-generate insights, save hours of manual analysis

### 3. Name Correction Dictionary (Stage 2)
**Impact:** Consistent corrections, build knowledge over time

### 4. Context Injection (Stage 3)
**Impact:** Better node reuse, fewer duplicates

### 5. Quality Metrics Tracking (Stage 8)
**Impact:** Measure improvement, justify protocol changes

---

## Implementation Priority

**Phase 1: Already Done ✓**
- Verification caching
- Name standardization
- Node merging
- Cross-episode numbering

**Phase 2: High Impact (Recommend Next)**
1. Name correction dictionary (Stage 2)
2. Real-time validation (Stage 3)
3. Context injection (Stage 3)
4. Pattern detection queries (Stage 5)

**Phase 3: Quality of Life**
5. Transcript metadata (Stage 1)
6. Review workflow (Stage 6)
7. Publication tracking (Stage 7)
8. Quality metrics (Stage 8)

---

## Ready to Implement?

Which stages would you like me to enhance next?

1. **Name correction dictionary** — auto-fix transcripts
2. **Real-time validation** — catch errors during generation
3. **Context injection** — help LLM reuse nodes
4. **Pattern detection** — auto-generate cross-episode insights

Or all of them?
