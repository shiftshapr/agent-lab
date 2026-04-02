# Editorial pass (scholarly transcripts + metadata)

After STT / captions, apply a **final editorial pass** before Phase 1 or when refreshing reference transcripts beside inscription JSON.

**Full stack (see also [TRANSCRIPT_OVERRIDES.md](./TRANSCRIPT_OVERRIDES.md)):**  
`neo4j apply-dir` → **editorial regex** → **accepted transcript overrides** → `sync_transcript_hashes`.

**Do not hand-fix recurring STT errors in transcripts** (e.g. `Kent wasn`, `Bronzeface`, `Lorie France` → `Lori Frantzve`, `Kenton Lorie France` → `Kent and Lori Frantzve`, split `morfar` across caption lines). Add or adjust a rule in **`config/editorial_transcript_rules.json`** and run **`scripts/editorial_transcript_pass.py`** so every pipeline run stays consistent. Rules support optional **`flags`** (`IGNORECASE`, `MULTILINE`, `DOTALL`) for multiline caption splits.

## Goals

1. **House style** — e.g. `Erika`, `Candace`, canonical surnames (`Frantzve`), Swedish kinship (`morfar`, `farfar`, `farmor`, `mormor`).
2. **Stable checksums** — `meta.transcript_sha256` must match the UTF-8 bytes of the transcript file the project treats as authoritative.
3. **No placeholder IDs in inscription** — Resolved JSON should not contain `NODE_*`, `CLAIM_*`, or `ART_*` strings (use `assign_ids` / fixed `apply_ids_to_json`).

## Dual transcripts (verbatim + display-clean)

When you want **readers** to see a **clean** transcript (fewer *uh* / *um*) but **retain** the exact caption text for audit:

| Role | Typical path (project-specific) | Notes |
|------|----------------------------------|--------|
| **Verbatim / forensic** | `transcripts_corrected/` as today | Keeps disfluencies; use as **source of truth** for “what STT said” unless you intentionally strip. |
| **Display / inscription** | Second file, e.g. `inscription/episode_NNN_transcript_display.txt`, or a `*_clean.txt` beside the canonical export | Generate with **extra rules** (filler stripping) or a dedicated script; **do not** silently fork without deciding which file **`meta.transcript_sha256`** in JSON refers to. |

**Policy:** If the **inscribed** bundle should use the **clean** file, set **`meta.transcript_sha256`** from the **same bytes** you ship in inscription and run **`sync_transcript_hashes.py`** after generating that file. Keep a **verbatim** copy elsewhere for anyone who wants the unedited line.

**`export_for_inscription.py`** supports:

- **Default:** one file, `inscription/episode_NNN_transcript.txt`.
- **`--dual-transcripts`:** also writes `episode_NNN_transcript_verbatim.txt` (copy of `transcripts_corrected` source). The **display** file remains `episode_NNN_transcript.txt` (hashed).
- **`--display-clean`** (with dual): strips standalone *uh* / *um* in the **display** file only; run **`sync_transcript_hashes.py`** afterward (the full workflow does this when **`BRIDE_EXPORT_DUAL_TRANSCRIPTS=1`** and optional **`BRIDE_EXPORT_DISPLAY_CLEAN=1`**).

Manifest version **2** includes both transcript filenames and a **`transcript_roles`** map when verbatim exists.

## Finding STT issues, spelling, and missing entity nodes

1. **Heuristic scan** — Draft Editor → **Transcripts** → **Scan episode** (`config/transcript_suspicious_patterns.json`).
2. **LLM sense scan** — Same tab; uses **`config/transcript_canonical_glossary.json`** (extend with institutions/programs and canonical spellings). Flags likely errors; queue **overrides** or add **editorial rules**.
3. **Editorial regex** — Recurring fixes → **`config/editorial_transcript_rules.json`** → **`editorial_transcript_pass.py`** → **`sync_transcript_hashes.py`**.
4. **Structured extraction** — **`templates/bride_charlie_entity_extraction.md`** + **`brief/monument_zero_briefing.md`**: named **government programs** and **institutions** must get **nodes** (not only meme rows). **Re-run Phase 1** (or hand-edit `phase1_output`) when prompts change, then **`assign_ids`**.
5. **Validators** — `validate_inscription_bundle.py`, `validate_inscription_node_claims.py`.
6. **Hub** — `/bride_of_charlie/` index tables; **`/api/bride/hub/validate-node-claims`** for edge consistency.

## Scripts (project root: `projects/monuments/bride_of_charlie`)

| Step | Command | Purpose |
|------|---------|---------|
| Editorial regex rules | `python3 scripts/editorial_transcript_pass.py` | Applies `config/editorial_transcript_rules.json` to `transcripts_corrected/` + `inscription/episode_*_transcript.txt`. Raw `transcripts/` is **skipped** unless `--include-raw`. |
| Preview | `python3 scripts/editorial_transcript_pass.py --dry-run` | Count replacements only. |
| SHA-256 sync | `python3 scripts/sync_transcript_hashes.py` | Sets `meta.transcript_sha256` in `inscription/episode_NNN.json` and `phase1_output/episode_NNN_*.json` from the resolved transcript file. |
| Human overrides | `python3 scripts/apply_transcript_overrides.py` | Applies **`config/transcript_overrides.json`** items with `status: accepted` after editorial pass. Draft Editor → **Transcripts** tab to propose / accept. |
| Fix legacy `NODE_` in JSON | `python3 scripts/fix_inscription_node_placeholders.py` | Rewrites `NODE_123` → `N-123` everywhere in inscription JSON (or re-run `assign_ids --batch` after code fix). |
| Validate | `python3 scripts/validate_inscription_bundle.py` | Fails if hash mismatch, **forbidden recurring STT** (e.g. `Lorie France`, `Kenton Lorie`), or placeholders remain. |

## Workflow integration

- **`run_full_workflow.py`**: Raw `transcripts/` stay immutable; `transcripts_corrected/` is built from raw + Neo4j name corrections. **`neo4j_corrections apply-dir` overwrites `transcripts_corrected/`** — any scholarly edits there are lost unless you run the editorial pass **again** after each apply-dir.
- Set **`BRIDE_EDITORIAL_PASS=1`** to run `editorial_transcript_pass.py` + `sync_transcript_hashes.py` automatically **after** Stage 2 `[2.2]` (and keep this on for consistent runs).
- **`inscription/episode_*_transcript.txt`** is updated by the editorial script too; treat it as reference beside JSON when present.
- **Neo4j**: After changing transcripts or inscription JSON, re-ingest when needed:  
  `uv run ... python scripts/neo4j_ingest.py --force`  
  (or your usual ingest path).

## Extending rules

Edit `config/editorial_transcript_rules.json`. Rules are applied **in order** (each rule runs a full pass over the file; put **specific** phrases before **broad** patterns like `\bKent wasn\b`). Prefer narrow patterns; run **`--dry-run`** first.

**Recommended:** set **`BRIDE_EDITORIAL_PASS=1`** in `.env` (or export before runs) so `run_full_workflow.py` runs editorial + hash sync after each `neo4j_corrections apply-dir`.

### Puns, jokes, and non-literal speech

Broad “fix the name” rules will **damage** intentional wordplay (e.g. ep5 ~01:31 **Frantzvestein**). Typical engineering patterns:

1. **Narrow, explicit rules** — One-off replacements with a **comment** (“intentional pun; not a real person”) beat a global `France → Frantzve` rule on that span.
2. **Overrides / exception table** — `(episode, timestamp) → exact string` merged after bulk normalization (common in localization and CMS).
3. **Layered text** — Keep **raw STT** vs **display transcript**; apply aggressive cleanup only where appropriate.
4. **Quoted spans** — Don’t run name normalization inside marked quotes unless policy says so.
5. **Tests / golden lines** — Snapshot a few known-hard captions so CI catches regressions.

## Prevention (already in code)

- **`assign_ids.py`**: Writes inscription JSON to **`project/inscription/`** by default (not `drafts_dir.parent`), and **`apply_ids_to_json`** now replaces **`node.related_nodes`** through `ref_to_id`.
- **Validation**: Run `validate_inscription_bundle.py` in CI or before merge.

## Optional: regenerate drafts from Phase 1

After transcript + phase1 hash sync:

```bash
python3 scripts/assign_ids.py --batch phase1_output/ --drafts drafts/ \
  --fresh-ledger --episode-output-names
```

Use only when you intend a full series ID regeneration.
