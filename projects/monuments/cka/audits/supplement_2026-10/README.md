# Supplement pass, batch 1 (2026-10-13)

The 20 lowest-density episodes, at 0.12–0.20 claims per minute against 0.98 for a full extraction, got an **add-only** supplement. Existing claims, artifacts, nodes and memes keep their ids and text; the pass only adds what the earlier extraction missed.

## Method

1. **Extraction.** One agent per episode (Claude Sonnet) read the full transcript and the existing draft and wrote only the missing items.
   - Spec: `SUPPLEMENT_SPEC.md` together with the skeleton `EXTRACTION_SPEC.md`.
   - Every snippet was machine-checked as verbatim.
   - **Calibration.** Episode 60 was run with both Opus and Sonnet. Sonnet found the same key beats and some more (87 claims against 78), so Sonnet was used for the batch.
2. **Integration.** `cka/scripts/supplement_integrate.py` appended the new items to each draft and assigned ids above the PR 66 tips.
   - New nodes take Tip-minted lines.
   - 94 nodes first appear earlier than their recorded introduction, so their intro moved to the earlier episode. Tip-minted nodes stay Tip-minted (`reintro-epNNN`), others become Hole-minted (`reintro-epNNN`), and the later episode lists them as Reused.
   - Coverage notes from each agent are in `coverage_notes/`.
3. **Inscriptions.** New items were merged into the existing inscription JSON. Existing objects are kept exactly as they are; 19 pre-existing draft/inscription mismatches are left for the inscription-rebuild task.
4. **Gate fixes.**
   - Spoken variants added as aliases: Tim P, Ye, Tumz, Andrew Cipher, Shawn Bryan.
   - Role references added to `mention_grounding.reviewed`: "president of France", "the writer" of the ep158 profile, and the camera operator.
   - Five ungrounded Mentions dropped.
   - Ron Paul, Astrid Tuminez and Allan Robertson are now introduced where they are first named (ep28, ep32, ep136), with Mentions links.

## Result
| Seq | Candace Ep | Video | Claims before | Added | Claims after |
|---|---|---|---|---|---|
| 4 | 237 | [2WEHTk0Xewg](https://youtu.be/2WEHTk0Xewg) | 13 | +78 | 91 |
| 34 | 267 | [581dILVcEE4](https://youtu.be/581dILVcEE4) | 10 | +59 | 69 |
| 36 | 269 | [sImMM04XdWY](https://youtu.be/sImMM04XdWY) | 10 | +87 | 97 |
| 40 | 273 | [his-JBjlkh8](https://youtu.be/his-JBjlkh8) | 11 | +85 | 96 |
| 41 | 274 | [ZAuuSq_j2_w](https://youtu.be/ZAuuSq_j2_w) | 9 | +38 | 47 |
| 48 | 281 | [9k2xrAC0H88](https://youtu.be/9k2xrAC0H88) | 11 | +87 | 98 |
| 49 | 282 | [ewBzjVe3LNQ](https://youtu.be/ewBzjVe3LNQ) | 11 | +77 | 88 |
| 50 | 283 | [w1oqQbR_bYs](https://youtu.be/w1oqQbR_bYs) | 9 | +71 | 80 |
| 57 | 290 | [BKcOm32ZEGk](https://youtu.be/BKcOm32ZEGk) | 11 | +65 | 76 |
| 60 | 293 | [9naMwS0kMBE](https://youtu.be/9naMwS0kMBE) | 10 | +87 | 97 |
| 65 | 298 | [xjzb_t5Tk9o](https://youtu.be/xjzb_t5Tk9o) | 13 | +93 | 106 |
| 107 | 341 | [Dkxa9OUA9K8](https://youtu.be/Dkxa9OUA9K8) | 15 | +114 | 129 |
| 120 | 354 | [9CuC1yf8-PU](https://youtu.be/9CuC1yf8-PU) | 10 | +74 | 84 |
| 125 | 359 | [X3VKJVJ7cN4](https://youtu.be/X3VKJVJ7cN4) | 10 | +67 | 77 |
| 130 | 364 | [ds6umq1rHAw](https://youtu.be/ds6umq1rHAw) | 10 | +88 | 98 |
| 141 | 376 | [E7P2ShoYDUA](https://youtu.be/E7P2ShoYDUA) | 13 | +83 | 96 |
| 144 | 379 | [_cNtgris8Ik](https://youtu.be/_cNtgris8Ik) | 14 | +80 | 94 |
| 157 | 394 | [bIuvTKlFeGo](https://youtu.be/bIuvTKlFeGo) | 12 | +115 | 127 |
| 158 | 395 | [5TTkMa49qj8](https://youtu.be/5TTkMa49qj8) | 12 | +65 | 77 |
| 159 | 396 | [q4m-kGzvwjw](https://youtu.be/q4m-kGzvwjw) | 9 | +98 | 107 |

The batch adds **1,611 claims** (C-4838..C-6448), 49 persons, 94 topic/org/place nodes and 45 memes. Bridges go from 11,580 to 14,627: Contradicts 23 → 40, Qualifies 12 → 37.

## Needs your review

**Policy.** Several attributed claims record sweeping, fringe or group assertions as the host made them, each worded "the host says…":
- Talmud characterization: [50@00:22:15](https://youtu.be/w1oqQbR_bYs?t=1335)
- "Jewish people controlled the slave trade": [50@00:26:29](https://youtu.be/w1oqQbR_bYs?t=1589)
- Zionist control of the cabinet, and JFK: [57@00:52:43](https://youtu.be/BKcOm32ZEGk?t=3163)
- Fluoride, moon-landing rituals and CERN (ep57)
- "Macron allegedly paid $1.5M for her assassination": [40@00:43:48](https://youtu.be/his-JBjlkh8?t=2628)

Decide whether these stay (perhaps with a relevance tag) or are excluded from the ledger.

**Identity.**
- **Dennis Frantzve (N-750):** the transcript says "Dennis Franks Bay", Erika's cousin who showed her around Romania. Inferred from the Frantzve family name: [125@00:23:00](https://youtu.be/X3VKJVJ7cN4?t=1380)
- **Volodymyr Zelensky (N-724):** transcribed "Zilinski" in the context of a Ukraine leaders' meeting: [36@00:11:24](https://youtu.be/sImMM04XdWY?t=684)
- **Rabbi Ysef MRI (N-737):** probably Rabbi Yosef Mizrachi.
- **Joseph Cornis (N-735):** unverified.
- **Tom Claire (ep36):** role unknown.

**Possible bias in the earlier record.**
- **C-3289** attributes "I have his cell phone" to Wilson. The new C-L28 Revises it, because the host ties the line to Erika's Glenn Beck interview: [141@00:19:40](https://youtu.be/E7P2ShoYDUA?t=1180)
- **C-2226** reverses who won "Anti-Semite of the Year". The new C-L1 Revises it: [65@00:00:01](https://youtu.be/xjzb_t5Tk9o?t=1)

**Corroboration inflation.** Same-host Supports map to `isCorroboratedBy` (443 edges). This is to be fixed in the companion mapping.
