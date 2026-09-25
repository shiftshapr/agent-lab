# DIA monument preflight

Merge-blocking harness for `projects/monuments/<slug>/` before **CLEAR**, merge-ask, or pack promotion.

## Run

From agent-lab root:

```bash
python3 projects/monuments/scripts/dia_preflight.py --monument bride_of_charlie
python3 projects/monuments/scripts/dia_preflight.py --monument cka
# or, with uv:
uv run python projects/monuments/scripts/dia_preflight.py --monument bride_of_charlie
uv run python projects/monuments/scripts/dia_preflight.py --monument cka

python3 projects/monuments/scripts/dia_preflight.py --monument bride_of_charlie --json /tmp/preflight.json
python3 projects/monuments/scripts/dia_preflight.py --monument bride_of_charlie --tip 3e79db6
python3 projects/monuments/scripts/dia_preflight.py --self-test
```

Convenience wrapper (same flags, default monument):

```bash
python3 projects/monuments/bride_of_charlie/scripts/dia_preflight.py
```

**Exit 0** only when there are no **P0** or **P1** findings. **P2** / **WARN** are advisory (soft cleanup can ride in the same fix-all PR).

## Hard gates (P0 / P1)

| Check | Severity | What it catches |
|-------|----------|-----------------|
| `person_band` | P0 | Person with `Node Type: Person` and N ≥ 1000; Topic/Org/Place with N &lt; 1000 |
| `person_density` / `topic_band_density` | P0 | Swiss-cheese gaps in N-1..max person or N-1000+ topic band |
| `intro_order` | P0 | `New Nodes Introduced` ledger order violates ascending id within band |
| `retired_citation` | P0 | Cites N-* that is not on the active register (tombstone ghost id) |
| `register_orphan` | P0 | Person in register never on any Claim/Artifact **Related Nodes** line |
| `remap_sync` | P0 | `canonical/nodes.json` or `inscription/` node name ≠ draft register |
| `meme_reuse` / `meme_global` | P0 | Same M-id, different term (per-episode or global) |
| `unknown_node` | P1 | Cites N-* absent from Node Register |
| `stamp_form` | P1 | Claim/Video timestamp bare `M:SS` instead of `HH:MM:SS` |
| `tip_match` | P0 | `--tip` or pack `TIP.txt` / `MANIFEST` ≠ git HEAD |

Grounding, transcript SHA, and name web-search remain in `scripts/verify_drafts.py` and `pipeline_gates.py`; run those in the analysis pipeline. Preflight focuses on ledger/remap/inscription class bugs from the BOC eps 1–8 cycle.

## Compressed review loop (Daveed lock)

1. **No CLEAR / no merge-ask** unless `dia_preflight` exits **0** on the **exact tip SHA** under review (`--tip <sha>`).
2. **One fix-all PR per cycle** — hard P0/P1 fixes and soft P2 hygiene in the same PR; no separate “cleanup-only” PR that forces a second hostile pass.
3. **Hostile once on the pack tip only** — do not CLEAR tip A and ship tip B in one review window.
4. **Remap contract** — any N-id change in one PR must include: draft `Related Nodes`, register `*Related*`, `config/retired_node_ids.json`, regenerated `inscription/`, and `canonical/nodes.json`. Preflight `remap_sync` enforces draft ↔ canonical ↔ inscription names.

## Neo4j promote (staging → prod)

- Staging: port **27687** — team promote after preflight + ingest validation.
- Prod: port **17687** — **query-only** for Bill D / Transit; no `--force` ingest on prod from agents.
- After promote, run read-only asserts: `projects/monuments/scripts/neo4j_post_promote_assert.cypher` (adjust `$PersonBandMax` if ledger grows).

## CI

No monument workflow in-repo yet — **manual gate** before CLEAR. Wire `dia_preflight.py --monument <slug>` into Actions when a monument PR workflow exists.

## Current `main` (`bride_of_charlie`)

At tip `3e79db6`, preflight **passes** (0 P0 / 0 P1). Typical soft findings: **P2** `register_related_empty` for persons with claim citations but empty register `*Related: *` lines (optional hygiene).
