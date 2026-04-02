# Transcript overrides (human queue)

STT + Neo4j name replacement + editorial regex still miss **context** (jokes, quotes, one-off captions). Overrides are the **last** layer before hash sync.

## Order in the pipeline

1. `neo4j_corrections.py apply-dir` → `transcripts_corrected/`
2. `editorial_transcript_pass.py` → `editorial_transcript_rules.json`
3. **`apply_transcript_overrides.py --apply`** → `config/transcript_overrides.json` (**`status`: `accepted` only**)
4. `sync_transcript_hashes.py`

`run_full_workflow.py` runs steps 2–4 via `run_transcript_postprocess_and_sync()` when:

- `BRIDE_EDITORIAL_PASS=1` enables step 2 (and triggers step 4 after any postprocess step ran).
- `BRIDE_TRANSCRIPT_OVERRIDES=1` (default) enables step 3.

Set `BRIDE_TRANSCRIPT_OVERRIDES=0` to skip the override layer.

## Store

- **File:** `config/transcript_overrides.json`
- **Items:** `proposed` | `accepted` | `rejected`
- **Fields:** `episode`, `match_mode` (`literal` | `regex`), `find`, `replace`, optional `max_replacements`, `priority`, `tiers` (`inscription`, `transcripts_corrected`, `transcripts`), `flags` (regex only: `IGNORECASE`, `MULTILINE`, `DOTALL`), `note`.

## Draft Editor UI

Start Draft Editor → **Transcripts** tab:

- **Scan episode** — runs heuristics from `config/transcript_suspicious_patterns.json` on `inscription/episode_NNN_transcript.txt`, lists hits with **hint / suggested fix**, and **YouTube** + **Play here** (embedded player at the caption timestamp before each match).
- **Preview** (on a queue item) — before/after text, **Open YouTube** / **Show & play here** at the match’s last caption stamp, and **Heuristic flags in this excerpt** for that snippet.
- **Heuristic + LLM → queue (Draft Editor):** After **Scan** or **LLM sense scan**, each hit has **Queue** (single) or **Queue all** / **Queue all LLM fixes** (bulk). That creates **`proposed`** rows in `transcript_overrides.json` via `POST /api/bride/transcript-overrides` or **`POST /api/bride/transcript-overrides/propose-from-scan`** `{ "episode": N, "source": "heuristic"|"llm", "items": [ { "find", "replace", "note" } ], "dedupe": true }`. Then use the existing **Queue** panel: **Save edits**, **Preview**, **Accept & apply**, or **Mark rejected**. **Edit in form** copies the hit into the composer without saving.
- **LLM sense check** — batches caption text through your configured model (`MINIMAX_API_KEY` or `OPENAI_BASE_URL` + `OPENAI_API_KEY` + `MODEL_NAME`) and asks for JSON **coherence** issues (garbled STT / nonsense **and** glossary-backed name fixes), **not** “I disagree with the host.” The system prompt includes **`config/transcript_canonical_glossary.json`**. Uses **`scripts/transcript_sense_scan.py`**.
  - **Apply (optional, direct write):** Draft Editor checkbox **Apply safe fixes**, or API `POST /api/bride/transcript-sense-scan` with `{ "episode": N, "apply": true }`. Writes inscription only where each `excerpt` appears **exactly once**; then **`sync_transcript_hashes.py --episode N`**. Prefer **Queue** when you want review before touching files.
  - **CLI:** `python3 scripts/transcript_sense_scan.py 3 --apply-inscription` (add `--dry-run` to preview).
  - **Through Cloudflare (long scans):** Draft Editor runs the scan in a **background job** (HTTP **202** + `job_id`, then poll `GET /api/bride/transcript-sense-scan/job/<job_id>`) so the proxy does not return **524** on full-episode runs. Local-only sync: `POST …/transcript-sense-scan?sync=1` or env `DRAFT_EDITOR_SENSE_SCAN_SYNC=1`.
  - Env **`TRANSCRIPT_SENSE_MAX_BATCHES`**: default **0** = entire episode. **`TRANSCRIPT_SENSE_MAX_EXCERPT_LEN`** (default 2000). **`TRANSCRIPT_SENSE_MAX_TOKENS`** (default 4096), **`TRANSCRIPT_SENSE_TEMPERATURE`** (default 0.05).
- Add **proposed** rows, **Save edits**, **Accept & apply** (writes files + runs `sync_transcript_hashes.py`), **Apply all accepted**.

Video mapping: `input/youtube_links.txt` line order = episode 1…N. Captions must use `[M:SS]` or `[H:MM:SS]` as in the transcript files.

Optional env for a non-default project path: **`BRIDE_PROJECT_ROOT`** (absolute path to `bride_of_charlie`).

## CLI

```bash
cd projects/monuments/bride_of_charlie
python3 scripts/apply_transcript_overrides.py --dry-run
python3 scripts/apply_transcript_overrides.py --apply
python3 scripts/apply_transcript_overrides.py --apply --episode 6
python3 scripts/apply_transcript_overrides.py --apply --id <override_id>
```
