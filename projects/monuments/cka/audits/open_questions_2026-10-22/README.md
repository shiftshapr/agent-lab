# ROADMAP 4.3: open-questions register (2026-10-22)

**Result.** `ledger/open_questions.json` (master) and `ledger/open_questions.md` (by topic) hold 1,317 questions:
1,213 open, 82 partly answered, 22 answered. Every one of the 4,888 core claims is linked to 1–3 questions through a
new `Open Questions:` line in the episode JSON (after `Investigative Direction`) and `open_questions` in the
inscription. 9,586 non-core claims are not linked yet.

**Each question has:**
- a neutral question;
- a topic;
- what is known, citing S-ids (records) and C-ids (claims; the host's claims are not evidence);
- what would settle it;
- a status (`answered` or `partly-answered` only when an S-id settles it);
- evidence ids;
- the claims that raise it;
- the claims that ask for or relay tips;
- first and last raised (episode dates).

**Method.**
- **Drafting.** 25 Opus reviewers each read ~200 core claims in airing order, with each claim's Investigative
  Direction and any verification note (`PROMPT_draft.md`). They drafted 1,782 questions and mapped every claim.
  Coverage was checked by script.
- **Merging.** `merge_prep.py` grouped near-duplicate questions across packs (TF-IDF ≥ 0.5, union-find): 232 groups
  covering 977 questions. 9 Opus reviewers merged only those asking about the same concrete matter
  (`PROMPT_merge.md`): 225 merges absorbed 690 questions.
- **Numbering.** `assemble.py` numbered the questions Q-1..Q-1317 in order of first raising. `provenance.json` maps
  each Q-id to the drafted questions it came from.

**Tooling.**
- `scripts/questions/apply_register.py` syncs the register into the episode JSON and the inscriptions, fills the
  dates, renders the Markdown and reports any core claim without a question. `--strict` exits 1 on any.
- It runs in finalize.
- The daily RUNBOOK has a new step: link each new core claim to existing questions, or add one, with `--add FILE`.
- `cka_source.py check` validates the `Open Questions:` id format.

**Largest questions (claims):**
- Q-6, donor and pro-Israel pressure on Kirk (62);
- Q-212, Mikey McCoy's calls (60);
- Q-21, whether anyone besides Robinson took part (49);
- Q-63, removal of the cameras and SD cards (46);
- Q-34, how Robinson's surrender came about (45, partly answered).

**For review (sensitive allegations, phrased as basis questions).** Q-509 (the misconduct allegation against Tyler
Bowyer), Q-1190 (the Erika Kirk modeling-agency allegation) and Q-1289 (TPUSA staff records) restate what the host
alleges as neutral questions about the basis. They link only claims already in the archive. Daveed may want them
reworded or hidden from the public register.

**Limits.**
- **Merging was keyword-gated.** Duplicates worded very differently may remain; the daily step and later
  consolidation will catch more.
- **Status is as of today's record (S-1..S-12).**
