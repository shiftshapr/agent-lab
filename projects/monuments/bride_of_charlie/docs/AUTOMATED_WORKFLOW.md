# Automated high-value workflow — run loop

End-to-end path from transcripts to graph, with iteration until stable.

**Transcripts:** `transcripts/` is **raw only** (e.g. from YouTube). Name corrections write **`transcripts_corrected/`**; episode analysis reads the corrected dir. Raw files are never overwritten by `neo4j_corrections`.

**Launch & comms (internal):** rollout order (inscribe → gov hub → Substack → video) and a **conversation → build log** live in [`LAUNCH_AND_COMMS_STRATEGY.md`](./LAUNCH_AND_COMMS_STRATEGY.md).

## Prerequisites

- `~/workspace/agent-lab` with env in `.env` (not committed): `OPENAI_*`, `NEO4J_*`, etc.
- **LLM:** Episode analysis uses LangChain `ChatOpenAI`. You can use **MiniMax** either by setting `MINIMAX_API_KEY` (dedicated branch) **or** by using the **OpenAI-compatible** variables only: `OPENAI_BASE_URL=https://api.minimax.io/v1`, `OPENAI_API_KEY=<minimax key>`, `MODEL_NAME=<MiniMax model id>`. Output token cap: `EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS` / `LLM_MAX_TOKENS` (same for both paths).
- **Submodule:** from agent-lab root:
  ```bash
  git submodule update --init --recursive
  ```
  This populates `framework/deer-flow` (used by `uv run --project framework/deer-flow/backend`).
- Neo4j running (e.g. `docker compose up -d` from agent-lab root). The compose file publishes **Bolt on host `17687`** and **Browser on `17474`** (not 7687/7474) to avoid port clashes with tools like OrbStack — set `NEO4J_URI=bolt://127.0.0.1:17687` in `.env`.

## One-command flow

```bash
cd ~/workspace/agent-lab
./projects/monuments/bride_of_charlie/scripts/run_ideal_workflow.sh
# or
uv run --project framework/deer-flow/backend python \
  projects/monuments/bride_of_charlie/scripts/run_full_workflow.py
```

**Telegram (Shiftshapr):** Send `/bride https://www.youtube.com/watch?v=…` from your allowed chat, or one line like “Process new Bride of Charlie episode” + the same YouTube URL. The bot appends the URL to `input/youtube_links.txt` and, by default, runs `scripts/run_full_workflow.py` on the machine where the webhook runs (`BRIDE_TG_RUN_WORKFLOW=0` to append only). Logs: `logs/bride_workflow_*.log` at agent-lab root.

**Transcript fetch:** The full workflow **does not** re-download when you already have enough local files. Stage 2 runs `fetch` **only** if `transcripts/` has **fewer** `episode_*.txt` files than **non-comment lines in `input/youtube_links.txt`** (same list `fetch_transcripts.py` uses). So when a new episode drops: **append its URL to `youtube_links.txt`**, re-run the full workflow — fetch runs automatically for the missing file(s). Optional override: set **`BRIDE_EXPECTED_EPISODES`** in `.env` if you must pin a number without editing the links file. Use `--skip-fetch` to never call the API. For a forced refresh of everything, run `run_workflow.py fetch` manually (or delete specific `episode_*.txt` files and re-run).

**Stop burning passes when the graph is CRITICAL-clean:** set `BRIDE_STOP_AFTER_GREEN_VALIDATE=1` in `.env` to exit the multi-pass loop after `neo4j_validate` returns 0, even if name-correction replacements were applied (tradeoff: may skip one more episode regen for transcript-only name tweaks).

`run_full_workflow.py` **defaults** `EPISODE_ANALYSIS_TWO_PHASE=1` (Phase 1 JSON → Phase 2 drafts + `inscription/*.json`). Set `EPISODE_ANALYSIS_TWO_PHASE=0` in `.env` to force single-pass.

**Phase 2 full renumber (`assign_ids.py --fresh-ledger`):** Resets A-/C-/N- counters and, by default, **deletes** legacy markdown `drafts/episode_NNN_episode_NNN_<youtubeId>.md` (old filename scheme; wrong ID space vs `episode_NNN.md`). That avoids `neo4j_ingest.py` ingesting two conflicting drafts per episode. Opt out with **`--keep-legacy-draft-md`** (not recommended). After a fresh ledger, **re-run `neo4j_ingest.py --force`** if you use Neo4j so the graph matches the new IDs.

**Extraction protocol (programs / institutions):** The Bride brief and **`templates/bride_charlie_entity_extraction.md`** require **InvestigationTarget** nodes for **named government programs** and similar institutions **on first substantive mention** (e.g. **MK Ultra**, **CIA Project Looking Glass**), not only when they recur. Memes complement nodes; they do not replace them. See **`docs/EDITORIAL_PASS.md`** for the **find → fix** workflow (heuristic scan, LLM sense scan, glossary, editorial rules, Phase 1 re-run).

**Inscription export (Stage 5b / `export_for_inscription.py`):** Writes canonical **`episode_NNN.json`** + **`episode_NNN_transcript.txt`** for each episode, updates **`manifest.json`** (only those pairs — no duplicate long filenames). By default **removes** redundant `episode_NNN_youtubeId.json` copies from `inscription/` after copying into the canonical name; use **`--no-prune`** to keep both.

### Re-run one episode (e.g. Phase 1 JSON parse failed for ep 5)

Episode index **5** = fifth file when `transcripts_corrected/episode_*.txt` are sorted (same as `episode_005_*` for Bride).

- **`--force --only 5`** deletes **only** that episode’s `drafts/episode_005_*.md` and `phase1_output/episode_005_*.json`, re-runs Phase 1 for it, then runs **Phase 2 (`assign_ids`) for all** JSON files in `phase1_output/`.

```bash
cd ~/workspace/agent-lab
export EPISODE_ANALYSIS_PROJECT=bride_of_charlie
export EPISODE_ANALYSIS_INPUT=transcripts_corrected
export EPISODE_ANALYSIS_OUTPUT=drafts
export EPISODE_ANALYSIS_TWO_PHASE=1
uv run --project framework/deer-flow/backend python agents/protocol/protocol_agent.py \
  --protocol episode_analysis --project bride_of_charlie --force --only 5
```

Equivalent env without CLI: `EPISODE_ANALYSIS_ONLY=5` plus `EPISODE_ANALYSIS_FORCE=1`. Multiple episodes: `--only 3,6`.

## Downstream graph (Neo4j)

Draft markdown in `drafts/` is parsed by `scripts/neo4j_ingest.py`. It now maps:

| Markdown / JSON field | Neo4j |
|----------------------|--------|
| `Transcript Snippet:` | `transcript_snippet` on Claim / Artifact |
| `Confidence:` / `Uncertainty:` | `confidence`, `uncertainty_note` |
| `Contradicts:` / `Supports:` | `CONTRADICTS` / `SUPPORTS` relationships between Claims |
| `same_as:` in Related line | IDs parsed correctly on artifacts |

`--force` on ingest clears **all nodes except `NameCorrection`** (aligned with `run_full_workflow`).

**Ingest:** With `NEO4J_INGEST_STRICT_CLAIMS=1` (default), placeholder / unanchored / nodeless claims are **skipped** (logged) so `neo4j_validate` can pass on CRITICAL checks. Set `NEO4J_INGEST_STRICT_CLAIMS=0` to restore permissive ingest.

**Name corrections:** Unsafe pairs are rejected on `add` / `import-from-verify`; `apply` skips insane rows already in the DB. Clear bad dictionary: `neo4j_corrections.py clear-all --yes`.

**Phase 1 JSON cut off mid-stream (`Unterminated string` / parse errors):** That is usually the **completion (output) token limit**, not input context. In `.env` try `EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS=16384` (or your provider’s max). Phase 1 also uses **compact output instructions** by default (`EPISODE_ANALYSIS_PHASE1_COMPACT=1`); set to `0` if you want the model to be more verbose (may truncate more often).

## Iteration loop (until “completely working”)

1. Run full workflow (or episode analysis only).
2. If Phase 1 validation fails: fix prompt/schema or transcript; check `canonical/edge_cases.jsonl` for `phase1_validation`.
3. Run `assign_ids` / ingest; if Neo4j validate scripts report issues, fix drafts or ingestion.
4. After verify / corrections: re-run workflow second pass until no new corrections.
5. Commit when green: `git status` → commit project + protocol changes.

## Commit policy

- Commit everything **in use** for this pipeline; keep `.env` and secrets gitignored.
- After pulling: `git submodule update --init` if `framework/deer-flow` is missing or outdated.
