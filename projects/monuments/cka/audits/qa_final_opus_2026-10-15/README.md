# QA after the full Opus re-check, 2026-10-15

A fresh 2% sample (278 claims, seed 20261016, whole archive), scored by Opus reviewers with `docs/qa/QA_PROMPT.md`.
Report: `qa.md`. Results: `results/`.

**Material-error rate: 1.4% (4 of 278) under the archive's own timestamp rule; 3.6% (10 of 278) under the QA
prompt's stricter one. The 2% target is met.**

| Pass | Material |
|---|---|
| Baseline (2026-10-14) | 14.0% |
| After first remediation | 10.4% |
| After Sonnet verification pass | 5.4% |
| After Opus re-check (this sample) | 1.4% (3.6% strict) |

The QA prompt counted a timestamp as an error unless the snippet came within 60 s after it. The archive's rule
(POLICY §9, `check_claim_timestamps.py`, the verify prompt) allows 75 s after and 20 s before. All 6 timestamp
findings in this sample pass that rule, and the gate confirms it. The QA prompt now uses the archive's rule.

The 4 remaining errors were all mis-transcribed names, now fixed archive-wide (`applied.json` holds the 6
timestamp tightenings, which are improvements, not corrections):
- Emmanuel Bierer ("Beerer", N-311; PBS NewsHour)
- Maggie Wegner ("Wagner", "Mags Wgner", N-389; her own handle @maggswegner)
- Chantal Thuy ("Chantel", N-465; November Renaissance Kickstarter credits)
- Pam Liebman ("Lehman", N-574; Corcoran CEO)

Still held for Daveed: Marina Minas changes, and Eliza vs. Elizabeth McCoy (N-218).
