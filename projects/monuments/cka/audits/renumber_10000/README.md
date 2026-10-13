# Topic band renumber to N-10000+ (2026-10-13)

Daveed's ruling (13 Oct 2026): persons get **N-1..N-9999**, and topic, organization and place nodes start at **N-10000**. This is a one-time mechanical renumber that changes ids only. No content changed.

## Mapping

- Topic, organization and place nodes **N-1000..N-2393 → N-10000..N-11393**. The offset is **+9000**, so old `N-1234` is now `N-11234`. Intro order and density are unchanged.
- Topic tombstones move with their ids, so `legacy-N-1001` is now `legacy-N-10001`, and the same for `wave1-` keys.
- The PR 47 person tombstones **N-10000..N-10033** were minted on 2026-10-04 and remapped into low-band holes in PR 50. They are renamed **`pr47-N-10000..pr47-N-10033`** wherever they appear, so the topic band can take those ids. Daveed chose this reuse over leaving a gap. Their `survives_as` targets are unchanged.
- `canonical/nodes.json` changes: `next_investigation_id` goes from 2394 to **11394**. `next_person_id` goes from null to **1000**, because new persons are now minted from N-1000.
- In `config/preflight_ledger_baseline.json`, `topic_node_ids` moves by +9000.

`renumber_map.csv` lists every active node and tombstone (old id, new id). `changed_files.csv` lists each rewritten file with its token count.

## Scope

- **Rewritten:** drafts, inscription, canonical, config, companion (bridges unchanged at 9288; a builder regen matches the rewritten package byte for byte apart from `generated_at` and `cka_root`), audits, docs, README, and `scripts/hostile_hard_gates.py`.
- **Not touched:**
  - Transcripts and transcript SHAs. They contain no N-ids.
  - Vendor files.
  - The historical one-shot `cka/scripts/batch*`, `catchup_*`, `hostile_fix_batch1.py` and `remap_boc_batch1.py`. They encode the old bands and must not be re-run.
  - BoC-era keys such as `pr33-person-N-1067`, which refer to Bride of Charlie ids.
- **Old prose:** in older free-text notes, abbreviated range tails written before the renumber (e.g. `N-11275..2300`, `N-10013/1020/1031`) keep the old 4-digit tail. Read the tail as old numbering, +9000.

## Gates

- `dia_preflight.py` reads the bands per monument from `node_bands` in `config/preflight_gates.json`. Bride of Charlie keeps the default bands, and its output is byte-identical before and after this change.
- `person_band_lock` stays on for the pinned N-1..N-999 band: no tombstone or reservation is reused, and no pinned id changes identity. It waives `next_person_id` and persons at N-1000+ because the band is widened (`capacity_ruling`).

Script: `cka/scripts/renumber_topic_band_10000.py`. It refuses to run a second time.
