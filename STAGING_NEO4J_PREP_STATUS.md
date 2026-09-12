# Bride of Charlie staging Neo4j — Mac Mini prep status

**Date:** 2026-09-12 (updated)  
**Machine:** Shiftshaprs-Mac-mini.local  
**Target tip:** `ddb72a04dbc57ce9a5a1761fc85992e96e40613a` (`ddb72a0`)

**Platform doc:** [docs/NEO4J_PLATFORM.md](docs/NEO4J_PLATFORM.md) — prod/staging split, per-project databases (`meta`, `boc`, `dia`, `pacha`).

## Ready

| Item | Status |
|------|--------|
| Live checkout | `/Users/shiftshapr/agent-lab` @ `ddb72a0` (PR19 merge) |
| Orphan preserved | `/Users/shiftshapr/workspace` (no `.git`, not used) |
| Docker | Docker Desktop; compose plugin via `~/.local/bin` |
| Tip drafts | 8 × `projects/monuments/bride_of_charlie/drafts/episode_00N.md` |
| `uv` + `neo4j` driver | uv 0.12.12; `neo4j==6.1.0` via `uv sync` |
| Compose | `agent-lab-neo4j-prod` (17474/17687) + `agent-lab-neo4j-staging` (27474/27687) |

## Recommended `.env`

```bash
NEO4J_URI_PROD=bolt://127.0.0.1:17687
NEO4J_URI_STAGING=bolt://127.0.0.1:27687
NEO4J_URI=bolt://127.0.0.1:27687
NEO4J_DATABASE_BOC=boc
NEO4J_AUTO_INGEST=false
```

## Start stack + init databases

```bash
cd ~/agent-lab
docker compose up -d
python scripts/neo4j_init_databases.py --all-instances
docker exec agent-lab-neo4j-staging cypher-shell -u neo4j -p openclaw 'RETURN 1'
```

## Staging ingest (not inscription)

```bash
cd ~/agent-lab/projects/monuments/bride_of_charlie
set -a && source /Users/shiftshapr/agent-lab/.env && set +a
export NEO4J_URI="${NEO4J_URI_STAGING:-bolt://127.0.0.1:27687}"
export NEO4J_DATABASE=boc

uv run --project /Users/shiftshapr/agent-lab python scripts/neo4j_ingest.py --force
uv run --project /Users/shiftshapr/agent-lab python scripts/verify_drafts.py
uv run --project /Users/shiftshapr/agent-lab python scripts/neo4j_merge.py --auto
uv run --project /Users/shiftshapr/agent-lab python scripts/neo4j_validate.py
uv run --project /Users/shiftshapr/agent-lab python scripts/neo4j_patterns.py all --output drafts/patterns_report.md
uv run --project /Users/shiftshapr/agent-lab python scripts/neo4j_quality.py --output drafts/quality_report.md
```

`--force` clears **only the `boc` database** on the target instance.

Inscription remains **held** until Daveed explicitly says go.

## Legacy `openclaw-neo4j`

If the old single container is still running, stop it before `docker compose up -d`. See migration steps in [docs/NEO4J_PLATFORM.md](docs/NEO4J_PLATFORM.md).
