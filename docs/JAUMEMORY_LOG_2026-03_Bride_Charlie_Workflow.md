# JAUmemory log — Bride of Charlie workflow upgrades (Mar 2026)

**Tags:** agent-lab, bride-of-charlie, neo4j, workflow, transcripts, episode-analysis, minimax

**Purpose:** Single paste for JAUmemory `remember` tool (after `mcp_login`). Also canonical changelog for Cursor/handoffs.

---

## Did we make all the upgrades?

**In-repo (code + docs): yes — the items below are implemented in `agent-lab` (paths relative to repo root).**  
**You still must set `.env` yourself** (gitignored): e.g. `NEO4J_URI`, `EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS`, MiniMax OpenAI-compat `OPENAI_BASE_URL` + `OPENAI_API_KEY` + `MODEL_NAME`.

---

## 1. Neo4j / Docker

- `docker-compose.yml`: host ports **17474** (browser), **17687** (Bolt) to avoid OrbStack/other hijack of 7474/7687.
- Default scripts/docs: **`bolt://127.0.0.1:17687`** (not 7687).
- `run_full_workflow.py` (and related): load `.env`, **auto-remap** legacy `bolt://localhost|127.0.0.1:7687` → **17687** when needed.

## 2. Transcripts vs corrections (critical)

- **Raw never overwritten:** `projects/monuments/bride_of_charlie/transcripts/` = source of truth.
- **Generated:** `transcripts_corrected/` = raw + `NameCorrection` replacements via `neo4j_corrections.py apply-dir --output-dir`.
- `run_full_workflow.py`: Stage 1.3 + 2.2 rebuild corrected; **`EPISODE_ANALYSIS_INPUT=transcripts_corrected`**.
- `export_for_inscription.py`: default `--transcripts` = **`transcripts_corrected/`**.
- `run_workflow.py`: `corrected` step; `fetch` then build corrected; episodes use corrected input; default **two-phase** env when unset (same as full workflow).

## 3. `neo4j_corrections.py`

- `apply` / `apply-dir`: write to **`transcripts_corrected/`** by default; refuse overwriting raw under `transcripts/` unless `--in-place`.
- **`is_sane_name_correction`**: blocks pathological verify→transcript pairs; **`apply_to_text`** skips insane rows already in DB.
- **`add_correction`** returns bool; import counts safe adds only.
- **`clear-all --yes`**: wipe all `NameCorrection` nodes.
- Cypher fixes (earlier): `ORDER BY size()`, `RETURN ... AS`, `WITH` before `WHERE` after `UNWIND` (KeyError / Neo4j 5).

## 4. `neo4j_validate.py`

- Removed property-based **`broken_artifact_references`** / **`broken_node_references`** (ingest never stored those strings → noise).
- **Exit code 1 only on CRITICAL**; WARNINGs printed but do not fail run.

## 5. `neo4j_ingest.py`

- **`NEO4J_INGEST_STRICT_CLAIMS`** (default **1**): skip placeholder labels, claims with no resolvable Artifact, claims with no resolvable Person/InvestigationTarget; log skips. **0** = legacy permissive.
- Sets **`anchored_artifact_ids`**, **`related_node_ids`** on `Claim` for audit.

## 6. Full workflow defaults

- **`EPISODE_ANALYSIS_TWO_PHASE=1`** when env unset (`run_full_workflow.py`, `run_workflow.py` episodes).
- Multi-pass loop unchanged; **`--max-passes`** default 5.
- **Fetch:** only when **`transcripts/`** has fewer **`episode_*.txt`** than **lines in `input/youtube_links.txt`** (non-comment); **`BRIDE_EXPECTED_EPISODES`** overrides if set. No automatic re-fetch when counts match. **`--skip-fetch`** disables.
- **`BRIDE_STOP_AFTER_GREEN_VALIDATE=1`**: after **`neo4j_validate`** exits 0 (no CRITICAL), **break** multi-pass loop (saves API; may skip extra pass for name-only transcript updates).

## 7. Episode analysis protocol (`protocols/episode_analysis/episode_analysis_protocol.py`)

- **Input files:** only **`episode_*.txt`** and **`episode_*.md`** (ignore `README.md` and loose `*.txt`).
- **`_llm_response_text`**: handles string or list `content` (multimodal).
- **`_strip_think_tags`**: strip `</think>`…`</think>` before JSON parse; Phase 1 uses **`rfind(close)`** + correct tag lengths (fixed prior `+7` bug).
- Phase 1: empty response message; **JSON error preview** (~400 chars).
- Phase 2: exclude `*readme*` from `phase1_jsons` batch list.
- **`_completion_max_tokens()`**: **`EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS`** / **`LLM_MAX_TOKENS`** → `get_llm().max_tokens` (default 8192 if unset).
- **`build_phase1_prompt`**: **compact output** block when **`EPISODE_ANALYSIS_PHASE1_COMPACT=1`** (default on).
- **`get_llm()` docstring:** MiniMax via **`MINIMAX_API_KEY`** *or* OpenAI-compat **`OPENAI_BASE_URL`** to MiniMax + **`OPENAI_API_KEY`** + **`MODEL_NAME`** (no `MINIMAX_API_KEY` required for that path).

## 8. Other scripts

- **`assign_ids.py`:** batch JSON glob excludes `readme` in filename.
- **`cross_episode_analysis.py`:** excludes `*readme*` in `episode_*.md`.
- **`episode_analysis_protocol.py`** (per-episode ingest): `sys.executable`, env copy, longer timeout (from earlier handoff).

## 9. Docs touched

- `projects/monuments/bride_of_charlie/docs/AUTOMATED_WORKFLOW.md` — ports, two-phase default, strict ingest, corrections, Phase 1 tokens/compact, LLM paths.
- `IDEAL_WORKFLOW.md`, `WORKFLOW_GAPS.md`, `README.md` (bride) — transcripts vs corrected.
- Removed **`transcripts_corrected/README.md`** once (it was mistaken for episode 8 when glob was `*.md`); protocol fix prevents recurrence.

## 10. Known operator actions (not automatic)

- **`git restore`** raw transcripts if corrupted before corrections split.
- **`neo4j_corrections clear-all --yes`** after bad dictionary imports.
- Set **`.env`**: `EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS` (e.g. 16384) if Phase 1 JSON **truncates** (MiniMax OpenAI-compat path uses same `max_tokens` as other branch).
- Delete bogus **`episode_008_README*`** artifacts if created before fixes; re-run workflow.

---

## Handoff one-liner

Bride of Charlie: raw **`transcripts/`**, corrected **`transcripts_corrected/`**, Neo4j **17687/17474**, two-phase on by default, strict ingest + critical-only validate fail, sane name corrections + clear-all, episode-only globs + think-tag strip + compact Phase 1 + tunable max output tokens; MiniMax OK via OpenAI-compat URL.

---

*End of log — paste into JAUmemory `remember` or keep as repo doc.*
