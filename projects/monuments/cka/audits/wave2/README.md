# CKA adversarial audit, Wave 2 (main 04fd309)

Wave 2 closes the rest of the Transit full adversarial audit (everything Wave 1 did not cover) plus Transit's N1-N5 follow-ups from the PR 59 re-audit. Transcript-driven only (no video). Staged only: no Neo4j writes, no pack, no BoC promote, no deploy. PR 55 and the BRC-222 2.1.0 re-vendor are untouched.

## Gate results

| Gate | Before (04fd309) | After |
|------|------------------|-------|
| `dia_preflight --monument cka` | P0 0 / P1 88 / P2 6 (46 claim_missing_from_drafts, 39 claim_ts_past_end, 3 duplicate_claim_header, 6 register_related_empty) | P0 0 / P1 0 / P2 0 |
| `hostile_hard_gates --monument cka` | P1 9 (NODE_NOT_IN_LEDGER) / P2 1 (CA_DEBT_CALLOUT) | CLEAR 0 / 0 / 0 |
| `dia_preflight --self-test` | OK | OK |
| BoC preflight | PASS | PASS |
| BRC-222 2.0.0 companion bridges | 9165 | 9193 (isMemberOf 6347, isSupportedBy 2819, contradicts 19, isCorroboratedBy 8) |

CA_DEBT_CALLOUT is accepted in `config/hostile_accepted.json` (the callout is deliberate documentation of carried debt, not a defect).

## Files

All CSVs use CRLF line endings.

| File | What it records |
|------|-----------------|
| `persons_orgs.csv` | Person mints (ep96, ep99), Havas Media org mint, orgs retyped out of the person band, junk rows removed, topic collapses, aliases, N4 rename, persons kept by judgement |
| `renumber_map.csv` | Every old id to new id (org retypes, topic collapses, anchor repoints). No claim was renumbered |
| `related_spray.csv` | Related spray cleanup (N-1207..N-1234 and N-1616, N-2139, N-1089, N-1268, N-1657, N-1115): local rows removed, claim and artifact edges removed, ledger strips, prose rewrites, with the reason for each |
| `mentions_backfill.csv` | Every Mentions add with the transcript evidence (full name, surname or first name, in window or elsewhere in the episode) and the 12 held names that are not in the transcript |
| `quotes.csv` | Spliced or paraphrased quotes replaced with verbatim transcript text (claims, artifacts, memes) |
| `timestamps.csv` | Eps 1-10 drift re-stamps to the transcript marker of the located quote, and MM:SS:xx stamps (ep30, ep134) written as 00:MM:SS |
| `claims.csv` | Restored inscription-only claims, dangling claims defined, junk headers, C-1788 stub, C-3736 correcting claim, C-1626 title, ep34 normalization |
| `ledger.csv` | Ledger fixes (NODE_NOT_IN_LEDGER, baseline ids moved off New lines, Hole-minted wave2 lines) |
| `memes.csv` | Meme timestamps and quote cleanup, N2 (M-7 ep9 dropped), N5 (ep8 MemeLink speakers) |
| `inscription_sync.csv` | Per-episode inscription JSON changes and the canonical `episodes` recompute |

## Items

1. **Preflight residuals and eps 1-10 drift.** 46 inscription-only claims restored verbatim from the inscription (ep149, ep150, ep159). 39 past-end stamps fixed (ep30 and ep134 MM:SS:xx stamps). 3 duplicate headers resolved. The 6 empty-Related register rows were junk rows (N-588, N-589 in ep47; baseline ids N-27, N-28, N-32, N-33 misused in ep96) and were removed. 377 timestamp changes in total; the eps 1-10 residual drift is 0 against the located quotes.
2. **Related spray.** Edges kept only where the claim shares a distinctive token with the topic name (generic words such as Charlie, Kirk, Utah, TPUSA, investigation do not count). The topic's first-introduction episode is kept. In eps 80+ the ids N-1207..N-1234 had been reused as per-episode local ids for different entities; those 445 local rows were removed with their edges. Persons named only in those rows and not already noded are a Wave 3 item.
3. **Spliced quotes.** 11 claims, 20 artifacts (eps 1-10 plus A-2193.1) and 6 meme quotes rewritten verbatim, with " ... " for elisions. Sentences the audit marked to strike were found to be real speech, so they were made verbatim instead of struck.
4. **hostile_hard_gates.** 9 NODE_NOT_IN_LEDGER fixed in the ledgers. CA_DEBT_CALLOUT accepted through config.
5. **Mentions backfill.** 1278 adds, each grounded in the transcript. 12 held (the name appears in the claim text but not in the transcript).
6. **C-1185.** New C-3736 (ep4, 00:45:45) says the speaker is Tucker Carlson and Contradicts C-1185. N-45 dropped from C-1185, A-1107.2 corrected.
7. **ep96 and ep99 persons.** Duplicate check against every person name and alias first. Minted into the lowest free holes in first-introduction order: N-612 Evan Hill, N-617 Cole Allen, N-619 Sarah Sidner, N-622 David Axelrod (ep96); N-623 Harmeet Dhillon, N-624 Lara Trump, N-625 Ian Carroll, N-626 Ryan Reynolds, N-627 Hugh Jackman (ep99). Havas Media is org N-2392. N-293 and N-903 (Aubrey Laitsch spellings) reused in ep96.
8. **inscription/episode_161.json** created.
9. **Pre-existing debt.** C-1788 duplicate stub removed, inscription-only claims restored, dangling C-1335/C-1566/C-1896 defined, junk headers removed, 7 orgs moved out of the person band (N-2385..N-2391), duplicate topics collapsed (N-1643 to N-1151, N-2063 to N-1444, N-1651 to N-1642), and 00:00:00 memes stamped (M-48 ep27 and M-34 ep33 really are at 00:00:00).
10. **Transit N1-N5.** N1 and N3 are checker fixes with tests (see `DIA_PREFLIGHT.md`). N1 exposed no data. N2 drops the M-7 ep9 occurrence. N4 renames N-166 to Xaviaer DuRousseau (aliases Xavier Deruso, Xavier Daruso, Xavier Duso; snippets left as spoken). N5 fills the ep8 MemeLink speakers.

## Next ids

Person N-628 (no free hole below it), topic or org N-2393, claim C-3737, artifact A-2521.
