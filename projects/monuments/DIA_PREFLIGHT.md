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
| `intro_order` | P0 | `New Nodes Introduced` ledger order violates ascending id within band (ids minted into free holes go on the `Hole-minted Nodes` line instead, see `hole_mint_order`) |
| `hole_mint_order` | P0 | `  - Hole-minted Nodes (<batch>): N-a, N-b` ledger lines: each id must be listed in the episode of its first register row, must not also sit on the New, Reused or a secondary `Existing Nodes Reused` line, must not appear on any New, Reused, `Existing Nodes Reused` or Hole-minted ledger line of an earlier episode, must ascend in first-introduction order per batch and band, and a person-band batch must leave no free person id (not active, not tombstoned, not on the episode_000 baseline) below its maximum |
| `retired_citation` | P0 | Cites N-* that is not on the active register (tombstone ghost id) |
| `register_orphan` | P0 | Person in register never on any Claim **Mentions** / **Related Nodes** line or on an artifact `*Related:*` line that also cites a C-/A- id (a register row or a context-only artifact note does not count) |
| `remap_sync` | P0 | `canonical/nodes.json` or `inscription/` node name ≠ draft register |
| `meme_reuse` / `meme_global` | P0 | Same M-id, different term (per-episode or global) |
| `claim_fork` | P0 | Same C-id with different labels (or materially different `Claim:` bodies) across episodes; remint + `Revises:` (and `Contradicts:` if explicit oppose) |
| `unknown_node` | P1 | Cites N-* absent from Node Register |
| `stamp_form` | P1 | Claim/Video timestamp bare `M:SS` instead of `HH:MM:SS` |
| `tip_match` | P0 | `--tip` or pack `TIP.txt` / `MANIFEST` ≠ git HEAD |
| `person_like_topic` | P1 | Topic-band node (N-1000..N-9999) whose name is a person: matches a Person name or alias, honorific plus name, or first-name plus surname shared with a Person; also canonical topic-band ids typed person |
| `mention_grounding` | P1 | Mentions person whose name (full name, alias, or distinctive name word) is absent from both the claim text and the transcript near the claim. Transcripts are `transcripts_corrected/episode_NNN_*.txt` or `.md`. With `window_seconds` set, only transcript segments within +-window of the Claim Timestamp count (`window_seconds_early` for episodes up to `early_max_episode`); a missing or placeholder `00:00:00-00:00:01` stamp, or one past the last marker, falls back to the whole episode. `first_name_ok` ids may ground on a first name. Host ids (`exempt_ids`) and human-reviewed role references (`reviewed`) go in `config/preflight_gates.json` |
| `claim_ts_past_end` | P1 | Claim Timestamp after the episode end (`config/yt_durations.json`, else last transcript marker); monuments without `yt_durations.json` opt out |
| `claim_missing_from_drafts` | P1 | Claim minted in `inscription/` but not defined in any draft |
| `duplicate_claim_header` | P1 | Same C-id header more than once, including residue headers like `**C-1 / C-2**` |
| `tombstone_collision` | P1 | Active canonical id listed in another node's `retired_ids` |
| `name_annotation_mismatch` | P1 | Inline `N-x (Name)` annotation whose Name is not node x (canonical name or alias, else any register row); descriptive labels such as `(verbal reference)` are ignored. For a person node a multi-word label must share the surname (last word) with a name or alias, so a shared first name alone fails. A one-word alias or name variant of a person never satisfies a multi-word label unless that word is the label's surname (last word) |

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
