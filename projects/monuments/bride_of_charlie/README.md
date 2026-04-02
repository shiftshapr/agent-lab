# Bride of Charlie (Monument Zero)

First monument project. Uses the Episode Analysis Protocol for structured investigative records.

## Structure

- **brief/** — Project briefing (protocol rules)
- **templates/** — Output format for episode analyses
- **input/** — YouTube links (`youtube_links.txt`) or raw transcripts
- **transcripts/** — Raw fetched YouTube transcripts (with timestamps); not modified by name corrections
- **transcripts_corrected/** — Generated copy with `NameCorrection` replacements (input to episode analysis)
- **drafts/** — Episode inscriptions + cross-episode analysis (for review)
- **output/** — Approved inscriptions (after review)
- **protocol_updates/** — Change log with reasons
- **scripts/** — Workflow scripts (fetch, ingest, validate)
- **logs/** — Run logs

See **WORKFLOW.md** for the full process.

## Usage

### Basic workflow

1. Place episode transcripts in `input/`
2. Run from agent-lab root:

```bash
uv run --project framework/deer-flow/backend python agents/protocol/protocol_agent.py --protocol episode_analysis --project bride_of_charlie
```

Or with env var:

```bash
EPISODE_ANALYSIS_PROJECT=bride_of_charlie uv run --project framework/deer-flow/backend python agents/protocol/protocol_agent.py --protocol episode_analysis
```

### Full workflow (recommended)

```bash
cd ~/workspace/agent-lab
python projects/monuments/bride_of_charlie/scripts/run_workflow.py all
```

Steps: `fetch` | `episodes` | `verify` | `cross` | `validate` | `all`

Flags:
- `--force` — Re-run episode analysis even if drafts exist
- `--skip-search` — Skip name spelling verification via DuckDuckGo
- `--validate` — Run Neo4j integrity validation after workflow completes

## Ledger

Artifacts (A-), Claims (C-), and Nodes (N-) use a global cross-episode numbering ledger. Each new episode continues from the highest existing ID. Do not renumber.

## Neo4j Integration (Optional)

The project now supports Neo4j as a graph database for ledger management and integrity validation.

**Benefits:**
- ID collision prevention via uniqueness constraints
- Real-time integrity checks (orphaned claims, dangling references)
- Computed investigative pressure from graph edges
- Visual graph exploration and Cypher queries

**Setup:**

See **NEO4J_SETUP.md** for full instructions.

Quick start:
```bash
cd ~/workspace/agent-lab
docker compose up -d                    # Start Neo4j
uv add neo4j                            # Install driver
python projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py    # Load episodes
python projects/monuments/bride_of_charlie/scripts/neo4j_validate.py  # Validate
```

Open [http://localhost:17474](http://localhost:17474) (login: `neo4j` / `openclaw`). Agent-lab `docker-compose.yml` maps **17474→7474** and **17687→7687** so Bolt does not clash with another local runtime (e.g. OrbStack) on the default ports.

**Configuration:**

Add to `.env`:
```bash
NEO4J_URI=bolt://127.0.0.1:17687
NEO4J_USER=neo4j
NEO4J_PASSWORD=openclaw
NEO4J_AUTO_INGEST=true
```

When `NEO4J_URI` is set, the protocol will query Neo4j for max IDs instead of regex-scanning markdown files.
