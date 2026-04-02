# Fix the fucking names — copy-paste

**Checklist (tick boxes):** [`NAME_FIX_LIST.md`](./NAME_FIX_LIST.md)

**Same person, two names (e.g. Erika Frantzve vs Erika Kirk):** one `**N-*` line with the canonical name, then `*Also known as: …; …*` (semicolon-separated). Ingest fills Neo4j `aliases`. See [`NAMES_FROM_DRAFTS_AUDIT.md`](./NAMES_FROM_DRAFTS_AUDIT.md) § “Same person, more than one name”.

**Always start here:**

```bash
cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
UV="uv run --project ../../../framework/deer-flow/backend python scripts"
```

Use `$UV neo4j_corrections.py …` in the commands below (or paste the full `uv run …` lines).

---

## Path A — The bad spelling is in the **YouTube transcript** (raw `transcripts/*.txt`)

Substring fixes are stored in Neo4j as **`NameCorrection`** and applied when building **`transcripts_corrected/`**. Raw files are **never** edited.

1. **See what’s already in the dictionary**

   ```bash
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py list
   ```

2. **Remove bad rows** (wrong “corrections” from old verify imports — must match `incorrect` **exactly**)

   ```bash
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py remove "exact WRONG string from list"
   ```

3. **Add the right mapping** (what appears in text → what you want)

   ```bash
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py add "WRONG" "RIGHT" --confidence high
   ```

   **Frantzve / Erika family:** concrete pairs live in [`NAME_AUDIT_FRANTZE.md`](./NAME_AUDIT_FRANTZE.md).

4. **Rebuild corrected transcripts**

   ```bash
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py apply-dir transcripts/
   ```

5. **Regenerate drafts** from corrected text (one episode or full — see [`AUTOMATED_WORKFLOW.md`](./AUTOMATED_WORKFLOW.md))

   ```bash
   cd ~/workspace/agent-lab
   export EPISODE_ANALYSIS_PROJECT=bride_of_charlie
   export EPISODE_ANALYSIS_INPUT=transcripts_corrected
   export EPISODE_ANALYSIS_OUTPUT=drafts
   export EPISODE_ANALYSIS_TWO_PHASE=1
   # one episode (5 = fifth sorted episode_*.txt):
   export EPISODE_ANALYSIS_ONLY=5
   export EPISODE_ANALYSIS_FORCE=1
   uv run --project framework/deer-flow/backend python agents/protocol/protocol_agent.py \
     --protocol episode_analysis --project bride_of_charlie --force --only 5
   ```

   Or run the full pipeline: `python projects/monuments/bride_of_charlie/scripts/run_full_workflow.py` (from agent-lab root).

6. **Reload the graph** after drafts look right — **use no fuzzy match** while you’re cleaning names:

   ```bash
   cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
   uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_ingest.py --force --no-fuzzy-match
   ```

---

## Path B — **Transcript is already correct**, only the **draft** (or phase1 JSON) is wrong

- Edit the **Node Register** line in `drafts/episode_*.md` for that `**N-*`**, **or**
- Fix **`phase1_output/`** JSON and rerun **`assign_ids`** / Phase 2, then ingest again (`--force --no-fuzzy-match` if merges bit you before).

---

## Path C — **Neo4j** already has a wrong `canonical_name` or alias (merge / old ingest)

- Fix in **Neo4j Browser**, **or**
- Fix drafts + **`neo4j_ingest.py --force --no-fuzzy-match`** so the graph is rebuilt from source (`NameCorrection` nodes are kept on `--force`).

---

## Sanity checks

```bash
# Spot-check corrected vs garbage strings
rg -n "Bronze|France|Frantzve|Frantze|Frontfay" transcripts_corrected/*.txt

# Dump graph + dictionary + draft N-lines to one markdown file
uv run --project ../../../framework/deer-flow/backend python scripts/list_names_audit.py --out names_audit.md
```

---

## Related docs

| Doc | What |
|-----|------|
| [`NAMES_FROM_DRAFTS_AUDIT.md`](./NAMES_FROM_DRAFTS_AUDIT.md) | Every `N-*` label + full playbook |
| [`NAME_AUDIT_FRANTZE.md`](./NAME_AUDIT_FRANTZE.md) | Frantzve / Erika / Kent-style fixes |
| [`NAME_ISSUES.md`](./NAME_ISSUES.md) | Flag “this is wrong” before you fix it |
| [`AUTOMATED_WORKFLOW.md`](./AUTOMATED_WORKFLOW.md) | Full loop, env vars, one-episode rerun |

**Nuclear reset of the correction dictionary only** (then re-`add` good rows and `apply-dir` again):

```bash
uv run --project ../../../framework/deer-flow/backend python scripts/neo4j_corrections.py clear-all --yes
```
