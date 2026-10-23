# Tier 2 reporting (ROADMAP 4.1 / 4.5) (2026-10-23)

**Research.** 4 Opus agents searched reputable reporting (POLICY 11 Tier 2) for the 100 most-raised open
questions (`PROMPT_research.md`). They read every page they cite and saved nothing. They found 62 articles for
66 questions (`candidates.md`). Daveed approved the 52 from outlets on the POLICY 11 list and dropped 10 borderline
ones: Newsweek, Euronews, JTA, two public-radio stations, and PolitiFact via WRAL.

**Sources.** S-15..S-66 (stream `tier2-reporting`) are fetched privately with `fetch.py`, about 99k words. The repo
keeps the manifest and short quotes only.

**Register.**
- 79 research findings were added to 55 questions as attributed "Reporting (outlet, date, S-id)" notes.
- 32 conflicts between the reporting and a core claim were added to the claim's question
  (`conflicts.json`, 54 in all). The 22 on non-core claims are listed there only.
- No status changes: reporting alone does not answer a question.

**Verification.**
- **Extraction:** 8 Opus agents pulled 1,232 facts with verbatim quotes, each tagged `reported`, `attributed` or
  `unconfirmed`. All quotes were checked against the page text.
- **Matching:** 1,906 unverified claims were matched by TF-IDF.
- **Judging:** 22 judges proposed 192 corroborations (0 disputed) and flagged 54 conflicts (`PROMPT_judge.md`).
- **Confirmation:** 5 confirm agents (`PROMPT_confirm.md`) kept 161. They saw the earlier court-record rejections:
  for example C-3013 and C-3015, the roof-access texts, which the record shows Dan Flood sent. On operator review I
  rejected two more (C-11019, C-12322) whose corroboration covered only a detail.

**Applied.** 159 claims are now `corroborated` with Tier 2 evidence (`tier2_reported` or `tier2_attributed`). Most
confirm what a named person said (Harpole, Turek, Erika Kirk, Brooksby, Netanyahu, Kolvet) or what filings and
officials state.

**Totals now:** 521 corroborated, 38 contradicted-by-record, 53 revised-by-host, 13,862 unverified.

**Rules applied.**
- Tier 2 never sets `contradicted-by-record`.
- `unconfirmed` facts never corroborate.
- Reporting that only says the host is wrong goes to the register, not to a status.
- The Twiggs–Robinson relationship claim (C-980) stays unverified.

**Not reachable.** AP, Reuters, NYT, WSJ and CNN's own sites blocked the research agents. Where possible, their
stories were cited through syndicated copies on station or newspaper sites; the `outlet` field marks each.
