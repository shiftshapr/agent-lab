# Supplement pass, batch 7: the last 22 episodes (2026-10-14)

This batch completes the supplement pass. Every one of the 161 episodes has now been either filled from a skeleton or supplemented. It is add-only, follows `../../docs/POLICY.md`, was written by Claude Sonnet agents (shared instructions in `AGENT_PROMPT_batch7.md`), and every claim carries a relevance tag.

## Result
| Seq | Candace Ep | Video | Claims before | Added | Claims after |
|---|---|---|---|---|---|
| 1 | special | [_dRaEO47-co](https://youtu.be/_dRaEO47-co) | 11 | +45 | 56 |
| 3 | 236 | [q7f8r-THr84](https://youtu.be/q7f8r-THr84) | 37 | +109 | 146 |
| 6 | 239 | [aDlhjfW6hz8](https://youtu.be/aDlhjfW6hz8) | 26 | +59 | 85 |
| 9 | 242 | [QZWSsq8ZWzw](https://youtu.be/QZWSsq8ZWzw) | 22 | +72 | 94 |
| 10 | 243 | [K5GjF53bfN4](https://youtu.be/K5GjF53bfN4) | 21 | +91 | 112 |
| 11 | 244 | [ZGxnf5cj4Uw](https://youtu.be/ZGxnf5cj4Uw) | 24 | +49 | 73 |
| 18 | 251 | [pc3pxRyNFZk](https://youtu.be/pc3pxRyNFZk) | 37 | +65 | 102 |
| 19 | 252 | [c5BcKF91iec](https://youtu.be/c5BcKF91iec) | 29 | +67 | 96 |
| 47 | 280 | [es7PWdFGoFI](https://youtu.be/es7PWdFGoFI) | 37 | +86 | 123 |
| 55 | 288 | [CMcktj3Egfo](https://youtu.be/CMcktj3Egfo) | 27 | +84 | 111 |
| 59 | 292 | [NIEbqsLAK8g](https://youtu.be/NIEbqsLAK8g) | 26 | +65 | 91 |
| 67 | 300 | [CEF7gQRWYCE](https://youtu.be/CEF7gQRWYCE) | 31 | +72 | 103 |
| 71 | 304 | [4YgrOhhy708](https://youtu.be/4YgrOhhy708) | 25 | +76 | 101 |
| 80 | 313 | [I0OaY6Gryqk](https://youtu.be/I0OaY6Gryqk) | 31 | +64 | 95 |
| 85 | 318 | [7ERqbYElOfs](https://youtu.be/7ERqbYElOfs) | 28 | +100 | 128 |
| 87 | 320 | [rupRLXmSndU](https://youtu.be/rupRLXmSndU) | 28 | +80 | 108 |
| 110 | 344 | [MhakwJxK-Zk](https://youtu.be/MhakwJxK-Zk) | 26 | +82 | 108 |
| 128 | 362 | [N4uM8Jdr410](https://youtu.be/N4uM8Jdr410) | 25 | +85 | 110 |
| 147 | 382 | [HIlPQ-_dcxM](https://youtu.be/HIlPQ-_dcxM) | 39 | +57 | 96 |
| 149 | 385 | [bpXkPHpz9po](https://youtu.be/bpXkPHpz9po) | 27 | +92 | 119 |
| 150 | special | [S07n8TnRT0Q](https://youtu.be/S07n8TnRT0Q) | 20 | +33 | 53 |
| 153 | 388 | [aLJhpxrakCU](https://youtu.be/aLJhpxrakCU) | 28 | +84 | 112 |

The batch adds **1617 claims** (C-13446..C-15062) and 116 artifact items. It also adds 19 persons (N-939..N-957), 48 topic/org/place nodes (N-11364..N-11411), 41 memes (M-314..M-354) and 182 meme occurrences. For every episode, the claim, artifact and meme-occurrence counts match the staged files, and the corrected meme backfill added no duplicates.

## Name corrections
This batch adds 161 rules to `config/transcript_name_corrections.json` (264 in total), drawn from the agents' MISTRANSCRIPTION reports (`mistranscriptions_reported.md`). Before applying them, every episode-scoped rule was checked for its hit count in its own episode. The correction pass changed 66 transcripts and dropped 16 transcription-error aliases.
- **Settled:** "Calira/Calera" is **Caldera Engineering** (confirmed independently by three agents). "Viva Frey" is **Viva Frei**. "Gary Ham" is **Gary Hamrick**. "Wed Makmoud/Machmood" is **Wed Mahmoud**. "Erika Kolfage" is Erika Kirk.
- **Scoped to one episode** because the wrong rendering is a real name elsewhere: "Johnny Depp" → Johnny Yep (ep80), "Frank Church" → Turek (ep128), "Taylor Robinson" → Tyler (ep87), and "Mikey McQuaid" → McCoy (eps 67, 85, 147).

## Needs your review
| Item | Question | Watch |
|---|---|---|
| Existing C-1162 (ep3) | The opening statement attributed to Charlie is spoken by Megyn Kelly. Kirk answers only from 00:53:07. An extraction error, to be corrected in place | [▶ ep3 00:51:10](https://youtu.be/q7f8r-THr84?t=3070) |
| Existing C-1165 (ep3) | The thread is attributed to Loomer, but the host credits a different account and brings in Loomer separately | [▶ ep3 01:01:39](https://youtu.be/q7f8r-THr84?t=3699) |
| Ep11 transcript gaps | About 10:22–24:48 and 35:51–49:14 are missing, and older claims cite text that isn't in the file. Re-fetch, with HappyScribe as a cross-check | [▶ ep11 00:10:22](https://youtu.be/ZGxnf5cj4Uw?t=622) |
| N-416/N-417 "Karashi" | Possibly "Qureshi"; unverified | [▶ ep87 00:06:41](https://youtu.be/rupRLXmSndU?t=401) |
| Schaefer vs Scheper Security | N-336 Greg Schaefer and N-11038 Scheper Security: the same firm? | [▶ ep59 00:11:15](https://youtu.be/NIEbqsLAK8g?t=675) |
| "Arena" or "Irina" Mappin (N-158) | Spelling unresolved; ep150 has both | [▶ ep150 00:05:08](https://youtu.be/S07n8TnRT0Q?t=308) |
