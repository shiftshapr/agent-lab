# Supplement pass, batch 4 (2026-10-14)

This batch adds missed claims and artifacts to the next 20 lowest-density episodes, which had about 0.28 to 0.32 claims per minute before this pass. It is add-only. It follows the method in `../supplement_2026-10/README.md` and the spec in `SUPPLEMENT_SPEC.md`. The agents were Claude Sonnet, one per episode, and every snippet was checked as an exact substring of the transcript. Every new claim carries a `relevance:` tag.

## Result
| Seq | Candace Ep | Video | Claims before | Added | Claims after |
|---|---|---|---|---|---|
| 12 | 245 | [YA1FxrDWNIo](https://youtu.be/YA1FxrDWNIo) | 15 | +66 | 81 |
| 17 | 250 | [2Riv3I7D0Yk](https://youtu.be/2Riv3I7D0Yk) | 22 | +75 | 97 |
| 22 | 255 | [iHav0PPzUz8](https://youtu.be/iHav0PPzUz8) | 19 | +48 | 67 |
| 24 | 257 | [K1tFD7FfoCU](https://youtu.be/K1tFD7FfoCU) | 16 | +66 | 82 |
| 26 | 259 | [LATnak75Si0](https://youtu.be/LATnak75Si0) | 19 | +71 | 90 |
| 27 | 260 | [vwG1juDCQZQ](https://youtu.be/vwG1juDCQZQ) | 21 | +63 | 84 |
| 28 | 261 | [r1PS67aRmcA](https://youtu.be/r1PS67aRmcA) | 16 | +51 | 67 |
| 30 | 263 | [MUA9ebCF4Ow](https://youtu.be/MUA9ebCF4Ow) | 16 | +67 | 83 |
| 37 | 270 | [mKXdKV-OBog](https://youtu.be/mKXdKV-OBog) | 14 | +65 | 79 |
| 58 | 291 | [X92MllIHDzw](https://youtu.be/X92MllIHDzw) | 18 | +83 | 101 |
| 64 | 297 | [QdM9jLwjwLw](https://youtu.be/QdM9jLwjwLw) | 19 | +98 | 117 |
| 68 | 301 | [QRS_hR7NXaQ](https://youtu.be/QRS_hR7NXaQ) | 15 | +48 | 63 |
| 72 | 305 | [ti5Fxrvegno](https://youtu.be/ti5Fxrvegno) | 15 | +79 | 94 |
| 74 | 307 | [1hcjQGgvxUY](https://youtu.be/1hcjQGgvxUY) | 19 | +89 | 108 |
| 76 | 309 | [ZzAT2xijKGQ](https://youtu.be/ZzAT2xijKGQ) | 18 | +72 | 90 |
| 86 | 319 | [UYkXV9mYbT4](https://youtu.be/UYkXV9mYbT4) | 18 | +55 | 73 |
| 97 | 331 | [69A8TzAGHlU](https://youtu.be/69A8TzAGHlU) | 24 | +69 | 93 |
| 140 | 374 | [5zgkrOaCCj4](https://youtu.be/5zgkrOaCCj4) | 17 | +77 | 94 |
| 152 | 387 | [kn1E0scy9Wc](https://youtu.be/kn1E0scy9Wc) | 20 | +90 | 110 |
| 161 | 398 | [0pSAhaAZz1w](https://youtu.be/0pSAhaAZz1w) | 23 | +53 | 76 |

The batch adds **1385 claims** (C-9258..C-10642), artifacts to A-3090, 36 persons (N-852..N-887), 52 topic/org/place nodes (N-11217..N-11268) and 29 memes (M-243..M-271). For 129 nodes, the introduction moved to the episode where they first appear. Claim, artifact sub-item and meme occurrence counts match the staged files for every episode, which confirms the batch 3 integrator fix. Per-episode notes are in `coverage_notes/`.

## Fixes in this batch
- **Duplicates reused, by title merge (`title_merges.json`):**
  - Operation Underground Railroad is the existing N-11167, now renamed to the full name.
  - David "Fraudsham" is N-817 David Frodsham.
  - Andrew "Pascado" is N-816 Andrew Piscatello.
  - "Sofer" Global Ministries is N-10989 Soter Global Ministries.
  - "Daily Wire" is N-10900.
  - "White Walkers Among Us" is M-140.
- **Renamed:** ep26 "APAC" is AIPAC. N-141 "Constantine Kissen" is renamed **Konstantin Kisin**, with the transcribed spellings kept as aliases.
- **Aliases added:**
  - "Bob Shuman" on N-98.
  - "James Braid" on N-155 James Blair, inferred from the White House staff list.
  - "Andrew Zenger" on N-137.
- **Mentions dropped (ungrounded):** C-9965 Trotter, C-10552 Leavitt, C-10631 Vance.
- **Reviewed role references:** "her husband" ×4, "Ben", "Andrew" and "Tyler".
- **Named before intro (accepted):** Justin Bieber (C-7884, C-1706) and Karl Marx (C-9573), both incidental mentions.
- **Link removed:** an ep140 claim had been linked as contradicting C-6699 ("not arrested in a maroon shirt"). The shirt in ep140 is the one Robinson changed into, not a maroon one, so the link was dropped before integration.

## Needs your review
| Item | Question | Transcript says | Watch |
|---|---|---|---|
| N-876 "Frank Carney" (C-10311) | Is this the TPUSA general counsel N-505 "Frank"? A web search found no public record linking a Frank Carney to TPUSA. Kept separate for now. | "The FBI was on the phone with Justin Strife, Frank Carney, and they were apparently speaking to the feds that day about whether or not I had recorded the footage." | [▶ ep86 00:08:17](https://youtu.be/UYkXV9mYbT4?t=497) |
| N-504 "Marina (TPUSA CMO)" | The aliases mix Marina Minas/Meanes (the TPUSA staffer) with Marina Medvin, an attorney and commentator. Here the host herself says "Marina, the COO" and "Marina Medvin". Is this one person or two? | "making informed decisions alongside Stacie Sheridan and this Marina Medvin" | [▶ ep64 00:58:47](https://youtu.be/QdM9jLwjwLw?t=3527) |
| Harpole's lawyer (C-10414) | The host says "Matt Slauson", and later "Matt Christiansen". Only Slauson was minted. | "this lawyer, Matt Slauson, the one who speaks like he has helium." | [▶ ep97 01:08:34](https://youtu.be/69A8TzAGHlU?t=4114) |
| Sept 8 clinic (C-10031, C-10287) | New detail for the open question C-8598 vs C-3804: Charlie took Erika's mother to a Lyme clinic on Sept 8, at 10:45 a.m. per ep76. Clinic vs hospital may settle the conflict. | "on September 8th … Charlie took Erika's mother for a treatment for Lyme disease at a clinic. I have the address, the name of the clinic." | [▶ ep68 00:28:00](https://youtu.be/QRS_hR7NXaQ?t=1680) · [▶ ep76 00:38:58](https://youtu.be/ZzAT2xijKGQ?t=2338) |
| Bowyer in Romania (C-10254 area) | Ep76 says 2010 and ep54 (C-8150) says 2011. No link was added. | "the Black Sea Rotational Force in Constanta, Romania, is being led by Erika's cousin, Lieutenant Colonel Dennis Fronkvey." | [▶ ep76 00:18:38](https://youtu.be/ZzAT2xijKGQ?t=1118) |
| C-10168 | A sensitive family assertion, recorded as the host's claim: "Stacy Sheridan is not Erika's real mom." Keep it? | "But Stacy Sheridan is not Erika's real mom. Lori is Erika's real mother." | [▶ ep74 00:19:48](https://youtu.be/1hcjQGgvxUY?t=1188) |

## Deferred person merges (one id-shift pass)
- N-506 "Justin (TPUSA COO)" → N-15 Justin Streiff
- N-131 "Ian Carol" → N-384 Ian Carroll
- N-394 "David Rodsham" → N-817 David Frodsham (to be checked)
