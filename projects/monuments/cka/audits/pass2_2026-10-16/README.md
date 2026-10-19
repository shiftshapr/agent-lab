# CKA pass 2: second full Opus check, names first (2026-10-16 to 2026-10-19)

The second full verification pass, run after the 2026-10-15 Opus re-check (1.4% material on the QA sample).
It covered all 232 chunks (13,915 claims) and focused on misheard names, which the QA sample showed to be
the main remaining error class.

## Method
- First pass: one Opus reviewer per 60-claim chunk, using `docs/qa/VERIFY_PROMPT.md` with the "Second pass:
  names first" section. Every name that is not a well-known public figure is web-checked.
- Timestamp findings inside the archive's window (content at most ~75s after the timestamp) are dropped before
  the confirm step, so only real timestamp errors are confirmed.
- Confirm: one Opus reviewer per 40 findings decides accept, amend or reject. Name corrections need a source
  the confirmer has checked. A fix the current text already has, or one that only repeats an existing
  correction rule, is rejected.
- Name corrections are made at source in `config/transcript_name_corrections.json`. They are scoped to
  episodes when the wrong form is a real word or name elsewhere.

## Results
- Findings sent to confirm: 487. Of these, 330 were accepted, 86 amended and 71 rejected.
- Fixes applied: 724 in total, 395 confirmed material and 329 minor. That is about 2.8% of claims with a
  material correction. Minor fixes that would have dropped content were held back unless confirmed.
- Many name rules were added (people, places, companies). Examples: Reams, Fink, Soon-Yi, Yrefy, Frank Carni,
  Breining, Samantha Karner, Dan Merrell, No Soup for Knowles, Lake Forest Group.
- Introductions moved earlier, with ids unchanged: Corey Lewandowski to ep19 and Zachariah Qureshi to ep85.

## Files
- `results/`: first-pass findings per chunk.
- `confirmed/wN_confirmed_*.json`: confirm decisions per wave.
- `applied_wN.json`: what was applied per wave.
- `names/`: the person-name audit of all 951 person nodes.

## Follow-ups
- Merge the duplicate person nodes N-570/N-864 (David Hull), N-576/N-820 (Nicole Rothstein) and N-128/N-132
  with `scripts/merge_person_nodes.py`.
- Fresh 2% QA sample to measure the error rate after pass 2.
