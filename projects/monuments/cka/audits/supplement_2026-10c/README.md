# Supplement pass, batch 3 (2026-10-14)

This batch adds missed claims and artifacts to the next 20 lowest-density episodes, which had about 0.25 claims per minute before this pass. It is add-only. It follows the method in `../supplement_2026-10/README.md` and the spec in `SUPPLEMENT_SPEC.md`. The agents were Claude Sonnet, one per episode, and every snippet was checked as an exact substring of the transcript. Every new claim carries a `relevance:` tag.

## Result
| Seq | Candace Ep | Video | Claims before | Added | Claims after |
|---|---|---|---|---|---|
| 14 | 247 | [t1YtLS1n8Vs](https://youtu.be/t1YtLS1n8Vs) | 13 | +75 | 88 |
| 29 | 262 | [YaZfwLQ7vrI](https://youtu.be/YaZfwLQ7vrI) | 15 | +67 | 82 |
| 35 | 268 | [SKGUzGHymcI](https://youtu.be/SKGUzGHymcI) | 14 | +88 | 102 |
| 45 | 278 | [6DhWawD4ZiM](https://youtu.be/6DhWawD4ZiM) | 15 | +60 | 75 |
| 54 | 287 | [wcD2khO3rOA](https://youtu.be/wcD2khO3rOA) | 21 | +126 | 147 |
| 62 | 295 | [gG4ZoYUjUc8](https://youtu.be/gG4ZoYUjUc8) | 12 | +65 | 77 |
| 66 | 299 | [Wjul6YV6izo](https://youtu.be/Wjul6YV6izo) | 14 | +59 | 73 |
| 70 | 303 | [mFuno0TuuQQ](https://youtu.be/mFuno0TuuQQ) | 13 | +57 | 70 |
| 73 | 306 | [hWTdXHGQ8R4](https://youtu.be/hWTdXHGQ8R4) | 14 | +72 | 86 |
| 82 | 315 | [SgVcnx4Oh30](https://youtu.be/SgVcnx4Oh30) | 16 | +58 | 74 |
| 88 | 321 | [q1NRQQAYS_Q](https://youtu.be/q1NRQQAYS_Q) | 15 | +72 | 87 |
| 89 | 322 | [ZIH5-V6UPkg](https://youtu.be/ZIH5-V6UPkg) | 13 | +54 | 67 |
| 90 | 323 | [eLgD5yUVbko](https://youtu.be/eLgD5yUVbko) | 17 | +66 | 83 |
| 96 | 330 | [qZ8RWfyuewQ](https://youtu.be/qZ8RWfyuewQ) | 22 | +66 | 88 |
| 122 | 356 | [IqHsl7d2dos](https://youtu.be/IqHsl7d2dos) | 17 | +111 | 128 |
| 126 | 360 | [puuMVxEu5NU](https://youtu.be/puuMVxEu5NU) | 15 | +75 | 90 |
| 132 | 366 | [HZvwbfePe7o](https://youtu.be/HZvwbfePe7o) | 12 | +80 | 92 |
| 138 | 372 | [ChuWo-n49B8](https://youtu.be/ChuWo-n49B8) | 16 | +67 | 83 |
| 142 | 377 | [4JxgOclKzqg](https://youtu.be/4JxgOclKzqg) | 13 | +57 | 70 |
| 160 | 397 | [ms5ChhZegRg](https://youtu.be/ms5ChhZegRg) | 15 | +47 | 62 |

The batch adds **1422 claims** (C-7836..C-9257), artifacts to A-2997, 45 persons (N-807..N-851), 64 topic/org/place nodes (N-11153..N-11216), 42 memes (M-201..M-242) and 212 meme occurrences. For 97 nodes, the introduction moved to the episode where they first appear. Per-episode notes are in `coverage_notes/`.

## Fixes in this batch
- **Meme occurrences (this batch and batch 2).** The integrator ended a register section at the first `###` heading, and staged Meme Registers use `### Occurrence N`. As a result, batch 2's first push and this batch's integration had no meme occurrences. Sections now end only at a heading of the same or higher level. `scripts/supplement_memes_backfill.py` restored 217 occurrences for batch 2 (pushed to that PR) and 212 for this batch. It also filled every empty meme definition: all 242 memes now have one.
- **Register headers.** Ep126 titles its section `# V. Node Register`, so new rows landed after the ledger summary. They were moved into the register. The section matcher now accepts any number prefix.
- **Names (web-checked or from context):**
  - "John Kirraou / Kuraku" is **John Kiriakou**, the CIA torture whistleblower interviewed by Danny Jones.
  - "Ari Schaefer" is **Ari Shaffir**, on the Rogan panel with Mark Normand and Shane Gillis.
  - "Cassie Akiva" is **Kassy Akiva**, a Daily Wire reporter.
  - "Mary Fagan" is **Mary Phagan** (the Leo Frank case).
  - ep122's "David Sprag (James Norman Rawlinson Jr.)" is merged into ep138's **David Sprag**, with both forms kept as aliases.
  - "Corey Comperatore" is reused as the existing N-106, and "George Zenn" is added as an alias of N-42 George Zinn.
- **"DOVE" / "DOAJ" are DOGE.** Ep54 "DOVE" and ep29 "DOAJ" are mis-transcriptions of the host's "internet DOGE", as the earlier claim C-1563 has it. The topic is now N-11171 Kirk "Internet DOGE" Money-Tracing Effort and is introduced in ep29.
- **Renamed:** "Atlantic Aviation" is now "Atlantic Aviation FBO Network", so the person-name gate no longer misreads it.
- **Mentions dropped (ungrounded):** C-7900 MTG; C-8449, C-8450 and C-8451 Jesse Watters; C-8682 Alex Jones; C-9164 Golow; C-9186 Kolvet.
- **Reviewed role references:** "a sitting leader of a foreign country" (Macron), "Ike", "Andrew" and "Justin".
- **Named before intro (accepted):** Kathy Nester appears in C-2769 text (ep94) and Ed Sheeran in C-3458 (ep152). Both were named in earlier immutable claims before their nodes were minted here.
- **Timestamps:** three ep73 claims estimated past the last transcript marker are clamped to 00:51:13.

## Needs your review
| Item | Question | Transcript says | Watch |
|---|---|---|---|
| N-818 "Don Oro" (C-8396) | A TPUSA person in Tampa who allegedly took a call from "Pierre". Web searches found no TPUSA staffer by this name; it may be a mis-transcription. | "Pierre had a phone call with Justin Strife. He also had a phone call uh with Mr. Don Oro of Turning Point USA down in Tampa." | [▶ ep70 00:13:09](https://youtu.be/mFuno0TuuQQ?t=789) |
| C-8379 / C-8380 "Ike Promoter" | Linked to N-748 Ike Perlmutter. This is a guess from context (a Mar-a-Lago fundraising lunch). | "Charlie had taken a meeting down in Florida with Ike Promoter at Mara Lago. It was a a fundraising meeting." | [▶ ep70 00:05:03](https://youtu.be/mFuno0TuuQQ?t=303) |
| C-8598 vs C-3804 | Ep88 says Erika's mother went in for treatment on Sept 8, "per records". Ep84 C-3804 says she was "not in the hospital September 8 through 10". Is this a Contradicts, or a clinic vs hospital distinction? No link has been added yet. | "she went in for a treatment 2 days earlier on September 8th because people sent me records of that." | [▶ ep88 00:39:53](https://youtu.be/q1NRQQAYS_Q?t=2393) |
| C-2193 (existing) vs C-8304 / C-8305 | The earlier pass merged two people: Marina Minas ("the Uber chick") and the part-time employee lured by the fake Zoom. A Qualifies link is proposed for the cross-batch link pass. | "Marina Minas, this is the the Uber chick." … "This employee is part-time. It kind of set up this fake Zoom meeting" | [▶ ep62 00:32:06](https://youtu.be/gG4ZoYUjUc8?t=1926) |
| C-8112, departure 11:43 vs 12:31 | The tip email gives two departure times from Fort Huachuca. The claim is recorded as Qualifies on C-1905. | "with this aircraft leaving at 11:43 a. m. on the 9th." | [▶ ep45 00:47:10](https://youtu.be/6DhWawD4ZiM?t=2830) |
| C-8810, Loomer tweet | The tweet is quoted verbatim, including "Zionist Jewish lawyer". The claim prose is neutral. Keep it as a quote? | "I reported her Zionist Jewish lawyer dropping her ahead of an important deadline in her lawsuit with the Macrons next week." | ep96 |
| N-506 "Justin (TPUSA COO)" | Still pending a merge into N-15 Justin Streiff, as one id-shift pass. | | |
