# Idempotent name corrections

How **Neo4j `NameCorrection`** and **transcript `apply-dir`** behave when you re-run the same workflow.

## Dictionary writes (`add` / `import-from-verify`)

- Each row is keyed by **`incorrect`** (`MERGE (nc:NameCorrection {incorrect: $incorrect})`).
- Re-running **import-from-verify** or **add** with the same pair updates properties in place; it does **not** create duplicate nodes.
- **No-op guard:** If `incorrect` and `correct` are the same (after trim), or either is empty, the row is skipped (avoids useless self-map entries).

## Transcript application (`apply` / `apply-dir`)

- Replacements run longest-match-first from Neo4j.
- **Second run:** If the transcript already contains only the **correct** spelling, the **incorrect** substring no longer appears → **zero** replacements → file is not rewritten (or is unchanged).
- Workflow: apply corrections **before** a graph clear that drops `Person` data but **preserves** `NameCorrection`, then re-ingest — corrections remain stable.

## Canonical nodes ↔ Neo4j

- `canonical_nodes.py` and verify/import pipelines are separate from the `MERGE` semantics above; human-reviewed merges are logged in `adjustments.jsonl` for learning.

## Related

- `scripts/neo4j_corrections.py`
- `scripts/run_full_workflow.py` (apply before clear; preserve `NameCorrection`)
