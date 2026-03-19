# Automated high-value workflow — run loop

End-to-end path from transcripts to graph, with iteration until stable.

## Prerequisites

- `~/workspace/agent-lab` with env in `.env` (not committed): `OPENAI_*`, `NEO4J_*`, etc.
- **Submodule:** from agent-lab root:
  ```bash
  git submodule update --init --recursive
  ```
  This populates `framework/deer-flow` (used by `uv run --project framework/deer-flow/backend`).
- Neo4j running (e.g. `docker compose up -d` if you use the repo compose file).

## One-command flow

```bash
cd ~/workspace/agent-lab
./projects/monuments/bride_of_charlie/scripts/run_ideal_workflow.sh
# or
uv run --project framework/deer-flow/backend python \
  projects/monuments/bride_of_charlie/scripts/run_full_workflow.py
```

Set `EPISODE_ANALYSIS_TWO_PHASE=1` in `.env` for Phase 1 JSON → Phase 2 drafts + `inscription/*.json`.

## Downstream graph (Neo4j)

Draft markdown in `drafts/` is parsed by `scripts/neo4j_ingest.py`. It now maps:

| Markdown / JSON field | Neo4j |
|----------------------|--------|
| `Transcript Snippet:` | `transcript_snippet` on Claim / Artifact |
| `Confidence:` / `Uncertainty:` | `confidence`, `uncertainty_note` |
| `Contradicts:` / `Supports:` | `CONTRADICTS` / `SUPPORTS` relationships between Claims |
| `same_as:` in Related line | IDs parsed correctly on artifacts |

`--force` on ingest clears **all nodes except `NameCorrection`** (aligned with `run_full_workflow`).

## Iteration loop (until “completely working”)

1. Run full workflow (or episode analysis only).
2. If Phase 1 validation fails: fix prompt/schema or transcript; check `canonical/edge_cases.jsonl` for `phase1_validation`.
3. Run `assign_ids` / ingest; if Neo4j validate scripts report issues, fix drafts or ingestion.
4. After verify / corrections: re-run workflow second pass until no new corrections.
5. Commit when green: `git status` → commit project + protocol changes.

## Commit policy

- Commit everything **in use** for this pipeline; keep `.env` and secrets gitignored.
- After pulling: `git submodule update --init` if `framework/deer-flow` is missing or outdated.
