# QA after pass 2, 2026-10-19

A fresh 2% sample (278 claims, seed 20261019, whole archive), scored by Opus reviewers with `docs/qa/QA_PROMPT.md`
(the archive's timestamp rule). It was taken after pass 2 (`audits/pass2_2026-10-16/`) and the merge of three duplicate persons.
Report: `qa.md`. Results: `results/`.

**Material-error rate: 0.7% (2 of 278).** Neither error is a name error, the class pass 2 targeted.

| Pass | Material |
|---|---|
| Baseline (2026-10-14) | 14.0% |
| After first remediation | 10.4% |
| After Sonnet verification pass | 5.4% |
| After Opus re-check (2026-10-15) | 1.4% |
| After pass 2, names first (this sample) | 0.7% |

Both errors are fixed:
- C-10792 (ep13): the outlet was the New York Times, not the New York Post. The NYT node (N-10968) is now
  introduced in ep13, through the tip-minted re-introduction ledger, and its id is unchanged.
- C-1557 (ep23): the timestamp was about 40-55 s late. It is now 00:36:19.

The 13 minor findings and 8 relevance disputes were applied on 2026-10-21. One was already fixed (C-3045, Tim Pool), and C-843 also lost its no-op Revises link. The ids in qa.md are pre-renumber.
