# Neo4j Workflow Enhancements — Beyond Ledger Management

## Current Use: Ledger & Validation

Right now, Neo4j is used for:
1. ID continuity (max A-/C-/N- IDs)
2. Integrity validation (orphaned claims, dangling references)

But Neo4j can do **much more** across the entire OpenClaw workflow.

---

## 1. Name Standardization & Entity Resolution

### The Problem

The OpenClaw protocol says: "Preserve exact names unless certain. If uncertain, preserve the name exactly as it appears and flag uncertainty."

But across 7 episodes, the same person might appear as:
- "Erica Kirk"
- "Erica France Kirk"
- "Erica France"
- "Erica K."

Without standardization:
- Investigative Pressure is fragmented across multiple nodes
- Cross-episode queries miss connections
- The graph doesn't reflect that these are the same person

### How Neo4j Helps

#### A. Entity Merging with Aliases

```cypher
// Create a canonical Person node with aliases
MERGE (p:Person {id: "N-2"})
SET p.canonical_name = "Erica Kirk",
    p.aliases = ["Erica France Kirk", "Erica France", "Erica K."]

// Query by any variant
MATCH (p:Person)
WHERE p.canonical_name = "Erica Kirk" 
   OR "Erica France" IN p.aliases
RETURN p
```

#### B. Fuzzy Name Matching During Ingest

Add to `neo4j_ingest.py`:

```python
def find_or_create_person(session, name: str, node_id: str) -> str:
    """
    Find existing person by fuzzy name match or create new.
    Returns canonical node ID.
    """
    # Check for exact match
    result = session.run(
        "MATCH (p:Person) "
        "WHERE p.canonical_name = $name OR $name IN p.aliases "
        "RETURN p.id AS id",
        name=name
    )
    record = result.single()
    if record:
        return record["id"]
    
    # Check for fuzzy match (Levenshtein distance, soundex, etc.)
    result = session.run(
        "MATCH (p:Person) "
        "WHERE apoc.text.levenshteinDistance(p.canonical_name, $name) < 3 "
        "RETURN p.id AS id, p.canonical_name AS canonical",
        name=name
    )
    record = result.single()
    if record:
        # Add as alias
        session.run(
            "MATCH (p:Person {id: $id}) "
            "SET p.aliases = coalesce(p.aliases, []) + $name",
            id=record["id"],
            name=name
        )
        print(f"  → Merged '{name}' into {record['canonical']} ({record['id']})")
        return record["id"]
    
    # Create new
    session.run(
        "MERGE (p:Person {id: $id}) "
        "SET p.canonical_name = $name, p.aliases = []",
        id=node_id,
        name=name
    )
    return node_id
```

#### C. Name Standardization Report

```cypher
// Find potential duplicates (similar names)
MATCH (p1:Person), (p2:Person)
WHERE p1.id < p2.id
  AND apoc.text.levenshteinDistance(p1.canonical_name, p2.canonical_name) < 5
RETURN p1.id, p1.canonical_name, p2.id, p2.canonical_name,
       apoc.text.levenshteinDistance(p1.canonical_name, p2.canonical_name) AS distance
ORDER BY distance
```

---

## 2. Cross-Episode Pattern Detection

### The Problem

Patterns emerge across episodes:
- Person X appears in episodes 1, 3, 5, 7
- Institution Y is mentioned alongside Person Z in 4 episodes
- Artifact family A always involves Node N

These patterns are hard to spot in flat markdown.

### How Neo4j Helps

#### A. Co-occurrence Analysis

```cypher
// Find people who appear together frequently
MATCH (p1:Person)-[:APPEARS_IN]->(e:Episode)<-[:APPEARS_IN]-(p2:Person)
WHERE p1.id < p2.id
WITH p1, p2, count(DISTINCT e) AS episodes_together
WHERE episodes_together > 2
RETURN p1.canonical_name, p2.canonical_name, episodes_together
ORDER BY episodes_together DESC
```

#### B. Network Centrality

```cypher
// Find most connected people (PageRank-style)
CALL gds.pageRank.stream({
  nodeProjection: ['Person', 'InvestigationTarget'],
  relationshipProjection: {
    INVOLVES: {
      type: 'INVOLVES',
      orientation: 'UNDIRECTED'
    }
  }
})
YIELD nodeId, score
RETURN gds.util.asNode(nodeId).canonical_name AS person, score
ORDER BY score DESC
LIMIT 10
```

#### C. Timeline Reconstruction

```cypher
// Show when each person first appears and how their involvement grows
MATCH (p:Person)-[:APPEARS_IN]->(e:Episode)
WITH p, e
ORDER BY e.episode_num
WITH p, collect(e.episode_num) AS episodes
RETURN p.canonical_name, 
       episodes[0] AS first_episode,
       size(episodes) AS total_episodes,
       episodes AS episode_list
ORDER BY first_episode, total_episodes DESC
```

---

## 3. Claim Verification Workflow

### The Problem

Claims need verification:
- "Erica's DOB is November 22, 1988" (from Episode 1)
- "Erica's DOB is November 20, 1988" (from Episode 3)

These contradictions should be flagged and tracked.

### How Neo4j Helps

#### A. Contradiction Detection

```cypher
// Find claims about the same person with conflicting statements
MATCH (c1:Claim)-[:INVOLVES]->(p:Person)<-[:INVOLVES]-(c2:Claim)
WHERE c1.id < c2.id
  AND c1.claim_text CONTAINS "DOB"
  AND c2.claim_text CONTAINS "DOB"
  AND c1.claim_text <> c2.claim_text
RETURN p.canonical_name, 
       c1.id, c1.claim_text, c1.episode_num,
       c2.id, c2.claim_text, c2.episode_num
```

#### B. Verification Status Tracking

Add properties to claims:

```cypher
// Mark claim as verified/disputed/pending
MATCH (c:Claim {id: "C-1001"})
SET c.verification_status = "VERIFIED",
    c.verification_date = date(),
    c.verification_source = "Certified birth certificate obtained"
```

#### C. Evidence Strength Scoring

```cypher
// Calculate evidence strength based on artifact count and confidence
MATCH (a:Artifact)-[:ANCHORS]->(c:Claim)
WITH c, count(a) AS artifact_count,
     avg(CASE a.confidence 
         WHEN 'High' THEN 3 
         WHEN 'Medium' THEN 2 
         WHEN 'Low' THEN 1 
         ELSE 0 END) AS avg_confidence
SET c.evidence_strength = artifact_count * avg_confidence
RETURN c.id, c.label, c.evidence_strength
ORDER BY c.evidence_strength DESC
```

---

## 4. Automated Protocol Compliance

### The Problem

The LLM might:
- Create claims without artifact anchors
- Reference non-existent IDs
- Use inconsistent node names

These should be caught **before** the draft is finalized.

### How Neo4j Helps

#### A. Real-Time Validation During Generation

Modify `episode_analysis_protocol.py` to validate **as the LLM generates**:

```python
def validate_claim_before_insert(claim_data: dict) -> list[str]:
    """Validate claim against Neo4j before writing to markdown."""
    errors = []
    
    # Check artifact anchors exist
    for artifact_id in claim_data["anchored_artifacts"]:
        result = session.run(
            "MATCH (a:Artifact {id: $id}) RETURN count(a) AS count",
            id=artifact_id
        )
        if result.single()["count"] == 0:
            errors.append(f"Artifact {artifact_id} does not exist")
    
    # Check nodes exist
    for node_id in claim_data["related_nodes"]:
        result = session.run(
            "MATCH (n) WHERE n.id = $id RETURN count(n) AS count",
            id=node_id
        )
        if result.single()["count"] == 0:
            errors.append(f"Node {node_id} does not exist")
    
    # Check claim has at least one artifact
    if not claim_data["anchored_artifacts"]:
        errors.append("Claim has no artifact anchor (violates protocol)")
    
    return errors
```

#### B. Suggested Corrections

```cypher
// When LLM references "Erica France Kirk", suggest canonical form
MATCH (p:Person)
WHERE "Erica France Kirk" IN p.aliases
RETURN p.id, p.canonical_name AS suggested_name
```

---

## 5. Name Spelling Verification (Your Question!)

### The Problem

The current `verify_drafts.py` uses DuckDuckGo to check name spellings:
- "Is it 'Loretta Abbis' or 'Loretta Abis'?"
- "Is it 'Phil Bliss' or 'Philip Bliss'?"

But results aren't stored — you have to re-verify every time.

### How Neo4j Helps

#### A. Persistent Verification Cache

```cypher
// Store verification results
MATCH (p:Person {id: "N-4"})
SET p.verified_spelling = "Loretta Abbis",
    p.verification_source = "DuckDuckGo search + Wikipedia",
    p.verification_date = date(),
    p.alternate_spellings = ["Loretta Abis", "Loretta Abbiss"],
    p.confidence = "High"
```

#### B. Verification Workflow Integration

Modify `verify_drafts.py`:

```python
def verify_name_with_cache(session, node_id: str, name: str) -> dict:
    """Check Neo4j cache before hitting DuckDuckGo."""
    
    # Check cache
    result = session.run(
        "MATCH (p:Person {id: $id}) "
        "RETURN p.verified_spelling AS verified, "
        "       p.verification_date AS date",
        id=node_id
    )
    record = result.single()
    
    if record and record["verified"]:
        age_days = (date.today() - record["date"]).days
        if age_days < 30:  # Cache valid for 30 days
            return {
                "name": record["verified"],
                "source": "cache",
                "confidence": "cached"
            }
    
    # Not cached — search DuckDuckGo
    result = search_duckduckgo(name)
    
    # Store in Neo4j
    session.run(
        "MATCH (p:Person {id: $id}) "
        "SET p.verified_spelling = $verified, "
        "    p.verification_source = $source, "
        "    p.verification_date = date(), "
        "    p.confidence = $confidence",
        id=node_id,
        verified=result["name"],
        source=result["source"],
        confidence=result["confidence"]
    )
    
    return result
```

#### C. Spelling Correction Report

```cypher
// Find names that need verification
MATCH (p:Person)
WHERE p.verified_spelling IS NULL
RETURN p.id, p.canonical_name, p.aliases
ORDER BY p.id
```

---

## 6. Investigative Pressure (Already Working!)

### How Neo4j Helps

Real-time computation from graph edges:

```cypher
MATCH (n:Person)
OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(n)
OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(n)
OPTIONAL MATCH (n)-[:APPEARS_IN]->(e:Episode)
WITH n, 
     count(DISTINCT a) AS artifacts,
     count(DISTINCT c) AS claims,
     count(DISTINCT e) AS episodes
RETURN n.canonical_name, 
       artifacts, 
       claims, 
       episodes,
       (artifacts + claims * 2 + episodes) AS pressure
ORDER BY pressure DESC
```

No manual counting needed — always accurate.

---

## 7. Export & Publishing

### The Problem

After review, you want to:
- Export approved inscriptions
- Generate cross-episode summaries
- Create investigative reports

### How Neo4j Helps

#### A. Markdown Export from Graph

```python
def export_person_dossier(session, person_id: str) -> str:
    """Generate a markdown dossier for a person from Neo4j."""
    
    result = session.run("""
        MATCH (p:Person {id: $id})
        OPTIONAL MATCH (p)-[:APPEARS_IN]->(e:Episode)
        OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(p)
        OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(p)
        RETURN p, 
               collect(DISTINCT e.episode_num) AS episodes,
               collect(DISTINCT {id: c.id, label: c.label, text: c.claim_text}) AS claims,
               collect(DISTINCT {id: a.id, desc: a.description}) AS artifacts
    """, id=person_id)
    
    record = result.single()
    # Generate markdown...
```

#### B. Timeline Visualization

```cypher
// Export timeline data for visualization
MATCH (p:Person {id: "N-2"})-[:APPEARS_IN]->(e:Episode)
MATCH (c:Claim)-[:INVOLVES]->(p)
WHERE c.episode_num = e.episode_num
RETURN e.episode_num AS episode,
       c.claim_ts AS timestamp,
       c.claim_text AS event
ORDER BY e.episode_num, c.claim_ts
```

---

## Implementation Priority

### Phase 1: Already Done ✓
- Ledger management (max IDs)
- Basic integrity validation
- Graph ingestion

### Phase 2: High Impact (Recommend Next)
1. **Name standardization** — biggest pain point across episodes
2. **Verification caching** — avoid re-searching names
3. **Real-time validation** — catch errors during generation

### Phase 3: Advanced Analytics
4. Co-occurrence analysis
5. Contradiction detection
6. Evidence strength scoring

### Phase 4: Publishing
7. Dossier generation
8. Timeline export
9. Report templates

---

## Proposed Enhancements

### 1. Add to `neo4j_ingest.py`

```python
# Name standardization with fuzzy matching
# Verification cache integration
# Alias tracking
```

### 2. Add to `neo4j_validate.py`

```python
# Contradiction detection
# Spelling verification report
# Evidence strength analysis
```

### 3. New: `neo4j_merge.py`

```python
# Interactive tool to merge duplicate nodes
# Suggest canonical names
# Bulk alias updates
```

### 4. New: `neo4j_export.py`

```python
# Export person dossiers
# Generate timeline markdown
# Cross-episode summaries
```

---

## Answer to Your Question

**Yes, Neo4j can absolutely help standardize spellings!**

Specifically:
1. **Cache verification results** — don't re-search the same name
2. **Track aliases** — "Erica Kirk" = "Erica France Kirk"
3. **Fuzzy matching** — detect "Loretta Abbis" vs "Loretta Abis"
4. **Canonical names** — one authoritative spelling per person
5. **Verification metadata** — source, date, confidence level

And beyond spelling:
- **Entity resolution** — merge duplicate nodes
- **Pattern detection** — cross-episode connections
- **Real-time validation** — catch errors during generation
- **Evidence tracking** — verification status, strength scores
- **Publishing** — export dossiers, timelines, reports

Neo4j becomes the **investigative memory** — not just a ledger, but a living knowledge graph that grows smarter with each episode.

---

## Next Steps

Want me to implement:
1. **Name standardization** (aliases + fuzzy matching)?
2. **Verification caching** (integrate with `verify_drafts.py`)?
3. **Real-time validation** (validate during episode generation)?

Or all three?
