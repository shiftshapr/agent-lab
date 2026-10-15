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

## Part 3b (chunks 79–98: episodes ~54–67, 1,201 claims)
- C-2033 had fallen into the gap left by the C-1489 deletion; it was checked in chunk 79.
- 157 findings went to confirmation: 125 accepted, 30 amended, 2 rejected. Applied: 151 confirmed fixes and 124 minor fixes.
- 29 name rules added, for example:
  - Anthony Aguilar, Arsen Ostrovsky, Audrey Hale, Ben Carollo, Charlamagne tha God, Doug DeGroote, Dr. Alan Wolfelt
  - Erika Frantzve, Farris Wilks, Jonathan Conricus, Laurie Cardoza-Moore, Marc Anthony, Matt Lieb, Mehdi Hasan
  - Michele Bachmann, Otto Busher, Rabbi Michael Barclay, Rabbi Yosef Mizrachi, Samuel Smadja, Shaffer Security
  - Jörg Fassbinder, Helmut Becker

  The matching nodes are renamed, and their transcription aliases dropped.
- Merged (`audits/person_merge_2026-10-15c/id_map.csv`): N-742 "Harley Pasternak" into N-80. The earlier
  "Harley Pastnic" correction had given the two nodes the same name. The pending results for chunks 99–110 were
  remapped through this map, and chunks 111 onward were rebuilt.
- **Held for Daveed:** C-10000's "Marina Medvin" → "Marina Minas". See the Marina item below.

## For Daveed: Marina (N-495)
N-495 is named "Marina (TPUSA CMO)" and carries the aliases Meanes, Medias, Medvin, Minas and Munz. Several
reviewers independently identified her as **Marina Minas**, TPUSA's chief marketing officer, from tpusa.com/team,
Fox 10 Phoenix and the HappyScribe transcript of Ep 297 ("this Marina Minas"). Marina Medvin is a different, real
person: an attorney and commentator. The recommendation is to rename N-495 to Marina Minas and turn the other
spellings into correction rules. The earlier C-2193 ruling is unaffected: that employee is unnamed, and the claim
records Minas separately.

## Part 3c (chunks 99–110: episodes ~67–75, 720 claims)
- 80 findings went to confirmation: 56 accepted, 23 amended, 1 rejected. Applied: 76 confirmed fixes and 75 minor fixes.
- Name rules: Aubrey Laitsch (Lech/Lich/Leach/Leitch; N-553 renamed), Megyn Kelly ("Meghan Kelly"), Jörg Fassbinder
  ("Fastbinder"), Barclay (ep66), Falcone (ep70).
- Held for Daveed: three more Marina Minas changes (C-10121, C-2320, C-2322). See "For Daveed: Marina (N-495)".

## Part 3d (chunks 111–138: episodes ~75–93, 1,680 claims)
- Confirmations: chunks 111–126 had 141 findings (119 accepted, 21 amended, 1 rejected); chunks 127–138 had 91 (68
  accepted, 22 amended, 1 rejected).
- Applied: 226 confirmed fixes and 174 minor fixes.
- Name rules added, for example:
  - Andrew Kolvet ("Colebat"), Dennis Frantzve, Dino Fantegrossi, James Blair (ep76), Otto Busher
  - Father Chad Ripperger, Mikey McCoy ("McQuaid", ep75), Amir Tsarfati, Andrew Piskadlo, Cori Kennedy, Jake Traylor
  - Zachariah Qureshi ("Karashy", which closes the Karashi/Qureshi review item)
  - Robert Bohls ("Bowles", now archive-wide)
- Merged (`audits/person_merge_2026-10-15d/id_map.csv`): N-135 Robert Bohls into N-134 ("Robert Bowles", introduced
  ep12), the same FBI Salt Lake City head. The ep12 named-before-intro exception is no longer needed.
- Held for Daveed: further Marina Minas changes (C-3795, C-2535, C-2536, C-11339).

## Part 3e (chunks 139–150: episodes ~93–101, 720 claims)
- 80 findings went to confirmation: 64 accepted, 14 amended, 2 rejected. Applied: 78 confirmed fixes and 72 minor fixes.
- **Terryl Farnsworth**, CEO of Visual Impulse, TPUSA's A/V contractor. The archive had "Terrell" (241 uses).
  CharlieFiles, IBTimes and other coverage spell it Terryl. N-262 is renamed and the rule covers the whole archive,
  including bare "Terrell" (all 21 transcripts that use it mean him). C-4824 no longer lists him: the claim does not
  refer to him.
- Matt Sarelson ("Slauson"; N-863 renamed), Baron Coleman (ep100's "Baron Cohen"), Caleb Robinson (ep100's "Kayla").

## Part 3f (chunks 151–160: episodes ~101–110, 600 claims)
- 54 findings went to confirmation: 48 accepted, 5 amended, 1 rejected. Applied: 52 confirmed fixes and 43 minor fixes.
- Name rules: Bradley Hansell, Charlie Spiering (N-636 renamed), Richard Smale (N-628 renamed), Raphael Schreiber,
  Andrew Kolvet ("Colvin"), Amir Tsarfati, and "Pierre Delecto" (Romney's account).
- The ep102 correction of "Nick Fuentes" to Nick Shirley (NPR) is applied to that claim only, not as a rule, because
  Nick Fuentes is named correctly throughout the archive.

## Part 3g (chunks 161–194: episodes ~110–137, 2,040 claims)
- Confirmations: chunks 161–178 had 120 findings (103 accepted, 13 amended, 4 rejected); chunks 179–194 had 103 (82
  accepted, 20 amended, 1 rejected).
- Applied: 213 confirmed fixes and 174 minor fixes.
- Name rules: Sergeant Jennifer Faumuina ("Filomena/Felomina"), Jon Bray, James Kaddis, Druski, Tyler Bowyer, Otto
  Busher, Frank Turek ("Cheric"), Matt Bromberg, George Zinn, Bradley Hansell ("Hantel"), Brian Harpole, and Andrew
  Kolvet ("Cole", "Colvett"; ep130 "Andrew Klavan", scoped because Andrew Klavan is a real Daily Wire host).
