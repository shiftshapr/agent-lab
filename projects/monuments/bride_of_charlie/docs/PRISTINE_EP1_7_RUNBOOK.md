# Runbook: pristine transcripts + inscription JSON (episodes 1–7) + healthy graph

Goal: **seven raw transcripts**, **corrected + editorial + overrides + hashes** aligned, **drafts → inscription JSON** without placeholders, **Neo4j** consistent with what you ship.

All commands assume **agent-lab** repo root unless noted. From `bride_of_charlie/` use `python3 scripts/...`.

---

## 1. Lock scope

- Set **`BRIDE_EXPECTED_EPISODES=7`** in `.env` if you want fetch / counts to target exactly seven links (`run_full_workflow` / `resolve_expected_episodes`).
- Confirm **`transcripts/episode_001_*.txt` … `episode_007_*.txt`** exist (raw is never hand-edited; fixes go through corrected + editorial + overrides).

---

## 2. Transcript stack (ground truth for analysis)

Order (already documented in **EDITORIAL_PASS.md** / **TRANSCRIPT_OVERRIDES.md**):

1. **`neo4j_corrections.py apply-dir`** — `transcripts/` → `transcripts_corrected/`
2. **`editorial_transcript_pass.py`** — house style (`BRIDE_EDITORIAL_PASS=1` in full workflow)
3. **`apply_transcript_overrides.py --apply`** — only **`accepted`** rows (`BRIDE_TRANSCRIPT_OVERRIDES=1`)
4. **`sync_transcript_hashes.py`** — JSON `meta.transcript_sha256` matches the transcript bytes you treat as authoritative

Human loop:

- **Draft Editor → Transcripts**: heuristic scan, LLM sense scan, **Queue → Preview → Accept & apply** (do **not** bulk `--prune-status proposed --confirm-prune** unless you intend to discard queued fixes).
- Re-run **sync** after any inscription transcript change.

---

## 3. Analysis artifacts (drafts → inscription)

- **Two-phase** episode analysis + **`assign_ids`** → **`drafts/episode_NNN*.md`**
- **`export_for_inscription.py`** — drafts + corrected transcripts → **`inscription/episode_NNN.json`** + **`episode_NNN_transcript.txt`**

Full pipeline (destructive to drafts if you use default backup behavior): from **`bride_of_charlie/`**:

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
python3 scripts/run_full_workflow.py --skip-fetch --stop-after 5
```

Then run **Stage 5b** manually if you stopped at 5, or run through **6** on a copy:

```bash
# From agent-lab (uv project), after drafts exist:
uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/export_for_inscription.py \
  --drafts projects/monuments/bride_of_charlie/drafts \
  --inscription projects/monuments/bride_of_charlie/inscription \
  --transcripts projects/monuments/bride_of_charlie/transcripts_corrected
python3 projects/monuments/bride_of_charlie/scripts/sync_transcript_hashes.py
```

Adjust paths if you run from `bride_of_charlie` with `python3 scripts/export_for_inscription.py …`.

---

## 4. Validators (must be green for “pristine”)

**Bundle (hashes, forbidden STT strings in transcripts + JSON strings, no `NODE_*/CLAIM_*/ART_*`):**

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
python3 scripts/validate_inscription_bundle.py --episodes 1-7
```

**Node ↔ claim edges (inscription JSON only):**

```bash
cd ~/workspace/agent-lab
uv run --project framework/deer-flow/backend \
  python projects/monuments/bride_of_charlie/scripts/validate_inscription_node_claims.py
```

Optional strictness: **`--strict-warnings`** once errors are gone.

**Graph (Neo4j):** requires **`NEO4J_URI`** (e.g. `bolt://127.0.0.1:17687`):

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
python3 scripts/neo4j_ingest.py --force
python3 scripts/neo4j_validate.py
```

Ingest parses **`drafts/*.md`**. If episode 8+ drafts exist, the graph will include them too—either keep only 1–7 in drafts for this milestone, or accept extra nodes until you split environments.

---

## 5. Review and quality signals

- **`python3 scripts/review_status.py list`** — human review state under **`inscription/.review_state.json`**
- **`python3 scripts/quality_score.py`** — where to deepen claim grounding / connectivity (episodes 2 & 6 historically weaker)
- **`python3 scripts/cross_episode_analysis_v2.py`** — convergence / pressure narrative (regenerate after inscription stabilizes)

---

## 6. Definition of done (episodes 1–7)

| Check | Command / criterion |
|--------|---------------------|
| Transcript bytes ↔ JSON hash | `validate_inscription_bundle.py --episodes 1-7` |
| No Phase-1 placeholders in JSON | same |
| No known forbidden STT blobs in shipped transcript + JSON strings | same |
| Node–claim consistency | `validate_inscription_node_claims.py` |
| Neo4j integrity | `neo4j_validate.py` after `neo4j_ingest.py --force` |
| Human sign-off | `review_status.py` → **approved** / **promote** to **`output/`** when ready |

---

## 7. If something fails

- **Hash mismatch** — Re-run **`sync_transcript_hashes.py`** after fixing the transcript file the JSON points at; re-export if drafts changed.
- **Graph dirty after transcript edits** — Re-**ingest** **`--force`** and re-**validate**.
- **Verify queue vs inscription** — `python3 scripts/apply_transcript_overrides.py --verify-inscription --episode N`
