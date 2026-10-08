# CKA adversarial audit, Wave 1 (main 9f16249)

Transit full adversarial audit of CKA at main 9f16249 returned FAIL (2 P0, 20 P1, 23 P2 groups).
Wave 1 covers the people-integrity items only. Transcript-driven only (no video).

## Files

| File | Rows | What it records |
|------|------|-----------------|
| `mentions_decisions.csv` | 236 | Every Mentions / Related Nodes person decision. `source`: `P1` = the 110 audit P1 rows (49 REMOVE, 46 REPLACE, 15 KEEP); `EXTRA` and `PHASE_B` = local-placeholder episodes (eps 21, 38, 67, 75, 92, 96, 120, 130, 143, 148, 154); `ITEM4` = ep161 tombstone-collision renames; `EP107` = ep107 rewrite; `ORPHAN_FIX` = persons whose only cite was a wrong Mention, re-cited where the transcript names them. |
| `person_moves.csv` | 30 | Person id moves, collapses and no-survivor retirements. |
| `ep107_renumber_map.csv` | 49 | ep107 claim, artifact, anchor and node renumbering. |
| `retired_ledger_rebuild.csv` | 653 | Per-key action for the `config/retired_node_ids.json` rebuild. |

Em dashes inside quoted legacy names are rendered as hyphens in these CSVs.

## Decision rule for Mentions

A person stays on a claim only when named in the claim text (title, Claim, Transcript Snippet), or in the
episode transcript within +-240 s of the claim timestamp (+-480 s for the BoC-remapped eps 1-10, which carry
timestamp drift). ASR spellings count (e.g. "Andrew Kova" for Andrew Kolvet) and were added as canonical
aliases. Role references in the claim text ("her husband", "her sister") count and are listed under
`config/preflight_gates.json` `mention_grounding.reviewed`.

## Gates added (projects/monuments/scripts/dia_preflight.py, all P1)

`person_like_topic`, `mention_grounding`, `claim_ts_past_end`, `claim_missing_from_drafts`,
`duplicate_claim_header`, `tombstone_collision`. Residuals at the Wave 1 tip belong to Wave 2
(CLM-P1-1 duplicate headers, CLM-P1-2 inscription-only claims, CLM-P1-5 beyond-end timestamps).
