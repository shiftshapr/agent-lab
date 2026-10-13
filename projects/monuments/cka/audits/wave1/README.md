# CKA adversarial audit, Wave 1 (main 9f16249)

Transit full adversarial audit of CKA at main 9f16249 returned FAIL (2 P0, 20 P1, 23 P2 groups).
Wave 1 covers the people-integrity items only. Transcript-driven only (no video).

## Files

| File | Rows | What it records |
|------|------|-----------------|
| `mentions_decisions.csv` | 457 | Every Mentions / Related Nodes person decision. `source`: `P1` = the 110 audit P1 rows (49 REMOVE, 46 REPLACE, 15 KEEP); `EXTRA` and `PHASE_B` = local-placeholder episodes (eps 21, 38, 67, 75, 92, 96, 120, 130, 143, 148, 154); `ITEM4` = ep161 tombstone-collision renames; `EP107` = ep107 rewrite; `ORPHAN_FIX` = persons whose only cite was a wrong Mention, re-cited where the transcript names them; `TRANSIT_FIXALL` (62) = Transit audit of head 5ecd06b, items 1, 2, 3, 7 and 8; `TRANSIT_WINDOW` (144) = windowed grounding (90 REMOVE, 3 REPLACE, 38 ADD on new transcript-driven claims, 13 KEEP reviewed role refs; ADD rows of the 12 pulled fan-mail claims dropped and C-1160 N-87, C-1185 N-67 and N-86 flipped to KEEP at the re-audit); `TRANSIT_REAUDIT` (15) = Transit re-audit of head ab20e61 (12 RETIRE, 2 ADD, 1 REPLACE). Claim ids are the post-renumber ids. |
| `person_moves.csv` | 44 | Person id moves, collapses and no-survivor retirements. |
| `ep107_renumber_map.csv` | 49 | ep107 claim, artifact, anchor and node renumbering. |
| `retired_ledger_rebuild.csv` | 666 | Per-key action for the `config/retired_node_ids.json` rebuild. |

Dashes inside quoted legacy names are written as en dashes (U+2013) in these CSVs, per Daveed's dash rule of 8 Oct 2026: en dash in prose, never a hyphen, comma or other punctuation in place of a dash; quotes stay exact to the transcript.

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
The re-audit of ab20e61 pulled 12 of these and renumbered the rest to C-3719..C-3735 (see below).

### Hole-minted ledger line and order lock

Ids minted into free holes below the band frontier do not go on `New Nodes Introduced` (which must
ascend). They go on a separate ledger line in the episode of their first register row:

    - Hole-minted Nodes (<batch>): N-a, N-b

Batches: `wave1` (eps 75, 92, 107, 148, 161: N-531..N-586 and topic N-2384), `wave1b` (Kim Kardashian
N-587 in ep32 and Danny Philip N-611 in ep125; these two are frontier mints at and above the old
`next_person_id` 587, not true holes, and sit on their own batch line so the ep125 id stays in order), `seq161` (ep161: N-447, N-472, N-477). Within a batch and band the ids ascend in
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
legacy N-11 survives as N-611). Both are frontier mints (N-588..N-610 is a legacy block whose gaps
are retired). `next_person_id` is 612.

## Transit re-audit fix-all (audit of head ab20e61)

### C-1185, C-1160 and C-1817 reviewed references

ep4 carries about 13 minutes of drift (C-1185 content at 45:45 to 50:07, stamp 58:39). Seth Dillon
(47:14 to 47:37) and Josh Hammer (49:58) are back on C-1185 Mentions and listed in
`config/preflight_gates.json` `mention_grounding.reviewed`. Aaron Wexler N-87 is back on C-1160 (its
anchor A-1102.1 is the Wexler-sent Hamptons invitations; ep3 41:32 "Aaron Wexler sent out some of the
invitations"). The C-1817 reason now cites ep39 47:01 "Tyler Bowyer has a younger brother". The
C-1185 correcting claim (Tucker misattribution) is Wave 2.

### Fan-mail claims pulled and viewer handles retired

Rule: a claim is minted to rescue an orphan person only when the claim stands on its own. Otherwise
the viewer handle is retired. The 12 claims whose Investigative Direction was "None" were pulled
(old ids C-3728..C-3734, C-3737..C-3739, C-3741, C-3742) with their artifact subs (A-2518.2..A-2518.8,
A-2519.3, A-2519.4, A-2519.5, A-2519.7, A-2519.8). Their persons were retired without survivor
(`legacy-N-x`, survives_as null): N-139, N-140, N-141, N-142, N-143, N-146, N-147, N-158, N-160, N-162,
N-163, N-164. These are ep000/BoC-era ids, so they are tombstones and not reusable holes. N-161 Recovery
Recon stays (its claim stands on its own). Meme M-7 in ep9 was spoken by N-158; the occurrence is
re-grounded on the host's reply at 41:58 to 42:08 (Speaker N-3).

Dense renumber (old to new): C-3735 to C-3728, C-3736 to C-3729, C-3740 to C-3730, C-3743 to C-3731,
C-3744 to C-3732, C-3745 to C-3733, C-3746 to C-3734, C-3747 to C-3735; A-2519.6 to A-2519.3.
C-3719..C-3727 and families A-2514..A-2520 keep their ids. Next claim C-3736, next artifact family A-2521.

### Other fixes

- C-3727 names its speaker, Andrew Kolvet N-42, in the Alex Clark interview clip played at 32:47 to 34:22
  (cued at 32:43 "Andrew's response to the Catholic question"); N-42 on Mentions and A-2518.1.
- C-3731 (old C-3743) adds N-166 Xaviaer DuRousseau ("Xavier Daruso" 03:46, "Xavier" 05:39).
- C-3735 (old C-3747) carries Confidence: low, matching A-1424.2.
- Hole-minted ids removed from secondary lines (ep92 N-536, N-569; ep148 N-578). `hole_mint_order` now
  also reads `Existing Nodes Reused` lines.
- `name_annotation_mismatch` requires a surname match for persons (a shared first name alone fails).
- ASR canonical names corrected, ASR spelling kept as alias: N-138 Michael Knowles (Michael Nolles),
  N-95 Brian Mast (Brian Mass), N-83 Abraham Poliak (Abraham Polokoff, Abraham Pollock), N-167 Natasha
  Hausdorff (Natasha Housedorf), N-171 Taylor Lorenz (Taylor Lorent, Taylor Ren).
- N-993 Michael Knowles (ep79) duplicated N-138 once the ASR name was fixed. One person one node:
  N-993 collapses onto N-138 (earliest introduction, ep8); `legacy-N-993` survives_as N-138.

`next_person_id` stays 612.
