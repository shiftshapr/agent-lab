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
See `orphan_mint_map.csv` (old id → new id for all 49 mints) / `orphan_persons_decisions.csv`. 49 persons minted into the lowest free holes in true first-introduction order (N-629 Dan Bongino ep15 … N-977 Matt Tardio ep152). N-476 Bill Aman retired into N-66 Bill Ackman. The person band N-1..N-999 is now full: `next_person_id` is **null** pending a Daveed ruling. Reserved baseline ids N-17, 20, 22, 27, 28, 31, 32, 33, 38, 55 (reasons in `config/retired_node_ids.json`).

### Memes
M-74..M-84 minted, numbered densely by first introduction within the batch (`meme_renumber_map.csv`, `memes_decisions.csv`); next_id **85**. M-85 Bride of Charlie rejected (series/work title → Wave 4 Thing debt). Lo and Behold (M-83) qualifies (26 hits / 20 episodes). Yanking = M-24 reuse; Frank Turek rejected as meme.

### Steering correctness (Oct 8)
1. **ep150 offset bug:** Related Nodes emptied on wrong N-12xx cites; Mentions remapped to grounded globals (N-1/N-3/N-5/N-56/N-182); A-2352.1 related fixed; spray nodes N-1207..1215 removed from inscription. N-56 Ye Mentions on short-token claims deferred (`ep150_ye_mentions_note.md`).
2. **"former local id" cleanup** on 17 drafts (082, 085, 091, 097, 126, 128, 130, 132, 133, 134, 144, 145, 147, 150, 152, 153, 155). Offset residue also scrubbed from inscription (`inscription_orphan_refs_removed.csv`, 373 rows) and canonical episode lists (`canonical_episode_list_fixes.csv`, 130).
3. **C-1971** claim_timestamp stamped `00:19:30` (draft + inscription).
4. **ep128 C-3072:** Related N-2132 only; Mentions N-192.
5. **ep93:** ungrounded N-576 Mention removed from C-2760 (intro is ep107).
6. Family-only inscription `bundle_name` overruns fixed (20 entries).

### Companion
Rebuilt `cka/companion/brc222-2.0.0/`: **9288 bridges** vs main 9209 (**+79**; +36 vs b558034's 9252). Edges: isMemberOf 6405 (+50 vs main), isSupportedBy 2842 (+19), isQualifiedBy 13 (+9), isCorroboratedBy 9 (+1), contradicts 19 (+0). The b558034 round added: isSupportedBy C-3764←A-2127.2 and the new claim anchors; isCorroboratedBy C-3764←C-3767; isQualifiedBy C-3126←C-3767; and the six Revises C-3771..C-3776, ruled isQualifiedBy in `config/companion_revises_rulings.json`.

## Resubmission after Transit FAIL at 73d663b
Every fixes.csv row and finding is resolved in `fixes_resolution.csv`. Per-row triage (decision + reason on every row):

| File | Rows | MINT | ALIAS | KNOWN | FIXED | REJECT | DEFER |
|------|------|------|-------|-------|-------|--------|-------|
| missing_nodes_triage.csv | 531 | 55 | 11 | 32 | 0 | 208 | 225 |
| missing_claims_triage.csv | 223 | 23 | 0 | 41 | 0 | 115 | 44 |
| missing_artifacts_triage.csv | 85 | 3 | 0 | 32 | 0 | 18 | 32 |
| missing_memelinks_triage.csv | 30 | 0 | 0 | 1 | 24 | 5 | 0 |
| dia_gaps_triage.csv | 76 | 6 | 0 | 47 | 0 | 16 | 7 |
| bridge_gaps_triage.csv | 32 | 0 | 0 | 4 | 7 | 16 | 5 |
| incorrect_residuals.csv | 17 | 0 | 0 | 5 | 12 | 0 | 0 |
| spelling_triage.csv | 124 | 0 | 68 | 7 | 10 | 39 | 0 |

DEFER is used only where a Daveed ruling, Wave 4 or the Ties PR is needed:
- **Person band full** (persons named in claims with no node; N-1..N-999 has no free id).
- **Org-node scope** (organizations named in claims).
- **Wave 4** (works, products, events and objects).
- **19 skeleton episodes** whose drafts have empty Artifact/Claim registers (84, 95, 100, 101, 103–106, 108, 109, 111–119). A full extraction pass is a scheduling call.
- **Ties PR** (artifact→claim Related links).

New in this push:
- 25 claims, C-3742..C-3766. Revises: C-3742, C-3743. DIA tip-line: C-3744, C-3745, C-3746, C-3764. Sampled gaps: C-3747..C-3753. Triage mints: C-3754..C-3763, C-3765, C-3766.
- 6 artifacts.
- 25 MemeLink occurrences.
- Verbatim quote fixes, logged in `quote_fixes.csv`.
- 82 pre-existing draft-vs-inscription mismatches reconciled (`draft_inscription_reconcile.csv`).
- New gate `named_before_intro` with tests. Pre-Wave-3 debt is listed in `named_before_intro_debt.csv`.

## Resubmission after Transit FAIL at b558034 (0 P0 / 3 P1 / 6 P2)
Every row of the new fixes.csv (9) and findings.csv (F1–F10) has a row in `fixes_resolution.csv` (source tag `b558034:`). The earlier rounds' rows are kept below them. The triage table above shows the current counts.

- **N-952 → N-916 (Lynn Forester de Rothschild).** Tombstone `legacy-N-952` survives_as N-916 and is never reused. Aliases Lindy Rothschild, Linda Rothschild and Lynn Forester moved to N-916. Refs repointed in drafts (ep76), inscription (eps 72, 76), canonical and the companion. N-916 is introduced at ep72, before its first cite (ep76).
- **ep131 bounty beats.**
  - C-3767 (00:19:05, payoff of the C-3764 lunch bounty; Supports C-3764, Qualifies C-3126).
  - C-3768 (00:25:07, Gary, president of AIPAC Nebraska).
  - C-3769 (00:26:05, the new $25,000 bounty).
  - Artifacts A-2524.1–.3 (verbal reference, host on air).
  - M-12 occurrences at 00:19:05 and 00:26:05.
  - C-3764 is now anchored by A-2127.2 (ep124 01:07:02).
  - "bounty" is added to `config/dia_scan_terms.json`. The corpus re-scan adds 9 `dia_bounty_rescan` rows to `dia_gaps_triage.csv`.
- **Viewer handles.** 17 viewer/commenter handles moved DEFER → REJECT. Real persons waiting for band capacity: **95** (112 − 17). This push adds two new DEFERs, Matt Robinson (ep124) and Gary Jabitch (ep131), for **97** in total. General Holt is a same-person DEFER for Blaine Holt and is not counted as waiting.
- **Triage reasons.** 14 false REJECTs → KNOWN (incl. Gernot N-184, Pastor Hibbs/Hibs N-309, Danny Danny N-611, Theo Vaughn N-205). Project Looking Glass and its short form "Looking Glass" → KNOWN N-1484. The remaining org/work DEFERs are relabelled kind organization (98) / topic (29). Placeholder-timestamp KNOWNs re-checked:
  - ep80 rows → REJECT and KNOWN C-2507;
  - ep94 → KNOWN C-2773;
  - A-2121.1 timestamp set to 00:14:07.
- **Bill Ackman.** A-2117.1 relabelled, now with Related N-66. Pledge claim C-3770 + A-2117.4 (ep124 00:06:50); Matt Robinson has no node and is DEFER "person band full, awaiting Daveed". Revises (isQualifiedBy) claims: C-3771→C-1194, C-3772→C-1212, C-3773→C-1295, C-3774→C-3324, C-3775→C-3680, C-3776→C-3696.
- **Klacik and Mengele.**
  - N-687 Kimberly Klacik added to `transcript_before_graph.csv`.
  - A-1699.1 now has Related N-630.
  - The Mengele decisions row is split into ep65 and ep97 rows.
- **Hygiene.**
  - N-161 retired (`legacy-N-161`, no survivor, never reused). C-3730 and A-2519.3 keep N-1 only.
  - Canonical names cleaned: N-877 Helmut Becker, N-713 Paul Havsgaard, N-365 Shauni Kerkhoff, N-193 Judge Tony F. Graf Jr. The old spellings are kept as aliases.
  - C-3743 has a transcript snippet.
- **Person band lock** (until Daveed rules). N-1..N-999 is full. Retired or tombstoned ids are never reused, and no person is minted at N-1000 or above; new persons are DEFER "person band full, awaiting Daveed". This is written in `config/preflight_gates.json` (`person_band_lock`), `cka/README.md` and `docs/DAY0.md`, and is enforced by the new P1 preflight gate `person_band_lock` (2 tests).
- **Wave 4 debt.** F10 (named_before_intro debt) and F4 (skeletons) are logged in `wave4_event_thing_debt.md`.

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
- pytest scripts/: 72 passed
- inscription orphan refs: 0; draft vs inscription Mentions/Related on claims: 0 (pre-existing residuals unchanged from main: 181 sub-artifact Related, C-1377/C-2229 anchors, 6 claim-text drifts, A-2470.1 description)
