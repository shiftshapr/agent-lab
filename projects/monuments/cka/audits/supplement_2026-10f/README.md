# Supplement pass, batch 6 (2026-10-14)

This batch adds missed claims and artifacts to the next 20 lowest-density episodes, which had about 0.37 to 0.43 claims per minute before this pass. It is add-only, follows `../../docs/POLICY.md`, and was written by Claude Sonnet agents, one per episode. Every claim carries a relevance tag. This is the first batch run under the name rules of 2026-10-14.

## Result
| Seq | Candace Ep | Video | Claims before | Added | Claims after |
|---|---|---|---|---|---|
| 5 | 238 | [sreYYcID-QY](https://youtu.be/sreYYcID-QY) | 23 | +85 | 108 |
| 8 | 241 | [UBkFkg4UNY8](https://youtu.be/UBkFkg4UNY8) | 24 | +60 | 84 |
| 16 | 249 | [5autG89PW6w](https://youtu.be/5autG89PW6w) | 24 | +85 | 109 |
| 20 | 253 | [Cq7nj9rxPdo](https://youtu.be/Cq7nj9rxPdo) | 24 | +116 | 140 |
| 23 | 256 | [YFmRH8p5lt0](https://youtu.be/YFmRH8p5lt0) | 25 | +88 | 113 |
| 33 | 266 | [JQjCAsfoXEE](https://youtu.be/JQjCAsfoXEE) | 23 | +67 | 90 |
| 42 | 275 | [DqGNvi36ol8](https://youtu.be/DqGNvi36ol8) | 23 | +60 | 83 |
| 43 | 276 | [Kmt6HgRjckU](https://youtu.be/Kmt6HgRjckU) | 18 | +47 | 65 |
| 56 | 289 | [ZZGWo6oDscc](https://youtu.be/ZZGWo6oDscc) | 21 | +63 | 84 |
| 69 | 302 | [DYD_QHMPwqM](https://youtu.be/DYD_QHMPwqM) | 16 | +84 | 100 |
| 78 | 311 | [5-HUyv9LyMg](https://youtu.be/5-HUyv9LyMg) | 23 | +79 | 102 |
| 83 | 316 | [5m-Wn6Pr5rM](https://youtu.be/5m-Wn6Pr5rM) | 21 | +68 | 89 |
| 91 | 324 | [jsqUIkszZd0](https://youtu.be/jsqUIkszZd0) | 24 | +78 | 102 |
| 94 | 327 | [kaWtDuoY_ns](https://youtu.be/kaWtDuoY_ns) | 26 | +100 | 126 |
| 99 | 333 | [eMtjzXkQrsU](https://youtu.be/eMtjzXkQrsU) | 28 | +74 | 102 |
| 102 | 336 | [KpxIBWkNsSs](https://youtu.be/KpxIBWkNsSs) | 24 | +86 | 110 |
| 121 | 355 | [sKuYLNx3iRo](https://youtu.be/sKuYLNx3iRo) | 24 | +64 | 88 |
| 131 | 365 | [amqTMimDr0A](https://youtu.be/amqTMimDr0A) | 25 | +73 | 98 |
| 139 | 373 | [d7VsbEIWkP8](https://youtu.be/d7VsbEIWkP8) | 24 | +87 | 111 |
| 145 | 380 | [JrhGEm8MGRY](https://youtu.be/JrhGEm8MGRY) | 19 | +66 | 85 |

The batch adds **1530 claims** (C-11916..C-13445) and 108 artifact items. It also adds 28 persons (N-911..N-938), 47 topic/org/place nodes (N-11317..N-11363), 15 memes (M-299..M-313) and 191 meme occurrences. For every episode, the claim, artifact and meme-occurrence counts match the staged files. Per-episode notes are in `coverage_notes/`.

## Name corrections (POLICY §4)
The agents reported each mis-transcription instead of turning it into an alias (`mistranscriptions_reported.md`). This batch adds 86 rules to `config/transcript_name_corrections.json`, and they were applied to 150 transcripts and every matching snippet, quote and line of prose. 42 transcription-error aliases were dropped, for example Kolvet's 13 variants, "Megan Kelly", "Jeremy Boring" and "Barry Weiss".
- **Episode-scoped rules.** The new `[pattern, replacement, [episodes]]` form handles renderings that are real names or ordinary words elsewhere:
  - "Frank Church" → Turek in ep121 only. Frank Church was a real senator.
  - "scientists" → Zionists in ep5 only.
  - "Greg Lori" → Greg Laurie, kept separate from Lori Frantzve.
  - "Mikey McCormick" → McCoy in ep91 only.
  - "Judge Leeman" → Liman in eps 88 and 99.
- **Narrowed after a mistake.** In ep131 the transcript has "Andrew Breitbart" twice. One is Kolvet ("didn't get the email question"). The other is the real Andrew Breitbart ("after Andrew Breitbart died"). The first rule covered both, so the Breitbart node, the Breitbart topic and two claims were wrongly renamed. They were restored, and the rule now matches only the exact Kolvet phrase. The same applies to "Andrew Klavan": the line "is out the gate saying Charlie was terrified of me" is Kolvet, while the Daily Wire meeting attendee stays as transcribed and is flagged for review (C-13141).

## Node fixes
- **N-98 renamed from "Bob Shulman" to Robert Shillman** ("Bob Shillman"). Evidence:
  - The ep23 transcript has "Shillman".
  - The node describes the donor who pulled millions from Charlie and wanted his name off the building.
  - Anadolu Agency, via Bengü Türk, reported that billionaire Shillman cut funding to Kirk after Kirk criticized Israel.
  
  Shulman, Shuman, Schman and Showman are corrected archive-wide. Overrule this if you know otherwise.
- **N-733 Karl Marx (Victor Marx's father).** The "Karl Marx" alias was dropped because it made the gate treat a mention of the philosopher in ep26 as this person. The batch 4 acceptance that rested on that confusion was removed, and the false positive is now accepted with the real reason.
- **Renamed:** Alex Marlow (was Marlo), Marissa Streit (was Strait), and the Lance Twiggs, Timpanogos and Andrew Kolvet topic titles.
- **Duplicates reused:** Daily Wire (N-10900) and Timpanogos Regional Hospital. "Rabbi Shmuley" is merged into "Rabbi Shmuley Boteach".

## Process fixes
- **Ep94 came in after integration.** Its agent finished after the batch was integrated, so it was integrated in a follow-up run. That gave its new nodes ids out of airing order, so batch 6's new node ids were renumbered into airing order.
- **Duplicate meme occurrences.** The meme backfill compared uncorrected staged text with corrected drafts and duplicated 3 occurrences in ep139. They were removed, and the backfill now corrects staged text first.

## Needs your review
| Item | Question | Transcript says | Watch |
|---|---|---|---|
| N-98 Robert Shillman | Confirm the rename from "Bob Shulman" | ep23 transcript: "Shillman" | [▶ ep23 00:34:42](https://youtu.be/YFmRH8p5lt0?t=2082) |
| Ep102 "Nick Fuentes" (3×) | The agent believes these mean Nick Shirley; they are left as transcribed until confirmed | | [▶ ep102 00:24:42](https://youtu.be/KpxIBWkNsSs?t=1482) |
| C-13141 "Andrew" at YWLS | Kolvet or Andrew Klavan? The Daily Wire context makes Klavan plausible | "I believe Andrew Klavan was actually present for that discussion" | [▶ ep131 00:12:34](https://youtu.be/amqTMimDr0A?t=754) |
| Ep69 "Robkea" | Possibly Rob Skiba; unverified | | [▶ ep69 00:05:43](https://youtu.be/DYD_QHMPwqM?t=343) |
| Ep131 "Gary Javitch" | Spelling unverified; no web results | | [▶ ep131 00:20:02](https://youtu.be/amqTMimDr0A?t=1202) |
| Ep5 and ep8 "Calira/Calera Engineering" | Caldera Engineering? The host's spelling varies | | [▶ ep8 00:02:36](https://youtu.be/UBkFkg4UNY8?t=156) |
