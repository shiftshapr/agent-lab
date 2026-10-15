# QA after the full verification pass, 2026-10-15

A fresh 2% sample (278 claims, seed 1015, whole archive), scored by Opus reviewers with `docs/qa/QA_PROMPT.md`.
Report: `qa.md`. Results: `results/`.

**Material-error rate: 5.4% (15 of 278).** It was 14.0% at baseline and 10.4% after the first remediation round,
so the 2% target is still not met. Errors: person 6 (mostly mis-transcribed names), timestamp 5 (most within about
15 seconds of the limit), attribution 3, accuracy 3.

**Why the pass did not reach 2%.** The verification pass's first reviewers (Sonnet) had seen all 15 claims. They
marked 14 as ok or minor, and only C-2510 as material. The remaining errors are the kind Opus catches and Sonnet
misses: speaker changes marked only by `>>`, details a claim adds, and names Sonnet could not resolve.

## Fixed here (`applied.json`)
- All 15 material findings, corrected as the reviewers proposed after checking the transcript. Two were checked
  further. **C-14762**: the three-hour Shawn Ryan interview was Brian Harpole's (SRS #254, Newsweek, SLTrib), not
  Frank Turek's. **C-5533**: the Rob McCoy line follows a `>>` speaker change, and the speaker refers to "my show",
  so it is Baron Coleman's.
- Name rules: Eric Moutsos ("Mutosos"; N-62 renamed), Sara Sidner ("Sarah"; N-371 renamed), Dana Loesch ("Dana
  Lash", now archive-wide, with the plural), Johnnie Moore ("Johnny", now archive-wide), Dino Fantegrossi ("Fonte
  Grassi"), John Kiriakou ("Kirraou", "Kuraku", "Kirao"; N-831's mis-transcription aliases dropped), and Charlie
  Kirk (ep76's "Todd Chris podcast").

## Follow-ups
- `inscription/episode_*_transcript.txt` (20 legacy files) and `canonical/memes.json` are outside
  `apply_name_corrections.py`, so old spellings can survive there. memes.json was fixed by hand for Johnnie Moore.
- Remaining "(transcribed X)" notes in drafts (e.g. ep142 "Netor", "Golo") should be checked against the ruling.
- Unresolved names: "Devante West" (C-9058), "Maggie Wagner" (C-6920), "Sprag/Sprague" (N-817).
- 26 minor and 13 relevance findings are recorded in `qa.md` and not applied.
