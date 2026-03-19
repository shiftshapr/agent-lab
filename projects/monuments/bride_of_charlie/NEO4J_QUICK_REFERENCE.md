# Neo4j Quick Reference — Bride of Charlie

## Setup (One-time)

```bash
cd ~/workspace/agent-lab
docker compose up -d
uv add neo4j
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py
```

Add to `.env`:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
NEO4J_AUTO_INGEST=true
```

---

## Daily Operations

### Start Neo4j
```bash
docker compose up -d
```

### Stop Neo4j
```bash
docker compose down
```

### View logs
```bash
docker compose logs -f neo4j
```

### Ingest episodes (with fuzzy name matching)
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py
```

### Ingest without fuzzy matching
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --no-fuzzy-match
```

### Validate integrity
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py
```

### Verify names (with caching)
```bash
python projects/monuments/bride_of_charlie/scripts/verify_drafts.py
```

### Merge duplicate nodes
```bash
# Interactive mode
python projects/monuments/bride_of_charlie/scripts/neo4j_merge.py

# Auto-merge mode
python projects/monuments/bride_of_charlie/scripts/neo4j_merge.py --auto

# Dry-run (preview only)
python projects/monuments/bride_of_charlie/scripts/neo4j_merge.py --dry-run
```

### Re-ingest (clear + reload)
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force
```

### Run workflow with validation
```bash
python projects/monuments/bride_of_charlie/scripts/run_workflow.py all --validate
```

### Check next available IDs
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_numbering.py next
```

### Validate episode numbering
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_numbering.py validate --episode 3
```

### Generate numbering report
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_numbering.py report --episode 3
```

### Show node reuse statistics
```bash
python projects/monuments/bride_of_charlie/scripts/neo4j_numbering.py reuse
```

---

## Useful Cypher Queries

### Show everything (limited)
```cypher
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100
```

### Count all nodes by type
```cypher
MATCH (n)
RETURN labels(n)[0] AS type, count(n) AS count
ORDER BY count DESC
```

### Find claims about a person
```cypher
MATCH (c:Claim)-[:INVOLVES]->(p:Person {name: "Erica Kirk"})
RETURN c.id, c.label, c.claim_text
```

### Show artifacts for an episode
```cypher
MATCH (e:Episode {episode_num: 1})-[:CONTAINS_FAMILY]->(af:ArtifactFamily)-[:HAS_ARTIFACT]->(a:Artifact)
RETURN af.id, af.name, a.id, a.description
ORDER BY a.id
```

### Find orphaned claims (no artifact anchor)
```cypher
MATCH (c:Claim)
WHERE NOT (:Artifact)-[:ANCHORS]->(c)
RETURN c.id, c.label, c.episode_num
```

### Investigative pressure (top 10)
```cypher
MATCH (n)
WHERE n:Person OR n:InvestigationTarget
OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(n)
OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(n)
OPTIONAL MATCH (n)-[:APPEARS_IN]->(e:Episode)
WITH n, 
     count(DISTINCT a) AS artifacts,
     count(DISTINCT c) AS claims,
     count(DISTINCT e) AS episodes
RETURN n.id, n.name, artifacts, claims, episodes,
       (artifacts + claims * 2 + episodes) AS pressure
ORDER BY pressure DESC
LIMIT 10
```

### Show claim with all anchors and nodes
```cypher
MATCH (c:Claim {id: "C-1009"})
OPTIONAL MATCH (a:Artifact)-[:ANCHORS]->(c)
OPTIONAL MATCH (c)-[:INVOLVES]->(n)
RETURN c, a, n
```

### Find nodes appearing in multiple episodes
```cypher
MATCH (n)-[:APPEARS_IN]->(e:Episode)
WHERE n:Person OR n:InvestigationTarget
WITH n, count(DISTINCT e) AS episode_count
WHERE episode_count > 1
RETURN n.id, n.name, episode_count
ORDER BY episode_count DESC
```

### Show artifact families by episode
```cypher
MATCH (e:Episode)-[:CONTAINS_FAMILY]->(af:ArtifactFamily)
RETURN e.episode_num, collect(af.id) AS families
ORDER BY e.episode_num
```

---

## Troubleshooting

### "Could not connect to Neo4j"
```bash
docker compose up -d
docker compose logs -f neo4j  # Wait for "Started."
```

### "neo4j driver not installed"
```bash
uv add neo4j
```

### Reset everything
```bash
docker compose down -v
docker compose up -d
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --force
```

### Check if Neo4j is running
```bash
docker ps | grep neo4j
```

### View Neo4j Browser
Open [http://localhost:7474](http://localhost:7474)
Login: `neo4j` / `openclaw`

---

## File Locations

- **Docker config:** `workspace/agent-lab/docker-compose.yml`
- **Ingest script:** `projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py`
- **Validate script:** `projects/monuments/bride_of_charlie/scripts/neo4j_validate.py`
- **Setup guide:** `projects/monuments/bride_of_charlie/NEO4J_SETUP.md`
- **Integration summary:** `projects/monuments/bride_of_charlie/NEO4J_INTEGRATION_SUMMARY.md`

---

## Environment Variables

```bash
NEO4J_URI=bolt://localhost:7687          # Required to enable Neo4j
NEO4J_USER=neo4j                         # Default: neo4j
NEO4J_PASSWORD=openclaw                  # Default: openclaw
NEO4J_AUTO_INGEST=true                   # Auto-ingest after episode analysis
```

---

## Workflow Integration

### Without Neo4j (regex scanning)
```bash
python scripts/run_workflow.py all
```

### With Neo4j (validation only)
```bash
python scripts/run_workflow.py all --validate
```

### With Neo4j (source of truth)
Set `NEO4J_URI` in `.env`, then:
```bash
python scripts/run_workflow.py all --validate
```

---

## Next Steps

1. Start Docker
2. Run `docker compose up -d`
3. Run `uv add neo4j`
4. Run `python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py`
5. Open [http://localhost:7474](http://localhost:7474)
6. Add Neo4j config to `.env`
