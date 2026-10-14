# Supplement pass, batch 2 (2026-10-13)

This batch adds the claims and artifacts the earlier extraction missed for the next 20 lowest-density episodes. It is add-only, uses the same method as batch 1 (`../supplement_2026-10/README.md`), and runs on Claude Sonnet agents. **Every new claim carries a relevance tag** (`relevance:core|context|tangential`, see `config/claim_lenses.json`).

## Result
| Seq | Candace Ep | Video | Claims before | Added | Claims after |
|---|---|---|---|---|---|
| 15 | 248 | [ozWJz2spBcI](https://youtu.be/ozWJz2spBcI) | 14 | +63 | 77 |
| 21 | 254 | [Qt0VHV-POCg](https://youtu.be/Qt0VHV-POCg) | 13 | +40 | 53 |
| 25 | 258 | [Qfwr08Ebczo](https://youtu.be/Qfwr08Ebczo) | 12 | +45 | 57 |
| 31 | 264 | [yAIb-NuUh_U](https://youtu.be/yAIb-NuUh_U) | 13 | +80 | 93 |
| 46 | 279 | [6J6lRZPQ4jk](https://youtu.be/6J6lRZPQ4jk) | 13 | +65 | 78 |
| 51 | 284 | [OEAHy3SsIiI](https://youtu.be/OEAHy3SsIiI) | 14 | +59 | 73 |
| 52 | 285 | [HYn0P-P1wUw](https://youtu.be/HYn0P-P1wUw) | 14 | +102 | 116 |
| 53 | 286 | [zSKrxIUMNqw](https://youtu.be/zSKrxIUMNqw) | 12 | +80 | 92 |
| 63 | 296 | [A39g5oqB_eM](https://youtu.be/A39g5oqB_eM) | 13 | +70 | 83 |
| 75 | 308 | [i8m_6D4QGmk](https://youtu.be/i8m_6D4QGmk) | 16 | +90 | 106 |
| 123 | 357 | [a2bZf4fic10](https://youtu.be/a2bZf4fic10) | 14 | +60 | 74 |
| 124 | 358 | [EtLHqDbxqks](https://youtu.be/EtLHqDbxqks) | 20 | +77 | 97 |
| 127 | 361 | [mLvJqdxS-FY](https://youtu.be/mLvJqdxS-FY) | 16 | +72 | 88 |
| 133 | 367 | [Vu6Y24pqhZs](https://youtu.be/Vu6Y24pqhZs) | 12 | +48 | 60 |
| 134 | 368 | [AoYZel7_cGQ](https://youtu.be/AoYZel7_cGQ) | 13 | +74 | 87 |
| 137 | 371 | [1CFDtD0IgEg](https://youtu.be/1CFDtD0IgEg) | 13 | +61 | 74 |
| 143 | 378 | [9hRcfSrri70](https://youtu.be/9hRcfSrri70) | 11 | +64 | 75 |
| 146 | 381 | [ZkDO-MRLUco](https://youtu.be/ZkDO-MRLUco) | 12 | +94 | 106 |
| 148 | 384 | [FGoeoZxDN1c](https://youtu.be/FGoeoZxDN1c) | 13 | +83 | 96 |
| 156 | 393 | [_Sq5RqP27NY](https://youtu.be/_Sq5RqP27NY) | 13 | +60 | 73 |

The batch adds **1387 claims** (C-6449..C-7835), 37 persons, 57 topic/org/place nodes and 36 memes. For 88 nodes the introduction moved to the episode where they first appear.

## Fixes in this batch
- **Integrator section headers.** Some older drafts use single-`#` section headers (`# IV. Node Register`). The section matcher now accepts `#`–`###`, so new rows land in the existing register instead of a duplicate section.
- **Aliases added:** Mark Amaday, Elizabeth McCoy, James Cadis / Cadis, JFK.
- **Reviewed role references:** "Erika's mother", "the vice president", "Justin" on Erika's own call, "Ye", and "the McCoys (Elizabeth, Mikey)".
- **Dropped:** four ungrounded Mentions.
- **First-naming intros:** Mike Lee is introduced in ep12 (A-1192.2) and Hasan Piker in ep97 (A-2023.1).
- **Name check:** ep31 "Rob Koy" is **Bob Coy** (N-772). He founded Calvary Chapel Fort Lauderdale, which started in Pompano Beach, and was a former Las Vegas entertainment director accused in a 2016 lawsuit. "Rob Koy" is kept as an alias.
- **Rename:** "Wilks Brothers" is now "Wilks Brothers Funding Network", so the gate no longer reads the topic as a person.

## Meme occurrences (fixed after the first push)
The first push of this batch was missing all 217 meme occurrences. The integrator's section matcher stopped at the first `###` heading, and every staged Meme Register uses `### Occurrence N`. `supplement_integrate.py` now ends a section only at a heading of the same or higher level. `supplement_memes_backfill.py` added the occurrences and filled the 36 meme definitions. Claims, artifacts and nodes were not affected: their counts match the staged files.

## Needs your review

### Sensitive attributed allegations (kept, tagged)
| Claim | Tag | Transcript says | Watch |
|---|---|---|---|
| C-7822 Netanyahu "blackmailed all of our politicians" | context | "because he's blackmailed all of our politicians." | [▶ ep156 00:38:44](https://youtu.be/_Sq5RqP27NY?t=2324) |
| C-7817 "Israel was behind 9/11" | tangential | "Israel was behind 911. Everybody knows it." | [▶ ep156 00:35:38](https://youtu.be/_Sq5RqP27NY?t=2138) |
| C-7826 Andrew Wilson drinking / chain smoking | context | "there's like late night stuff of him just like downing whiskey" | [▶ ep156 00:45:44](https://youtu.be/_Sq5RqP27NY?t=2744) |

### Identity
| Claim | Question | Transcript says | Watch |
|---|---|---|---|
| C-7760 "Andrew Cooper" | Probably Andrew Kolvet, mis-transcribed. Left unlinked until you confirm. | "We know it wasn't tongue-in-cheek because Andrew Cooper gave that conversation to Tulsi Gabbard's office." | [▶ ep148 00:53:42](https://youtu.be/FGoeoZxDN1c?t=3222) |
| N-506 "Justin (TPUSA COO)" | Very likely N-15 Justin Streiff. The merge is deferred to a single id-shift pass with any other merges. | | |

### The host revises her own earlier timeline
Ep52 revises the Dairy Queen timing (Revises C-1186). The host moves the stop earlier and raises a time-zone error:
- C-6809: "the Dairy Queen stop because it had to have occurred earlier than we had initially documented." [▶ ep52 00:08:15](https://youtu.be/HYn0P-P1wUw?t=495)
- C-6813: "Maybe it was actually 5:38 p. m. and time zones were wrong." [▶ ep52 00:09:58](https://youtu.be/HYn0P-P1wUw?t=598)
