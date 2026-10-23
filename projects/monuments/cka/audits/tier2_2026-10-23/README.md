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

## Round 2 (same day)

**Research.** The same research prompt was used, plus `already_have.txt`, the round 1 articles, which could be
cited but weren't fetched again. It covered the next 100 most-raised open questions. Agents found 48 new articles,
all from outlets on the POLICY 11 list (`candidates_round2.md`). Daveed approved all 48, fetched as S-67..S-114,
about 91k words.

**Register.**
- 90 attributed research findings were added to 56 questions.
- 24 reporting conflicts were added to their questions (`conflicts_round2.json`, 40 in all; 16 involve non-core claims).

**Verification.**
- **Extraction:** 6 extraction agents pulled 1,114 verbatim facts.
- **Matching:** they were matched to 1,554 unverified claims.
- **Judging:** 18 judges proposed 88 corroborations and 1 disputed.
- **Confirmation:** 3 confirm agents kept 58. They saw both the court-record rejections and round 1's rejections
  (`rejected_round2.json`). Claims rejected again include:
  - C-3015, the roof-access texts
  - C-8373, the grandfather's rifle
  - C-12052, the Cedar City sequence
  - C-9102, the Vance "lecture"
- **The proposed dispute, C-326, was rejected.** The charging documents say Robinson's mother recognised him and
  Patel says his father did; both can be true.
- **Operator review:** I rejected C-11906, a prediction that a ruling would come around Sept. 1. I also replaced a
  truncated quote for C-12774 and C-12775 (Neff on Owens' theories) with the exact sentence from S-89 para 69.

**Applied.** 57 corroborated.

**Totals now:** 578 corroborated, 38 contradicted-by-record, 53 revised-by-host, 13,805 unverified.
