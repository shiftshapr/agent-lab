# Neo4j handoff — Bill D & Transit

**Updated:** 2026-09-12  
**Host:** `Shiftshaprs-Mac-mini.local` (Daveed’s Mac Mini)  
**Graph:** Bride of Charlie investigative graph (BOC)

This briefing covers how to connect to **production** Neo4j after the platform upgrade. Internal reference: [NEO4J_PLATFORM.md](./NEO4J_PLATFORM.md).

---

## What changed

| Before | Now |
|--------|-----|
| Single container `openclaw-neo4j` | **Production:** `agent-lab-neo4j-prod` |
| One port pair (17474 / 17687) | **Staging:** `agent-lab-neo4j-staging` (27474 / 27687) — internal only |
| Full-graph `--force` wipes | BOC `--force` clears **BOC labels only** (Community Edition) |

**You should use production only.** Staging is for ingest experiments and validation before promote.

---

## Current data status (2026-09-12)

| Instance | Bolt port | Graph nodes | Notes |
|----------|-----------|-------------|--------|
| **Production** | `17687` | **0** | Empty until Daveed promotes a validated graph |
| Staging | `27687` | ~465 (8 episodes) | Has the migrated BOC graph; not your target URI |

When production is populated, this doc’s connection details stay the same — only the data appears.

---

## Production connection (your target)

| Setting | Value |
|---------|--------|
| **Bolt URI** | `bolt://127.0.0.1:17687` |
| **Browser** (on Mac Mini) | http://localhost:17474 |
| **Browser** (remote, if tunnel configured) | https://neo4j.metawebbook.com |
| **Username** | `neo4j` |
| **Password** | `openclaw` |
| **Edition** | Neo4j 5.18 **Community** |
| **Database name** | `neo4j` (single shared DB; BOC data uses node **labels**) |

There is no separate `boc` database on Community Edition. Query BOC nodes by label: `Episode`, `Claim`, `Person`, `Artifact`, `Organization`, `Topic`, `Place`, etc.

---

## Remote access (recommended)

Bolt does **not** go through the HTTP browser tunnel alone. Use SSH port-forwarding:

```bash
ssh -L 17687:127.0.0.1:17687 shiftshapr@Shiftshaprs-Mac-mini.local
```

Keep that session open. From your machine, `127.0.0.1:17687` forwards to production on the Mini.

Optional — browser UI while tunneled:

```bash
ssh -L 17474:127.0.0.1:17474 shiftshapr@Shiftshaprs-Mac-mini.local
```

Then open http://localhost:17474 and log in with `neo4j` / `openclaw`.

---

## cypher-shell

**From your laptop** (after SSH tunnel above):

```bash
cypher-shell -a bolt://127.0.0.1:17687 -u neo4j -p openclaw "RETURN 1"
```

Or:

```bash
export NEO4J_URI=bolt://127.0.0.1:17687
cypher-shell -u neo4j -p openclaw "RETURN 1"
```

**If you SSH into the Mac Mini**, either form above works, or:

```bash
docker exec agent-lab-neo4j-prod cypher-shell -u neo4j -p openclaw "RETURN 1"
```

(`docker exec` uses the container’s internal port — no `17687` needed.)

---

## Application / driver config

Use these in Transit, scripts, or any Neo4j driver:

```bash
NEO4J_URI=bolt://127.0.0.1:17687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
# Logical name for BOC tooling; on Community this still uses the `neo4j` database
NEO4J_DATABASE=boc
```

**Python example:**

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://127.0.0.1:17687",
    auth=("neo4j", "openclaw"),
)
with driver.session(database="neo4j") as session:
    result = session.run("MATCH (e:Episode) RETURN e.episode_num ORDER BY e.episode_num")
    print([r["e.episode_num"] for r in result])
driver.close()
```

**Do not use:**

| Wrong | Why |
|-------|-----|
| `bolt://127.0.0.1:27687` | Staging |
| `bolt://127.0.0.1:7687` | Default port; not mapped on this host |
| `openclaw-neo4j` container name | Retired |

---

## Starter queries (BOC graph)

Once production has data:

```cypher
// Episodes
MATCH (e:Episode) RETURN e.episode_num, e.filename ORDER BY e.episode_num;

// People
MATCH (p:Person) RETURN p.id, p.canonical_name ORDER BY p.id LIMIT 25;

// Claims for an episode
MATCH (c:Claim {episode_num: 1}) RETURN c.id, c.label LIMIT 20;

// Person ↔ artifacts / claims
MATCH (p:Person {id: 'N-1'})
OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(p)
OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(p)
RETURN p.canonical_name, count(DISTINCT a) AS artifacts, count(DISTINCT c) AS claims;

// Graph size
MATCH (n) WHERE n:Episode OR n:Claim OR n:Person OR n:Artifact
RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;
```

---

## Rules of the road

1. **Production is read/query for you** — do not run ingest with `--force` or bulk delete against prod.
2. **Staging (`27687`)** is for Daveed’s team only — validation and re-ingest.
3. **Promote workflow:** validated graph on staging → copy or re-ingest to prod when Daveed signs off (inscription still held separately).
4. **Community Edition:** meta-layer notes (`ML*` labels) may live in the same `neo4j` database; BOC queries should filter by BOC labels (as above).

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Connection refused on `17687` | SSH tunnel running? `docker compose ps` on Mini shows `agent-lab-neo4j-prod` up? |
| Auth failed | User `neo4j`, password `openclaw` |
| Empty graph | Prod may not be promoted yet; confirm with Daveed |
| Wrong data / experimental | Accidentally on staging (`27687`) — switch to `17687` |

**On the Mini (Daveed or console access):**

```bash
cd ~/agent-lab
docker compose ps
docker exec agent-lab-neo4j-prod cypher-shell -u neo4j -p openclaw "MATCH (n) RETURN count(n)"
```

---

## Contacts / docs

- Platform overview: [NEO4J_PLATFORM.md](./NEO4J_PLATFORM.md)
- BOC project scripts: `~/agent-lab/projects/monuments/bride_of_charlie/scripts/`
- Questions on promote timing or inscription: Daveed
