# Phase 5.1: the host against herself (2026-10-21)

**Candidates.** `candidates.py` produced the candidate pairs.
- Each pair is two of the host's own claims, in different episodes, sharing a specific person or topic (Charlie Kirk,
  Erika Kirk, the host herself and TPUSA are excluded as too broad).
- They are compared by TF-IDF cosine similarity: at least 0.4 for the top 2 earlier matches per claim, and a lower bar
  with 5 matches for claims with correction cues ("misspoke", "correction", "actually", …).
- The result: 1,458 pairs, 153 of them driven by cues.

**Judging.** 20 Opus reviewers judged every pair (`judged_*.json`): 1,030 supports, 362 none, 54 revises,
10 qualifies, 2 contradicts.

**Confirmation.** A second Opus reviewer checked all 66 non-trivial links against the transcripts
(`confirmed.json`): 34 accepted, 1 amended, 31 rejected. The usual reasons for rejection:
- the earlier claim was already hedged;
- an added source, not a replacement;
- a different event;
- relayed material rather than her own claim;
- rounding or loose wording.

**Applied.** The 35 confirmed links were added to the later claims through the JSON source: 31 `Revises` and
4 `Qualifies` (`accepted.json` has each delta). The 1,030 `supports` judgements are not applied here, because a
same-host repeat is not corroboration (3.3).

**Ledger.** `ledger/then_vs_now.json` and `.md` (ROADMAP 5.3) list every Revises, Contradicts and Qualifies link
(282; 87 are the host against herself) with both clips, dates and the delta, and a `review` field for Daveed.
`scripts/ledger/export_then_vs_now.py` regenerates it in the daily finalize step and keeps the review state.

Two accepted links are new developments rather than corrections: #24 (Marx replied later) and #55 (her team found
the hotel). Daveed may want them kept off the promoted ledger.
