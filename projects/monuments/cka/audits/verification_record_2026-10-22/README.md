# ROADMAP 4.5: claims checked against the record (2026-10-22)

**Sources.** Every Tier 1 text source fetched in 4.1 (S-1..S-12):
- the charging Information;
- the preliminary hearing (five days, the closing arguments and the bindover ruling);
- the contempt hearing;
- two County Attorney press releases;
- the charging press conference;
- the UVU After-Action Report.

The ADS-B archive (S-13) is not used yet. The originals stay private in `~/agent-lab-data/cka_sources`.

**Facts.** `chunk.py` split the texts into 38 packs of about 11,000 words. 30 Opus reviewers pulled 4,046 checkable
facts from them (`PROMPT_extract.md`). Each fact has:
- its source id and location (timestamp or page);
- its speaker and kind (testimony, exhibit, ruling, report finding, official statement, charging allegation or
  argument);
- a verbatim quote.

`validate.py` confirmed that every quote appears word for word in its source (0 failures). One-word answers keep the
question asked just before them.

**Matching.** `match.py` compared every claim against the facts by TF-IDF.
- 3,634 claims about the case were kept: those scoring at least 0.25, or at least 0.15 with a case keyword.
- Each kept claim got its top 8 facts.

**Judging.** 41 Opus reviewers read every claim against its facts (`PROMPT_judge.md`). They proposed 431 statuses:
342 corroborated, 78 disputed and 11 contradicted. Every other claim was `none`: opinion, theory, or not covered by
the record.

**Confirmation.** 8 Opus reviewers checked all 431 against POLICY 11 strictly (`PROMPT_confirm.md`):
- Attorney argument never corroborates a fact.
- A charging allegation corroborates only a claim about what was charged or quoted.
- The record's silence is never a contradiction.
- `disputed` needs two record sources in conflict.

The result: **320 corroborated, 33 contradicted-by-record, 0 disputed, 78 rejected** (`rejected.json` gives the
reasons). No proposed `disputed` survived. In every case, either only one side was in the record, or the other side
was argument or allegation. Those became `contradicted-by-record` where testimony, an exhibit, a ruling or a report
finding settles the point, and were rejected otherwise.

**Applied.** `scripts/verification/apply_record.py` sets `Verification:` and `Verification Evidence:` (the S-ids)
through the JSON source.
- The master is `ledger/verification_record.json`: for each claim, the evidence with location, kind, speaker,
  fact and quote, plus a one-sentence note.
- `ledger/verification_record.md` is the review copy.
- One claim, C-11509, keeps `revised-by-host`, because the host corrected herself in the same episode.
- Totals now: 320 corroborated, 32 contradicted-by-record, 53 revised-by-host, 14,069 unverified.
- `apply_record.py` now runs in the daily finalize step, before `derive_status.py`.

**What the contradictions are about.** Most are the host saying one of the following:
- Robinson never set foot on campus;
- Kirk got no first aid;
- there was no exit wound;
- the screwdriver is not in evidence;
- the rifle was never shown to have been fired;
- Robinson was not wearing maroon at his arrest.

In each case sworn testimony or the bindover ruling says otherwise.

The first-aid contradictions rest on Agent Hull's testimony, and Hull was not an eyewitness. Daveed may want those
four (C-1971, C-2364, C-3524, C-10954) held for review.

**Limits.**
- **Recall is bounded by the matcher.** A reviewer could cite only the 8 facts matched to a claim, and several
  reviewers noted a clear record fact attached to a neighbouring claim instead. A second pass with wider candidates,
  or one that propagates verdicts to near-duplicate claims, would raise coverage.
- **Rev mislabels speakers.** The facts name the real speaker where the context shows it (e.g. Officer Bagley, whom
  Rev labels "Richard Novak").
- **Not yet done:** the ADS-B traces, Tier 2 reporting, and the open-questions register (4.3) that 4.5's
  done-condition needs for the claims still `unverified`.

## Wider-recall pass (same day)

**Candidates.** `wide_build.py` re-matched 3,566 claims about the case that were still unverified, skipping claims
that open with an opinion verb. Each claim got up to 20 facts:
- its first-pass 8;
- the next-ranked facts (TF-IDF ≥ 0.12);
- the evidence of up to 3 already-verified claims with similar wording (cosine ≥ 0.3), for 251 claims.

**Judging.** 48 Opus reviewers worked under a stricter prompt that already applies POLICY 11's `disputed` rule
(`PROMPT_judge_wide.md`). They proposed 79 statuses: 64 corroborated and 15 contradicted. 38 of the 79 were claims the
first confirm pass had rejected.

**Confirmation.** 4 Opus reviewers checked all 79 (`PROMPT_confirm_wide.md`). Each item showed the earlier rejection
reason, which could be overturned only if the newly cited facts answered it. The result: 33 corroborated,
5 contradicted-by-record, 41 rejected (`rejected_wide.json`). On operator review I also rejected C-12360, whose
corroboration rested on the record's silence.

**Applied.** 36 new statuses. One more claim keeps `revised-by-host`. Totals now: **351 corroborated,
37 contradicted-by-record**, 53 revised-by-host, 14,033 unverified.

Yield was about 1 in 100 claims re-judged. The remaining unverified claims about the case are mostly opinion, theory,
or matters the record does not cover, so they belong in the open-questions register (4.3).
