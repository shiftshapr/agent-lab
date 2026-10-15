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

## For Daveed
- **C-1489 (ep19).** The claim cites Ryan Mata, but he is not named anywhere in the episode's transcript. Two
  reviewers agree. Claims are never deleted, so the choice is to withdraw it (mark it withdrawn, with a note) or to
  re-source it.
