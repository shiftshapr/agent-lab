# Wave 3 adversarial (cka-adv-wave3)

Date: 2026-10-08 PT. Branch `cka-adv-wave3` from main `26f2115a3927de7e4ed5926fabc03a2cf9c9cb6a`.

## Scope completed

### ORDER OF WORK A + B1–B7
- A: CRLF restore on wave1 `mentions_decisions.csv`, `retired_ledger_rebuild.csv`
- B1: C-3661 / A-2489.1 → 00:17:50; A-2485.1 → 00:47:35
- B2: 99 draft-only ids synced into inscription + `inscription_missing` P1 gate + tests (documented in `DIA_PREFLIGHT.md`)
- B3: `cited_before_intro` covers topics in strict mode + test
- B4: legacy-N-997 reason → N-628; mentions_backfill C-1830 → N-628
- B5: A-1696.1 / N-1535 description; N-279 alias "Robert Craft"; hole-mint README note
- B6: N-525 Root Brands → N-2393 org tip-mint; `next_investigation_id` 2394
- B7: `transcript_before_graph.csv` (74 rows)

### Orphan persons (dense hole mint)
See `orphan_mint_map.csv` / `orphan_persons_decisions.csv`. Persons minted N-629..N-813 into free holes (next_person_id **814**). Register rows + Hole-minted ledger lines; intro order and hole_mint_order gates pass.

### Memes
M-74..M-85 minted (`memes_decisions.csv`); next_id **86**. Yanking = M-24 reuse; Frank Turek rejected as meme.

### Steering correctness (Oct 8)
1. **ep150 offset bug:** Related Nodes emptied on wrong N-12xx cites; Mentions remapped to grounded globals (N-1/N-3/N-5/N-56/N-182); A-2352.1 related fixed; spray nodes N-1207..1215 removed from inscription. N-56 Ye Mentions on short-token claims deferred (`ep150_ye_mentions_note.md`).
2. **"former local id" cleanup** on 17 drafts (082, 085, 091, 097, 126, 128, 130, 132, 133, 134, 144, 145, 147, 150, 152, 153, 155). Offset residue also scrubbed from inscription (`inscription_orphan_refs_removed.csv`, 373 rows) and canonical episode lists (`canonical_episode_list_fixes.csv`, 130).
3. **C-1971** claim_timestamp stamped `00:19:30` (draft + inscription).
4. **ep128 C-3072:** Related N-2132 only; Mentions N-192.
5. **ep93:** ungrounded N-576 Mention removed from C-2760 (intro is ep107).
6. Family-only inscription `bundle_name` overruns fixed (20 entries).

### Companion
Rebuilt `cka/companion/brc222-2.0.0/`: **9209 bridges**, set-identical to main (delta 0). Labels refreshed for dash fidelity / truncated descriptions.

## Deferred (all DEFER in triage CSVs)
| File | Rows |
|------|------|
| missing_nodes_triage.csv | 529 |
| missing_claims_triage.csv | 223 |
| missing_artifacts_triage.csv | 85 |
| missing_memelinks_triage.csv | 30 |
| dia_gaps_triage.csv | 67 |
| bridge_gaps_triage.csv | 32 |
| incorrect_residuals.csv | 17 |

Also: Holker/Kirraou deferred; Maquilo rejected; Something Is Not Right deferred; commenters rejected (Wave 2 viewer-handle policy). Wave 4 Event/Thing debt: `wave4_event_thing_debt.md`. Ties avoidance: `ties_avoidance.md`.

## Explicit non-goals
- No Neo4j / pack / BoC deploy
- PR 55 and BRC-222 2.1.0 held
- No Ties implementation; no new Ties-covered untyped Related
- No dash re-work (PR 61 squash-merged)
- Do not start Wave 4 (Event/Thing types); leave clear events/objects as debt

## Sequencing lock (Daveed via Transit)
Wave 3 → Wave 4 → Ties edges PR → PR 55 rebase.

## Gates (as of package)
- CKA dia_preflight: PASS 0/0/0
- BoC preflight: PASS
- dia_preflight --self-test: OK
- hostile_hard_gates: CLEAR
- pytest scripts/: 68 passed
