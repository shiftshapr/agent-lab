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
- **Fields:** `episode`, `match_mode` (`literal` | `regex`), `find`, `replace`, optional `max_replacements`, `priority`, `tiers` (`inscription`, `transcripts_corrected`, `transcripts`), `flags` (regex only: `IGNORECASE`, `MULTILINE`, `DOTALL`), `note`, optional **`literal_not_followed_by`** (literal only: do not match if `find` is immediately followed by this substring, case-insensitive, max 64 chars per part). **Comma-separated** values mean “skip if followed by **any** of these”. **Ignored** when the next character after `find` is whitespace or punctuation (ASCII `string.punctuation` or Unicode general category P*). Optional **`literal_require_ws_or_punct_after`** (literal only, boolean): only match when the character after `find` is **end of file**, **whitespace**, or **punctuation** (same classification as above). Use this for short literals that should not match as a **prefix** of a longer token (e.g. a truncated name vs the full spelling).

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

**Local audio for Draft Editor Listen (no embed):** place files under `input/audio/episode_NNN.*`, or batch-download from the same links with `scripts/fetch_episode_audio_from_youtube.py` — see **`docs/EPISODE_AUDIO_FROM_VIDEO.md`**.

**One occurrence only (multi-hit Find):** In **Verify vs inscription**, expand occurrences and click **Scope** (violet) on the line you want. That loads the **same** queue row in the editor and sets `match_start_offset` so **Accept & apply** replaces **only that** instance. The verify API still returns **every** inscription hit for that row’s `find` (and `match_count` is the full count); `replacements_if_applied_now` reflects the scoped apply (usually 1). The response includes `scoped_match_start_offset` when set. **Scope does not change `find`**. Edit **Find** manually if you need a longer literal. **Clear scope** removes the offset so Accept applies to all matches again. **Queue this hit** still creates a *separate* proposed row if you prefer a forked edit.

Optional env for a non-default project path: **`BRIDE_PROJECT_ROOT`** (absolute path to `bride_of_charlie`).

## France (country) vs Frantzve (surname)

The word **France** is often correct (**president of France**, **country**, etc.). Other times captions mean **Frantzve** (family surname). The tooling does **not** maintain a per-line whitelist of “this France is OK.”

**What to do**

1. **Fix only the bad spans** — Use **Queue** / **Edit in form** with a **long enough `find`** string so the replacement is unique (e.g. `Erika France was raised` → `Erika Frantzve was raised`, or `1988. France divorced Erika` → `1988. Frantzve divorced Erika`). Avoid a global `France` → `Frantzve` replace.
2. **“Correct” instances** — Leave them alone: **do not** add a queue row for country/contextual France. If the **heuristic scan** shows a hit that is actually correct (e.g. pattern matched but context is geopolitical), **skip** — only queue real fixes.
3. **Wrong proposal already queued** — Select it in the Queue panel and **Mark rejected** (`status: rejected`); it will not apply.
4. **Recurring pattern** — Add a **narrow** regex to **`transcript_suspicious_patterns.json`** (Draft Editor heuristics) or **`editorial_transcript_rules.json`** (pipeline) so you don’t rely on remembering each line. Examples already in heuristics: `Erika France`, `Lorie France`; add more only when the pattern is safe (won’t touch “president of France”).

## Why the LLM sense scan misses some STT errors

The sense scan sends **windows** of de-timestamped text to the model with **`transcript_canonical_glossary.json`** in the system prompt. It will **miss** or **skip** issues when:

- The name **isn’t in the glossary** with STT variants (the prompt tells the model not to “fix” every odd proper noun).
- The corruption still **looks like a plausible name** to the model (“when in doubt…” leans toward not flagging).
- The issue sits on a **window boundary** (reduced by overlap; tune `TRANSCRIPT_SENSE_FLOW_OVERLAP` / chunk size if needed).
- The model returns JSON the parser can’t use (**errRows** in the UI).

**What to do:** Add **canonical + `stt_often`** entries to **`config/transcript_canonical_glossary.json`**, add **narrow heuristics** to **`config/transcript_suspicious_patterns.json`**, and/or queue a **one-off override**. Re-run **Scan** / **LLM sense scan** after glossary changes.

## Prune the queue

When **`proposed`** (or **`rejected`**) rows pile up in `transcript_overrides.json`:

```bash
cd projects/monuments/bride_of_charlie
python3 scripts/apply_transcript_overrides.py --prune-status proposed
python3 scripts/apply_transcript_overrides.py --prune-status proposed --confirm-prune
```

Without **`--confirm-prune`**, the command only lists what would be removed.

## Broad corrections (separate tool)

**`scripts/broad_corrections.py`** can rewrite **`transcripts_corrected_v2/`**. **`apply`** defaults to **dry-run**; use **`apply --write`** or **`all --write`** only after reviewing the preview.

## CLI

```bash
cd projects/monuments/bride_of_charlie
python3 scripts/apply_transcript_overrides.py --dry-run
python3 scripts/apply_transcript_overrides.py --apply
python3 scripts/apply_transcript_overrides.py --apply --episode 6
python3 scripts/apply_transcript_overrides.py --apply --id <override_id>
python3 scripts/apply_transcript_overrides.py --prune-status proposed --confirm-prune
```
