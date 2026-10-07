# Epistemic graph staging smoke runbook

**Target:** Daveed staging Neo4j `bolt://127.0.0.1:27687` (user `neo4j` / password `openclaw`).

**Hard locks**

- No prod (`17687`) write or promote from this harness.
- Do not start `openclaw-neo4j` or bare `7687` as a substitute for staging.
- No inscription pack zip; no BoC promo.
- Prefer additive `MERGE` ingest; never indiscriminate `--force` wipe.

## 1. Preflight (local, no Neo4j)

```bash
python3 projects/monuments/scripts/dia_preflight.py --monument cka --tip "$(git rev-parse HEAD)"
```

Expect exit 0 with P0=0.

## 2. Unit tests (offline)

```bash
python3 projects/monuments/bride_of_charlie/scripts/test_neo4j_ingest_parse.py
```

## 3. Optional minimal CKA ingest into staging

Only when staging Bolt is reachable from this host:

```bash
export NEO4J_URI=bolt://127.0.0.1:27687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=openclaw
# Additive MERGE; do not --force wipe unless Daveed explicitly orders a staging reset.
python3 projects/monuments/bride_of_charlie/scripts/neo4j_ingest.py --monument cka
```

If staging is unreachable: leave ingest unrun; still land code + harness; report SKIPPED.

## 4. §5 smoke pack

```bash
NEO4J_URI=bolt://127.0.0.1:27687 \
  python3 projects/monuments/scripts/epistemic_graph_smoke.py
```

Cypher twin: `projects/monuments/scripts/epistemic_graph_smoke.cypher`.

The runner prints edge counts for `ASSERTS`, `SUPPORTED_BY`, `REVISES`, `CONTRADICTS`, `MENTIONS`, `APPEARS_IN`, `CONNECTED_TO`, `CAPTURED_AT` (plus `SUPPORTS` / `QUALIFIES` / `FROM_EPISODE`) and executes the seven design §5 queries. Empty result sets are allowed (PASS means queries execute without error). Connection failure returns SKIPPED (exit 3), not a fabricated PASS.

## 5. After smoke

Report edge counts + PASS/FAIL/SKIPPED in the PR body. Ask Transit for one independent re-audit of the draft PR tip. Do not merge from the agent path.
