# Node id compaction, no tombstones (2026-10-13)

Daveed's rulings (13 Oct 2026):

1. Persons get **N-1..N-9999**, and topic, organization and place nodes start at **N-10000**.
2. **No tombstones.** CKA keeps no retired-id ledger.
3. Ids are **compacted with no holes**.

This is a one-time mechanical change: only ids change, never content.

## Result

| Band | Nodes | Ids | Next id |
|---|---|---|---|
| Person | 607 | N-1..N-607 | N-608 |
| Topic / org / place | 903 | N-10000..N-10902 | N-10903 |

Each band keeps its previous id order. The map is monotone, so every intro, hole-mint and tip-mint order relation the gates check still holds. `id_map.csv` lists each node's old id, new id, name and type.

## Removed

- `config/retired_node_ids.json`: 494 tombstones and 10 reserved baseline ids.
- `config/person_band_snapshot.json`.
- The `person_band_lock` gate, together with its config and tests.
- `retired_ids` on 196 nodes.
- The long `remap_note` history in `canonical/nodes.json`. That history is still in git and in the audit folders.
- From the `episode_000` baseline ledger line: 67 ids that are no longer nodes (`baseline_ids_dropped.csv`).
- From `config/preflight_ledger_baseline.json`: the same dead ids.
- The hostile check `HUSBAND_DUPLICATE_SMELL`, which hardcoded the old N-59/N-100 pair. N-100 no longer exists.

## Scope

- **Rewritten:**
  - drafts
  - inscription
  - canonical
  - config
  - companion (bridges unchanged at 9288; a builder regen matches apart from `generated_at` and `cka_root`)
  - `scripts/hostile_hard_gates.py`
- **Not rewritten:**
  - Transcripts.
  - Audit CSVs and notes dated before 2026-10-13. They keep the ids of their time; translate them with `id_map.csv`.
  - The historical one-shot `cka/scripts/batch*` / `catchup_*` scripts. Do not re-run them.

Bride of Charlie still has its own retired-id ledgers. The shared `retired_citation` / `tombstone_collision` gates run only where such a ledger exists.

Script: `cka/scripts/compact_node_ids.py`. It refuses to run a second time.
