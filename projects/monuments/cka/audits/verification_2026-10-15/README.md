# Full verification pass (ROADMAP 2.5), started 2026-10-15

Decided by Daveed on 2026-10-15: re-check every claim against its transcript, because sampling put the archive's
material-error rate at about 10% (QA round 2: 10.4%, 29 of 278), against a target under 2%.

## Method
1. `scripts/qa/verify_pack.py` puts all 13,916 claims into 232 chunks of 60, in airing order. Each claim comes with
   its transcript window and the episode's person roster. Sonnet reviewers follow `docs/qa/VERIFY_PROMPT.md`, using
   the five QA checks, and propose structured fixes. A name fix needs a checked source.
2. `scripts/qa/confirm_pack.py` collects every material finding and every name fix. Opus reviewers follow
   `docs/qa/CONFIRM_PROMPT.md` and accept, amend or reject each one. They verify names themselves, and keep a person
   whom a claim clearly refers to without naming.
3. `scripts/qa/apply_fixes.py` applies the confirmed fixes. It also applies minor-only fixes (claim wording, title,
   relevance) when they keep every number, capitalised name and quote of the original; otherwise it skips them.
4. Confirmed name fixes become rules in `config/transcript_name_corrections.json`. A rule covers the whole archive
   for distinctive misspellings and is scoped to episodes for common words; each was checked for hits before applying.

## Part 1 (chunks 1–40: episodes 1–~29, 2,400 claims)
- 281 material findings (11.7%) went to confirmation, plus 10 name-only fixes: 231 accepted, 57 amended, 3 rejected.
- Applied: 280 confirmed fixes and 247 minor fixes. Skipped: 71 minor fixes, because the content check flagged them.
- 29 name rules added, for example Irina Mappin (confirmed three times, including by John Mappin's own post on X),
  Shaner Broderick, Andrew Zenger, Judge Tony Graf, Michael Burt, Robert Bohls, Michael Knowles, Jack Posobiec,
  Lila Rose, Deirdre Amaro and Andreessen Horowitz.
- Structural fixes:
  - **Duplicate people merged** (`audits/person_merge_2026-10-15/id_map.csv`):
    - N-181 "Derek Maxwell" was the ep18 transcript's mishearing of Derek Maxfield. Merged into N-94.
    - N-101 "Charlie Skyler" was the host's slip ("Charlie, I mean Charlie Skyler"). Merged into the producer
      Skyler, N-68.
  - **Ep18:** the transcript's "Ghislaine Maxwell" was Shirlene Maxfield. The Ghislaine Maxwell node (N-47) is
    removed from ep18.
  - **Accepted early namings:** Shirlene Maxfield (named in ep18, introduced ep22) and Robert Bohls (named in ep12,
    introduced ep13) are recorded in `config/preflight_gates.json` rather than moving their introductions.
- **Ep11:** 9 of the 11 baselined timestamps are now corrected; the reviewers used HappyScribe and YouTube captions
  to cover our transcript's gaps.

## Deleted claims
- **C-1489 (ep19), deleted 2026-10-15 (ruled by Daveed).** It was a placeholder ("Host discusses Ryan Mata in
  episode comment-thread context (register anchor)") at 52:00–53:00. Neither "Matta" nor "Mata" appears anywhere
  in ep19, and that segment is viewer comments. Daveed checked the video. N-190 Ryan Matta keeps its id; his
  ep19 register description is corrected, since he is first named in ep34.

## Part 2 (chunks 41–68: episodes ~29–47, 1,680 claims)
- Wave 3 (chunks 41–52) was checked before the part 1 merge renumbered ids. Its results were remapped through
  `audits/person_merge_2026-10-15/id_map.csv` before confirmation. Chunks 53 onward were rebuilt from the merged drafts.
- Confirmations: wave 3 had 97 findings (76 accepted, 20 amended, 1 rejected); wave 4 had 115 (94 accepted, 20
  amended, 1 rejected).
- Applied: 206 confirmed fixes and 153 minor fixes. 37 minor fixes were skipped by the content check.
- 23 name rules added, for example:
  - Lara Trump, Shauni Rae Kerkhoff, J. Warner Wallace, Anthony Iglesias, Doug DeAndrea, Jeffrey Zizz
  - Allie Beth Stuckey, Losee Center, Arynne Wexler, T.W. Lewis, Shawn Ryan, Satys, Jean-Michel Trogneux
  - Tom Clare, Bob Evnen, Ashley Rindsberg, Hervé Hoppenot, Greg Shaffer, Andrew Sypher

  Greg Shaffer closes the open Schaefer/Scheper review item. The matching person and topic nodes are renamed, and
  the transcription aliases ("Andrew Cipher", "Greg Shafer") are dropped.
- Accepted early namings: Jean-Michel Trogneux (named ep35, introduced ep38). Two claims citing "her husband"
  (George, N-30) are recorded as reviewed in the grounding gate.
- The two Kerkhoff claims (C-1655, C-1656) attribute her identification to the host's sources; neither says she is a
  suspect.

## Part 3a (chunks 69–78: episodes ~47–54, 600 claims)
- 53 findings went to confirmation: 46 accepted, 7 amended. Applied: 53 confirmed fixes and 64 minor fixes.
- Name rules: Andrew Kolvet ("Andrew Colberg"), Guinta, Harpole ("Herpolsheimer", ep54 only), Hunter Kozak
  ("Hunter Cosgrove"), Larry Guinta, Mark Amodei, Thomas Burt (Duncan Aviation).
- Duplicates merged (`audits/person_merge_2026-10-15b/id_map.csv`): N-362 "Andrew Colberg" into N-14 Andrew Kolvet,
  and N-372 "Hunter Cosgrove" into N-328 Hunter Kozak. The chunks not yet verified were rebuilt from the merged drafts.
