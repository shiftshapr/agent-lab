# CKA adversarial audit, Wave 1 (main 9f16249)

Transit full adversarial audit of CKA at main 9f16249 returned FAIL (2 P0, 20 P1, 23 P2 groups).
Wave 1 covers the people-integrity items only. Transcript-driven only (no video).

## Files

| File | Rows | What it records |
|------|------|-----------------|
| `mentions_decisions.csv` | 458 | Every Mentions / Related Nodes person decision. `source`: `P1` = the 110 audit P1 rows (49 REMOVE, 46 REPLACE, 15 KEEP); `EXTRA` and `PHASE_B` = local-placeholder episodes (eps 21, 38, 67, 75, 92, 96, 120, 130, 143, 148, 154); `ITEM4` = ep161 tombstone-collision renames; `EP107` = ep107 rewrite; `ORPHAN_FIX` = persons whose only cite was a wrong Mention, re-cited where the transcript names them; `TRANSIT_FIXALL` (62) = Transit audit of head 5ecd06b, items 1, 2, 3, 7 and 8; `TRANSIT_WINDOW` (160) = windowed grounding (93 REMOVE, 3 REPLACE, 54 ADD on new transcript-driven claims, 10 KEEP reviewed role refs). |
| `person_moves.csv` | 31 | Person id moves, collapses and no-survivor retirements. |
| `ep107_renumber_map.csv` | 49 | ep107 claim, artifact, anchor and node renumbering. |
| `retired_ledger_rebuild.csv` | 653 | Per-key action for the `config/retired_node_ids.json` rebuild. |

Em dashes inside quoted legacy names are rendered as hyphens in these CSVs.

## Decision rule for Mentions

A person stays on a claim only when named in the claim text (title, Claim, Transcript Snippet), or in the
episode transcript within +-240 s of the claim timestamp (+-480 s for the BoC-remapped eps 1-10, which carry
timestamp drift). ASR spellings count (e.g. "Andrew Kova" for Andrew Kolvet) and were added as canonical
aliases. Role references in the claim text ("her husband", "her sister") count and are listed under
`config/preflight_gates.json` `mention_grounding.reviewed`.

## Gates added (projects/monuments/scripts/dia_preflight.py)

P1: `person_like_topic`, `mention_grounding` (windowed, see below), `claim_ts_past_end`,
`claim_missing_from_drafts`, `duplicate_claim_header`, `tombstone_collision`,
`name_annotation_mismatch`. P0: `hole_mint_order`. Residuals at the Wave 1 tip belong to Wave 2
(CLM-P1-1 duplicate headers, CLM-P1-2 inscription-only claims, CLM-P1-5 beyond-end timestamps).

Expected `dia_preflight --monument cka` at the tip: P0 0 / P1 88 (46 claim_missing_from_drafts,
39 claim_ts_past_end, 3 duplicate_claim_header) / P2 6 (register_related_empty).

## Transit fix-all (audit of head 5ecd06b)

### Windowed grounding

`mention_grounding` now reads `.txt` and `.md` transcripts and only counts transcript segments
within +-240 s of the Claim Timestamp (+-480 s for eps 1-10). `first_name_ok` lets N-1 and N-2
ground on "Charlie" / "Erika". A placeholder `00:00:00-00:00:01` stamp falls back to the whole episode.
Windowing surfaced 106 ungrounded Mentions (claim, person pairs). 93 spray Mentions were removed, 3 wrong persons were
replaced (C-1724 and C-1926 to N-42 Andrew Kolvet, C-1927 to N-434 Flood), and 10 genuine role
references or Transit rulings were added to `reviewed`. Removing spray Mentions left 33 register
persons with no claim or artifact cite. N-74 Matt Gutman was re-cited on C-1142 (Cox answers
"that report by Matt Gutman"). The other 32 got minimal transcript-driven claims, each anchored to a
verbal-reference artifact: C-3719..C-3746 with families A-2514..A-2520 (eps 1, 2, 3, 5, 8, 9, 10;
host references and viewer comments read on air), and C-3747 on the existing A-1424.2 (ep33, Andrew K. Smith).

### Hole-minted ledger line and order lock

Ids minted into free holes below the band frontier do not go on `New Nodes Introduced` (which must
ascend). They go on a separate ledger line in the episode of their first register row:

    - Hole-minted Nodes (<batch>): N-a, N-b

Batches: `wave1` (eps 75, 92, 107, 148, 161: N-531..N-586 and topic N-2384), `wave1b` (Kim Kardashian
N-587 in ep32 and Danny Philip N-611 in ep125), `seq161` (ep161: N-447, N-472, N-477). Within a batch and band the ids ascend in
first-introduction order and a person batch leaves no free person id below its maximum.

Renumber to first-introduction order (old id at 5ecd06b to new id):

| Old | New | Name |
|-----|-----|------|
| N-572 | N-531 | Chad Ripperger |
| N-531 | N-536 | Ballard |
| N-536 | N-569 | Victor Marx |
| N-570 | N-570 | Corby Hall (unchanged) |
| N-569 | N-571 | Eileen Marx |
| N-573 | N-572 | Melody |
| N-574 | N-573 | Holly |
| N-575 | N-574 | Victor Marx's son |
| N-576 | N-575 | Victor Marx's daughter |
| N-577 | N-576 | Amir Safari |
| N-578 | N-577 | Gloyce |
| N-571 | N-578 | Usha Vance |

Corby Hall keeps N-570 because he is first introduced in ep92 together with Victor Marx.

### New persons

Kim Kardashian N-587 (eps 32, 148) and Danny Philip N-611 (eps 125, 129, 147; alias Danny Phillip,
legacy N-11 survives as N-611). `next_person_id` is 612.
