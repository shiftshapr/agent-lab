# Neo4j platform (agent-lab)

Multi-project graph storage on the Mac Mini with **production** and **staging** instances. Container names use the `agent-lab-neo4j-*` prefix (no `openclaw-`).

## Instances

| Instance | Container | Browser | Bolt | Use |
|----------|-----------|---------|------|-----|
| **Production** | `agent-lab-neo4j-prod` | http://localhost:17474 | `bolt://127.0.0.1:17687` | Transit / Bill D queries; promote-only ingest |
| **Staging** | `agent-lab-neo4j-staging` | http://localhost:27474 | `bolt://127.0.0.1:27687` | `--force` ingest, experiments, validation |

Credentials: `neo4j` / `openclaw` (from compose and `.env`).

Remote browser (HTTP tunnel): https://neo4j.metawebbook.com — Bolt still requires SSH port-forward:

```bash
ssh -L 17687:127.0.0.1:17687 shiftshapr@Shiftshaprs-Mac-mini.local   # prod
ssh -L 27687:127.0.0.1:27687 shiftshapr@Shiftshaprs-Mac-mini.local   # staging
```

## Project databases

**Community Edition (current compose image):** one shared Bolt database named `neo4j`. Projects are isolated by **node labels**, not separate databases:

| Logical DB | Project | Labels (examples) |
|------------|---------|-------------------|
| `meta` | Meta-layer / Logseq / knowledge | `MLSource`, `MLChunk`, `MLConcept` |
| `boc` | Bride of Charlie | `Episode`, `Claim`, `Person`, `Artifact` |
| `dia` | DIA inbox (planned) | `DIAInbox`, … |
| `pacha` | Pacha (planned) | `P*`, … |

**Enterprise:** `neo4j_init_databases.py` can create real `meta` / `boc` / `dia` / `pacha` databases. Scripts auto-detect which mode is available.

After first `docker compose up`:

```bash
cd ~/agent-lab
python scripts/neo4j_init_databases.py --all-instances
```

Scripts use logical names via `NEO4J_DATABASE` or `NEO4J_DATABASE_BOC` / `_META` / etc. Shared helper: `scripts/neo4j_platform.py`.

## Environment variables

```bash
# Production (Transit / promoted graph)
NEO4J_URI_PROD=bolt://127.0.0.1:17687

# Staging (local dev and --force)
NEO4J_URI_STAGING=bolt://127.0.0.1:27687

# Active URI for scripts (default: prod if unset)
NEO4J_URI=bolt://127.0.0.1:27687

NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw

# Per-project database names
NEO4J_DATABASE_BOC=boc
NEO4J_DATABASE_META=meta
NEO4J_DATABASE_DIA=dia
NEO4J_DATABASE_PACHA=pacha

# Optional override for any script
# NEO4J_DATABASE=boc
```

**Recommendation:** Point `NEO4J_URI` at **staging** during ingest/validation; switch to **prod** only when promoting a validated graph.

## Docker compose

```bash
cd ~/agent-lab
docker compose up -d
docker compose ps
python scripts/neo4j_init_databases.py --all-instances
```

Health check:

```bash
docker exec agent-lab-neo4j-prod cypher-shell -u neo4j -p openclaw 'RETURN 1'
docker exec agent-lab-neo4j-staging cypher-shell -u neo4j -p openclaw 'RETURN 1'
```

## Bride of Charlie workflow

**Staging** (safe to wipe BOC data):

```bash
cd ~/agent-lab/projects/monuments/bride_of_charlie
set -a && source /Users/shiftshapr/agent-lab/.env && set +a
export NEO4J_URI="${NEO4J_URI_STAGING:-bolt://127.0.0.1:27687}"
export NEO4J_DATABASE=boc

uv run --project /Users/shiftshapr/agent-lab python scripts/neo4j_ingest.py --force
uv run --project /Users/shiftshapr/agent-lab python scripts/verify_drafts.py
uv run --project /Users/shiftshapr/agent-lab python scripts/neo4j_merge.py --auto
uv run --project /Users/shiftshapr/agent-lab python scripts/neo4j_validate.py
```

`--force` clears **only BOC-labeled nodes** (preserves `NameCorrection` nodes). On Community Edition it does not touch `ML*` meta-layer nodes. On Enterprise with a dedicated `boc` database, it wipes that database only.

**Production promote** (after inscription sign-off): export from staging or re-ingest against prod URI without `--force` unless intentionally replacing prod.

## Meta-layer / Logseq

```bash
export NEO4J_URI="${NEO4J_URI_STAGING:-bolt://127.0.0.1:27687}"
export NEO4J_DATABASE=meta
python scripts/ingest-meta-layer-knowledge.py
python scripts/ingest-logseq-notes.py
```

## Migration from legacy `openclaw-neo4j`

The old single-service compose used container `openclaw-neo4j` and volume `agent-lab_neo4j_data` with data in the default `neo4j` database.

1. Stop the old container: `docker stop openclaw-neo4j && docker rm openclaw-neo4j`
2. Start new stack: `docker compose up -d`
3. **Option A — re-ingest (recommended):** Run BOC staging ingest into `boc` on staging (see above).
4. **Option B — copy volume to staging:**
   ```bash
   docker compose stop neo4j-staging
   docker run --rm \
     -v agent-lab_neo4j_data:/from \
     -v agent-lab_neo4j_data_staging:/to \
     alpine sh -c 'cp -a /from/. /to/.'
   docker compose start neo4j-staging
   python scripts/neo4j_init_databases.py --uri bolt://127.0.0.1:27687
   ```
   Legacy graph remains in the `neo4j` database until you migrate or re-ingest into `boc`.

Production starts with an **empty** volume until you promote.

## Handoff (Bill D / Transit)

- **Production Bolt:** `bolt://127.0.0.1:17687` on the Mac Mini (or SSH tunnel above).
- **Database:** `boc` — set `NEO4J_DATABASE=boc` in client config.
- **Do not** run `--force` against production.
- Staging is for validation; prod receives promoted graphs only.
