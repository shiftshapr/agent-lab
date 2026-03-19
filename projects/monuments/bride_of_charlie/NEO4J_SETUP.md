# Neo4j Setup Guide — Bride of Charlie

This guide walks you through setting up Neo4j for the Bride of Charlie investigative graph.

---

## Why Neo4j?

The OpenClaw protocol already describes "a reversible investigative graph" — Neo4j makes it native. It prevents:

- **ID collisions** — uniqueness constraints replace fragile regex scanning
- **Orphaned claims** — find Claims with no Artifact anchor in one query
- **Dangling references** — ingesting `Related: A-9999` when A-9999 doesn't exist raises immediately
- **Manual pressure tracking** — Investigative Pressure computed from real edges, not manually maintained counters
- **Missing bidirectional links** — verify `C-1009 → N-2` has matching `N-2 → C-1009`

---

## Prerequisites

You need Docker to run Neo4j. Choose one:

### Option 1: Docker Desktop (Recommended)
Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)

### Option 2: Colima (Lightweight alternative)
```bash
brew install colima docker
colima start
```

### Option 3: OrbStack (Mac only, fastest)
Download from [orbstack.dev](https://orbstack.dev)

---

## Setup Steps

### 1. Start Neo4j

```bash
cd ~/workspace/agent-lab
docker compose up -d
```

Wait 10-15 seconds for Neo4j to fully start. Check logs:

```bash
docker compose logs -f neo4j
```

Look for: `Started.` (means Neo4j is ready)

### 2. Install Python driver

```bash
cd ~/workspace/agent-lab
uv add neo4j
```

### 3. Configure environment

Add to your `.env` file:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
NEO4J_AUTO_INGEST=true
```

### 4. Ingest existing episodes

```bash
cd ~/workspace/agent-lab
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py
```

Expected output:
```
[neo4j-ingest] Connecting to bolt://localhost:7687...
[neo4j-ingest] Ingesting 7 episode(s)...
  [1/7] episode_001_episode_001_ZAsV0fHGBiM.md
       OK (Episode 1)
  [2/7] episode_002_episode_002_1IY2oD-_xVA.md
       OK (Episode 2)
  ...
[neo4j-ingest] Done. View graph at http://localhost:7474
[neo4j-ingest] Login: neo4j / openclaw
```

### 5. Validate integrity

```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py
```

Expected output:
```
================================================================================
OPENCLAW PROTOCOL INTEGRITY VALIDATION
================================================================================

--- GRAPH STATISTICS ---

  Total Episodes: 7
  Total Artifact Families: 45
  Total Artifacts: 123
  Total Claims: 87
  Total People: 12
  Total Investigation Targets: 8

--- INTEGRITY CHECKS ---

  [PASS] Claims with no artifact anchor (violates Artifact Anchor Test)
  [PASS] Artifacts with no related claims or nodes (violates Cross-Reference Rule)
  [PASS] Nodes with zero evidence (no artifacts or claims reference them)
  [PASS] Claims with no related nodes (violates protocol requirement)

================================================================================
RESULT: ALL CHECKS PASSED ✓
================================================================================
```

---

## Usage

### View the graph

Open [http://localhost:7474](http://localhost:7474) in your browser.

Login: `neo4j` / `openclaw`

Try these Cypher queries:

**Show all nodes and relationships:**
```cypher
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100
```

**Find claims about Erica Kirk:**
```cypher
MATCH (c:Claim)-[:INVOLVES]->(n:Person {name: "Erica Kirk"})
RETURN c.id, c.label, c.claim_text
```

**Show investigative pressure (top 5 nodes):**
```cypher
MATCH (n)
WHERE n:Person OR n:InvestigationTarget
OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(n)
OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(n)
WITH n, count(DISTINCT a) AS artifacts, count(DISTINCT c) AS claims
RETURN n.id, n.name, artifacts, claims, (artifacts + claims * 2) AS pressure
ORDER BY pressure DESC
LIMIT 5
```

**Find artifacts with no claims (potential orphans):**
```cypher
MATCH (a:Artifact)
WHERE NOT (a)-[:ANCHORS]->()
RETURN a.id, a.description
```

### Run validation after changes

```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py
```

### Re-ingest after editing drafts

```bash
# Clear graph and re-ingest
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force
```

### Use Neo4j in the pipeline

When `NEO4J_URI` is set in `.env`, the episode analysis protocol will:
1. Query Neo4j for max IDs instead of regex-scanning markdown files
2. Auto-ingest new episodes to Neo4j after analysis (if `NEO4J_AUTO_INGEST=true`)

Run workflow with validation:
```bash
python projects/monuments/bride_of_charlie/scripts/run_workflow.py all --validate
```

---

## Troubleshooting

### "Could not connect to Neo4j"

Check if Neo4j is running:
```bash
docker ps | grep neo4j
```

If not running:
```bash
docker compose up -d
```

### "neo4j driver not installed"

```bash
cd ~/workspace/agent-lab
uv add neo4j
```

### Reset everything

```bash
docker compose down -v  # Remove container and volumes
docker compose up -d    # Start fresh
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force
```

### View logs

```bash
docker compose logs -f neo4j
```

---

## Architecture

```
Episode Transcript
       ↓
  Analysis Agent (LLM)
       ↓
  Query Neo4j for max IDs → next A-/C-/N- IDs
       ↓
  Draft Markdown
       ↓
  neo4j_ingest.py → Parse markdown → MERGE nodes + relationships
       ↓
  neo4j_validate.py → Run integrity checks
       ↓
  output/ (approved inscriptions)
```

---

## Graph Schema

**Nodes:**
- `Episode` — episode metadata
- `ArtifactFamily` — top-level artifact bundle (A-1000)
- `Artifact` — individual artifact (A-1000.1)
- `Claim` — falsifiable assertion (C-1009)
- `Person` — person node (N-2)
- `InvestigationTarget` — investigation target (N-1000)

**Relationships:**
- `Episode -[:CONTAINS_FAMILY]-> ArtifactFamily`
- `ArtifactFamily -[:HAS_ARTIFACT]-> Artifact`
- `Artifact -[:ANCHORS]-> Claim`
- `Artifact -[:INVOLVES]-> Person|InvestigationTarget`
- `Claim -[:INVOLVES]-> Person|InvestigationTarget`
- `Claim -[:FROM_EPISODE]-> Episode`
- `Person|InvestigationTarget -[:APPEARS_IN]-> Episode`

---

## Next Steps

1. Start Docker
2. Run `docker compose up -d`
3. Run `uv add neo4j`
4. Run `python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py`
5. Run `python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py`
6. Open [http://localhost:7474](http://localhost:7474)
7. Add Neo4j config to `.env`

For questions or issues, see the main project README or workflow documentation.
