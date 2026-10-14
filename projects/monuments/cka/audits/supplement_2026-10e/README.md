# Supplement pass, batch 5 (2026-10-14)

This batch adds missed claims and artifacts to the next 20 lowest-density episodes, which had about 0.32 to 0.36 claims per minute before this pass. It is add-only. It follows the method in `../supplement_2026-10/README.md` and the spec in `SUPPLEMENT_SPEC.md`. The agents were Claude Sonnet, one per episode, and every snippet was checked as an exact substring of the transcript. Every new claim carries a `relevance:` tag.

## Result
| Seq | Candace Ep | Video | Claims before | Added | Claims after |
|---|---|---|---|---|---|
| 2 | 235 | [czVBmqZP6Ss](https://youtu.be/czVBmqZP6Ss) | 23 | +74 | 97 |
| 7 | 240 | [ja26iltROkM](https://youtu.be/ja26iltROkM) | 20 | +54 | 74 |
| 13 | 246 | [adJ4LNGp84I](https://youtu.be/adJ4LNGp84I) | 18 | +66 | 84 |
| 32 | 265 | [7RLtGgkTh9o](https://youtu.be/7RLtGgkTh9o) | 21 | +54 | 75 |
| 38 | 271 | [tB5SXXmd9vU](https://youtu.be/tB5SXXmd9vU) | 22 | +58 | 80 |
| 39 | 272 | [a-e7HC6SeK8](https://youtu.be/a-e7HC6SeK8) | 19 | +82 | 101 |
| 44 | 277 | [t4U7NjnUEgc](https://youtu.be/t4U7NjnUEgc) | 18 | +83 | 101 |
| 61 | 294 | [GY6GWceEqtQ](https://youtu.be/GY6GWceEqtQ) | 24 | +68 | 92 |
| 77 | 310 | [H9p2ZGHAs9A](https://youtu.be/H9p2ZGHAs9A) | 17 | +53 | 70 |
| 79 | 312 | [k8ueJdPFel4](https://youtu.be/k8ueJdPFel4) | 18 | +60 | 78 |
| 81 | 314 | [B9TyCs-6o_0](https://youtu.be/B9TyCs-6o_0) | 19 | +80 | 99 |
| 92 | 325 | [SubDoZWHARo](https://youtu.be/SubDoZWHARo) | 22 | +61 | 83 |
| 93 | 326 | [1mYNOqzAdXs](https://youtu.be/1mYNOqzAdXs) | 20 | +56 | 76 |
| 98 | 332 | [uC_GjKU8rs8](https://youtu.be/uC_GjKU8rs8) | 22 | +69 | 91 |
| 129 | 363 | [OgRyiOAVtWU](https://youtu.be/OgRyiOAVtWU) | 24 | +74 | 98 |
| 135 | 369 | [iB-YtO3UZOg](https://youtu.be/iB-YtO3UZOg) | 18 | +67 | 85 |
| 136 | 370 | [AH1KVKkweUE](https://youtu.be/AH1KVKkweUE) | 18 | +55 | 73 |
| 151 | 386 | [O4Zw3bCALjU](https://youtu.be/O4Zw3bCALjU) | 20 | +47 | 67 |
| 154 | 389 | [NNiCZk1cuzs](https://youtu.be/NNiCZk1cuzs) | 21 | +55 | 76 |
| 155 | 391 | [6XfDqKTdFKg](https://youtu.be/6XfDqKTdFKg) | 20 | +57 | 77 |

The batch adds **1273 claims** (C-10643..C-11915), artifacts to A-3173, 31 persons (N-888..N-918), 48 topic/org/place nodes (N-11269..N-11316) and 27 memes (M-272..M-298). For 71 nodes, the introduction moved to the episode where they first appear. Claim, artifact sub-item and meme occurrence counts match the staged files for every episode. Per-episode notes are in `coverage_notes/`.

## Fixes in this batch
- **Uppercase register headers.** Ep64 (batch 4) and ep154 title their sections `# IV. NODE REGISTER`. The integrator matched headers case-sensitively, so new rows went into separate sections appended at the end. They have been moved into the original registers; no content changed. Header matching is now case-insensitive, and a scan confirms every draft has exactly one Artifact, Node and Claim register the integrator recognizes.
- **Meme backfill:** `supplement_memes_backfill.py` now also maps new-node placeholders, for example a meme speaker, by name.
- **Renamed:** N-130 "Kaye McAney" is now **Kayleigh McEnany**, and N-10435 "Fort Wuka …" is now **Fort Huachuca Erika Kirk Location Investigation**. The old spellings are kept as aliases.
- **Merged:** the meme "Candace Was Right Jar" is merged into M-259 "Candace Owens Was Right Jar".
- **Ledger:** the ep32 `reintro-ep032` tip-mint lines are merged and ordered.
- **Reviewed role references:** "her husband" ×2, "Tyler" ×2, and "as you know, Andrew".
- **Named before intro (accepted):** Miss Noble (C-3005, ep124) and Blake Hariff (C-3550, ep149).

## Needs your review
| Item | Question | Transcript says | Watch |
|---|---|---|---|
| N-913 Ashley Brown Guajardo, N-11303, C-11648..C-11650, A-L2..A-L4 (ep135) | The medical examiner's wife, an NYU professor, is not a public figure. The host shows her furry-costume book-promo video, her bio and her LinkedIn. Everything is attributed, but it is personal material. Keep it as is, tag it tangential, or drop it? | "he's married to someone who encourages, supports, works with, and propagates the culture of furries, and occasionally dresses up as one herself." | [▶ ep135 00:05:07](https://youtu.be/iB-YtO3UZOg?t=307) |
| N-906 Bettina Anderson (ep92, ep93) | The transcript says only "Bettina" ("soon-to-be Trump"). The surname comes from public knowledge (Donald Trump Jr.'s fiancée). | "Erika Kirk flew into Palm Beach because she was attending Bettina's bridal shower which took place on Sunday." | [▶ ep93 00:07:27](https://youtu.be/1mYNOqzAdXs?t=447) |
| N-915 "Bobby Saucelito" (ep151, ep155) | A commentator whose clip the host plays. The spelling is as transcribed and unverified. | "If you were in the trunk, how did you do that? And how would Brian not remember you jumping over the seat to do it?" | [▶ ep151 00:11:11](https://youtu.be/O4Zw3bCALjU?t=671) |
| Existing C-1241 (ep7), C-3505 (ep154) | The earlier pass misattributed a line: in C-1241 a student's AIPAC line is given to Charlie, and in C-3505 Tucker's "maximalist" line is given to the Politico author. Both are proposed as Qualifies in the cross-batch link pass. | | |

## Person duplicates found in the whole-graph scan (one merge pass, id shift)
These are older duplicates, mostly from earlier waves. Two were mine: in batch 2 I renamed N-772 to Bob Coy without seeing N-261, and batch 3 minted N-815 Paul Vallely next to N-459 "Paul Valli".
| Keep | Merge in | Note |
|---|---|---|
| N-15 Justin Streiff | N-506 "Justin (TPUSA COO)" | |
| N-261 Bob Coy | N-772 Bob Coy | |
| N-384 Ian Carroll | N-131 "Ian Carol" | |
| N-817 David Frodsham | N-394 "David Rodsham" | to check |
| N-459 Paul Valli → rename Paul Vallely | N-815 Paul Vallely | |
| N-228 Brandon Tatum | N-58 "Brendan Tatum" | |
| N-289 Eric Bolling | N-72 "Eric Bowling" | |
| N-663 Phil Tourney | N-510 "Phil Turney" | to check spelling |
| N-701 Dr. Philip Goldsberry | N-700 Philip Goldsberry Jr. | possibly father and son; to check |
