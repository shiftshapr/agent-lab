# Opus re-check of the whole archive, 2026-10-15

Why: after the Sonnet verification pass, a fresh 2% QA sample still showed 5.4% material errors, and the Sonnet
reviewers had passed 14 of those 15 (`audits/qa_final_2026-10-15/`). Daveed chose a full re-check with Opus as the
first reviewer.

Pipeline (same as the verification pass, with Opus throughout):
- `scripts/qa/verify_pack.py` builds 232 chunks of 60 claims. `docs/qa/VERIFY_PROMPT.md` gained a "Common misses"
  section (`>>` speaker changes, added details, who "you" is, reported content stated as fact) and the rule that the
  host (N-3) is optional in Mentions.
- Findings that only add or remove N-3 are dropped before confirmation.
- A second Opus reviewer confirms every material finding and name fix (`confirmed/`), then
  `scripts/qa/apply_fixes.py` applies them with content-preserving minor fixes (`applied_w*.json`).
- Marina Minas changes and the Eliza/Elizabeth McCoy (N-218) question stay held for Daveed.

## Waves 1-7 (chunks 1-112, about 6,700 claims)
- Material findings sent to confirmation: 54, 34, 64, 59, 60, 51, 49 (about 5-6 per 100 claims). Rejected about 3%.
- Most common: Mentions listing someone the claim does not name (or missing someone it does), host reports stated as
  fact, a guest's or clip's words given to the host (or the reverse), and timestamps more than 20 s late.
- Name rules added: Frantzve, Milgrim, Lischinsky, Debra Lea (N-140 renamed), Erica Mindel, Sara Schmachtenberger,
  Nate Carlisle (N-220), Kenzie Kinney, Jeffrey Masson, Elle Reeve, Taylor Lorenz, George Zinn, Judge Jan Jurden,
  Eyal Yakoby, Panguitch, Phil Tourney, Laitsch, Erika Kirk ("Erica Kirk"), Kolvet ("Kolbet", "Colberg"), and
  ep37's "Kittis' lawyer" (Candace's).
- Preflight exceptions: named-before-intro for N-822 (ep34) and N-453 (ep43); reviewed by-role mentions for
  C-1819, C-5079 and C-8232.
- C-14209..C-14212 (ep59): the drone lines are Gary Melton's (Paramount Tactical), not Kolvet's. N-617 is introduced
  in ep100, so he is named in the claims but not yet on their Mentions lines.

## Waves 8-14 (chunks 113-232, about 7,200 claims)
- Material findings sent to confirmation: 60, 50, 84, 57, 51, 56, 40. Confirmers rejected about 5%, mostly fixes
  that re-applied an existing name rule.
- Name rules added: Terryl ("Tarro"), Jake Hoffman (N-580, was "AJ Copp"), Laura Ingraham / Ingraham Angle (now
  archive-wide), Norma Jean and Jimmy Ates, Yrefy ("Wi-Refi"), Bagur (N-398), Frédéric Vaglio, Daniel Beaulieu, Karl
  Marx (ep91), Carrie Prejean Boller (N-555), Ryan Rippeon (N-623; mis-transcription aliases dropped), Druski, Ed
  Gallrein, Richard Smale, Christoph Schweizer, H. Duane Anderson, Hansell (ep118), Mikey McCoy ("McCormick"),
  Panguitch, Laitsch (eps 96-97), Frank Turek ("Frank Church", eps 127-129), Beau Mason, Judge Tony Graf, Deirdre
  Amaro, Jon Bray, Allan Robertson, Gordon Margulis, Mell Stewart (ep130), Irina Mappin, Goldsberry, Claire Guinan
  (N-756), DeGroote, Jeremy Boreing.
- Claim-level name fixes (no rule, because the wrong form is a real name elsewhere): Markwayne Mullin (C-3932,
  "Mark Meadows"), Nick Shirley (C-2561, "Nick Searcy"), Andrew Kolvet (C-7760, "Andrew Cooper").
- Preflight: reviewed by-role mentions for C-12849, C-2744, C-4603 (the confirmer had picked N-70 for "the
  governor"; corrected to N-41 Spencer Cox).
- Held for Daveed: every Marina Minas change (C-2320, C-2322, C-2535, C-2536, C-3145, C-3795,
  C-9059, C-10121) and Eliza/Elizabeth McCoy (N-218).

## Follow-ups noted by reviewers
- ep70: N-313 (Pierre Falcone, arms dealer) is attached to a different "Pierre" (a Catholic near Tampa).
- Unresolved names: Joshua Harrelson, Jesse Kege, Emmanuel Beerer, Robby Hild, Mitch Manley, Madison Brandford.
