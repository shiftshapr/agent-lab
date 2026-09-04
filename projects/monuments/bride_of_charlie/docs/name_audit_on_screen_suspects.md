# Bride of Charlie — on-screen / video name audit (suspects)

**Scope:** `transcripts_corrected/` episodes 1–8 only.  
**Method:** Systematic grep + manual context review for person-name near-misses (ASR/debate substitutions, military rank + odd surnames, glossary `stt_often` forms still present).  
**Policy for this audit:** No corrections applied. No overrides. No inscription. Flag only — prefer **video/on-screen check** over transcript debate.

**Generated:** 2026-09-04 (Cloud Agent scan, `main` tip).

---

## Summary

| Category | Count |
|----------|------:|
| **Open suspects** (need video/on-screen confirmation) | **23** |
| **Resolved / proven** (not open) | **1** |

---

## Resolved / proven (not open)

| Ep | Timestamp | Snippet | Status | Notes |
|----|-----------|---------|--------|-------|
| 6 | `[17:28]` | `…was even stationed with a Sergeant Ber` | **Proven: Sergeant Boyer** | On-screen Facebook post (landing separately) shows **Boyer**, not Ber. Still present in `transcripts_corrected/episode_006_y8lak3CRwDw.txt` — transcript fix is out of scope for this audit; do not debate ASR into a replace without re-checking that post. |

---

## Open suspects — video/on-screen check preferred

Each row is one flagged hit. Recommended next step is **video/on-screen check** unless noted.

### Military rank + surname (Ber-class landmines)

| # | Ep | Timestamp | Transcript snippet | Why suspicious | Next step |
|---|----|-----------|-------------------|----------------|-----------|
| 1 | 6 | `[15:32]` | `…has confirmed ASU undergraduate Tyler Storm Bowyer as the new student regent…` | Raw STT had `Storm Buer`. “Storm” may be middle name on a news clip, or ASR glue (`Tyler` + `Storm` + `Boyer/Bowyer`). Wrong person/name conflation risk for Tyler Bowyer. | **video/on-screen check** — read the ASU/senate confirmation graphic |
| 2 | 5 | `[28:38]` | `…Colonel Otto Buscher is` | Raw STT: `Colonel Otto Busher` / `Otter Busher`. Glossary canonical is **Buscher**; corrected changed spelling without a cited on-screen artifact in-repo. | **video/on-screen check** — rank + surname on source doc or chyron |
| 3 | 6 | `[30:48]`–`[30:56]` | `…Colonel Otto Buscher… Buscher who will be accused` | Same Buscher/Busher split as ep5; raw used **Busher**. | **video/on-screen check** |
| 4 | 7 | `[38:47]` | `thanks Colonel Otto Buscher in` | Same family of spellings; raw ep7 used **Busher**. | **video/on-screen check** |
| 5 | 6 | `[18:53]` | `…it was Captain Curtis Kovvet who was stationed in Afghanistan.` | Glossary canonical: **Curtis Kolvet**. `Kovvet` matches raw but may be wrong person spelling on military records/article. | **video/on-screen check** — captain name on cited article |
| 6 | 6 | `[19:08]` | `…Curtis Kulovit was the commander of the 593rd` | Same person, third spelling in ~30s (`Kovvet` / `Kulovit` / `Kovett`). Strong ASR/substitution signal. | **video/on-screen check** |
| 7 | 6 | `[24:59]` | `Captain Curtis Kovvet is the key` | Repeat of `Kovvet` spelling later in episode. | **video/on-screen check** |
| 8 | 5 | `[04:32]` | `Her father was Colonel Paul Tracy Gerard` | Military rank + multi-part name; verify against on-screen bio/source Jerry Frantzve segment cites. | **video/on-screen check** |

### Bowyer / Boyer / Ber cluster (Tyler + family)

| # | Ep | Timestamp | Transcript snippet | Why suspicious | Next step |
|---|----|-----------|-------------------|----------------|-----------|
| 9 | 5 | `[35:39]` | `…you knew the Boyers.` | Narration lists **Boyers**; house glossary canonical surname is **Bowyer**. Raw also had Boyers — may be spoken or may be ASR from Bowyer. | **video/on-screen check** |
| 10 | 6 | `[22:53]` | `…the Frantzve phase and the Boyers` | Same Boyers vs Bowyers question in Romania/Afghanistan synergy passage. | **video/on-screen check** |
| 11 | 7 | `[43:31]` | `And crucially, the Boyers, the Farnsworth, the Frantzves, the Kolvets,` | Third **Boyers** hit; inconsistent with **Bowyer** elsewhere in corrected text. | **video/on-screen check** |
| 12 | 7 | `[27:24]` | `…committee at the university, Bowyer applied directly through the governor's office.` | Raw STT: `Ber applied`. Corrected to **Bowyer** (parallel to Sergeant Ber→Boyer fix) but no on-screen cite recorded in this audit for this line. | **video/on-screen check** — governor/press clip spelling |

### Kolvet / Kovett / Kulvette family (same landmine pattern as Ber)

| # | Ep | Timestamp | Transcript snippet | Why suspicious | Next step |
|---|----|-----------|-------------------|----------------|-----------|
| 13 | 6 | `[18:57]` | `And yeah, that's Andrew Kovett's brother.` | **Andrew** spelled `Kovett`; glossary **Andrew Kolvet**; elsewhere **Kovette** / **Kulvette**. | **video/on-screen check** |
| 14 | 4 | `[54:09]`–`[54:25]` | `Andrew Kovette, the PR guy… Andrew Kovette.` | TPUSA PR figure; spelling **Kovette** vs ep8 **Kolvet** and ep6 **Kovett**. | **video/on-screen check** — LinkedIn/on-screen lower third |
| 15 | 7 | `[40:41]` | `…Erika and Andrew Kovette` | Same **Kovette** spelling. | **video/on-screen check** |
| 16 | 8 | `[00:03]` | `everyone except Andrew Kolvet.` | Only ep8 line uses glossary-canonical **Kolvet**; conflicts with **Kovette**/**Kovett** in other episodes. | **video/on-screen check** — reconcile all Andrew spellings to one on-screen source |
| 17 | 6 | `[19:56]`–`[20:01]` | `…Robert Kulvette.… Robert Kovette was the commander` | **Two spellings five seconds apart** for Robert (Kulvette → Kovette). Raw had similar chaos. | **video/on-screen check** — Facebook caption / unit roster shown |
| 18 | 6 | `[22:49]` | `…if the Kovets and the` | Plural **Kovets** vs **Kolvets** (ep7) vs Kolvet canonical. | **video/on-screen check** |
| 19 | 7 | `[43:33]` | `…the Kolvets,` | **Kolvets** plural in Arizona GOP committee list; may be correct family plural or ASR from Kovett/Kolvet. | **video/on-screen check** |
| 20 | 6 | `[58:18]` | `…episode that involved Andrew Kulvette` | Reader-mail quote; **Kulvette** variant (not frozen). | **video/on-screen check** if episode material uses this name on-screen |

### Frantzve / Fron / Fay / Feay / Ferrin (surname truncation & France homophone)

| # | Ep | Timestamp | Transcript snippet | Why suspicious | Next step |
|---|----|-----------|-------------------|----------------|-----------|
| 21 | 1 | `[17:50]` | `…he's Kenneth Fron, but he goes by Kent, was` | Truncated **Fron** where family canonical is **Frantzve**; may be spoken abbreviation or STT clip. | **video/on-screen check** — Tucker clip / chyron |
| 22 | 1 | `[21:57]` | `Frantzve Feay, we are told, was born on` | **Feay** embedded in birth-announcement line; unusual compound vs plain Frantzve. | **video/on-screen check** — scan of announcement |
| 23 | 2 | `[13:46]` | `…a C in algebra," Fron said in an interview.` | Quote attribution **Fron** (Jerry Frantzve interview?); raw/corrected may have dropped surname. | **video/on-screen check** — byline on interview clip |
| 24 | 2 | `[19:13]` | `she's going by Dr. Frantzve Fay. and her` | **Fay** fused with Frantzve (caption-era “Frantzve Fay”); person-name merge risk. | **video/on-screen check** |
| 25 | 2 | `[23:44]` | `…Richard Castor, Susan` | Raw STT: **Richard Caster**. Corrected to **Castor** without documented on-screen report cover in this audit. | **video/on-screen check** — Radford report cover (five names block) |
| 26 | 2 | `[55:21]` | `mother, Marjorie Frantzve. F E R R I N.` | Raw: `Marjorie France. F E R R I N.` Narrator spells **FERRIN** while label says **Frantzve** — wrong-person / wrong-surname risk (Mormon line). | **video/on-screen check** — Jerry Mormon-family segment |
| 27 | 5 | `[12:07]` | `uh Lorie Fron forms another Intel` | **Lorie Fron** = truncated Frantzve in narration (LLC timeline). | **video/on-screen check** if filing shown |
| 28 | 7 | `[03:56]` | `Fron's face bio.` | **Fron's face** for Frantzve bio (STT homophone); ep7 also has on-screen profile quote below. | **video/on-screen check** |
| 29 | 7 | `[46:17]` | `>> Hi, I'm Erika Fron. I'm 25 years old` | On-screen reality-show style intro; surname clipped to **Fron**. High-value on-screen frame. | **video/on-screen check** — freeze frame on show graphic |

### Other person-name near-misses

| # | Ep | Timestamp | Transcript snippet | Why suspicious | Next step |
|---|----|-----------|-------------------|----------------|-----------|
| 30 | 1 | `[19:41]` | `Larry Ginta. in her high school` | Glossary canonical **Guinta**; ep4 narration explicitly flags Ginta/Guinta ambiguity. | **video/on-screen check** — marriage/divorce docs |
| 31 | 3 | `[38:23]` | `Larry Ginta. That's the first time um` | Repeat **Ginta**. | **video/on-screen check** |
| 32 | 7 | `[41:19]` | `husband Larry Ginta recommend that you` | Third **Ginta** hit. | **video/on-screen check** |
| 33 | 7 | `[40:03]`–`[40:39]` | `Diane Bernett… Mark Bernett… Mark Bernett` | Survivor/Apprentice creator is conventionally **Mark Burnett**; **Bernett** may be ASR or on-screen typo. | **video/on-screen check** — Tracy Martin clip / social like UI |
| 34 | 4 | `[06:10]` | `…Wargaming Blake Nef` | Glossary: **Blake Neff**. **Nef** persists in corrected across eps 4–7. | **video/on-screen check** — lower third / tweet |
| 35 | 6 | `[16:38]`–`[24:13]` | `Dennis Frantzve` (multiple) | Cousin Marine named **Dennis Frantzve** — verify against FB/military graphic shown in episode (not assumed from narration alone). | **video/on-screen check** |
| 36 | 3 | `[27:18]` | `…alleged marriage between Lauri and Kent.` | **Lauri** vs canonical **Lori** — ASR given-name near-miss. | **video/on-screen check** if doc shown |
| 37 | 3 | `[05:11]` / `[14:12]` / `[15:33]` | `Laurianne` / `Lorianne` | vs **Lori Anne Erpenbeck** (Erpenbeck sister); possible person conflation. | **video/on-screen check** — court/news clips |

---

## Intentionally not flagged (context-checked)

- **France** in ep1/ep2 where meaning is country, DuPont wordplay, or Macron — not person-surname substitution.
- **Lorie** / **Loriy's** — caption-style Lori variants; house style prefers **Lori** but not Ber-class wrong-person swaps (lower priority than rows above).
- **Erpenbeck** spellings — normalized per monument house style; not ASR person substitution in corrected set.
- **Tyler Bowyer is** / **Bowyer is's** — caption merge artifact (`Tyler Ber is` → editorial spacing); grammar noise, not a distinct person name.
- Glossary **`stt_often`** forms absent from corrected (`Tyler Ber`, `Busher`, `Erica`, `Candice`, `Bronzeface`, `Franfveet`, etc.) — already scrubbed in corrected layer; remaining suspects are **near-misses still in text** or **corrected without recorded on-screen proof**.

---

## Suggested video-check order (highest yield)

1. Ep6 `[17:28]` Sergeant line (confirm Boyer fix when editing transcript) + `[15:32]` Storm Bowyer + Kolvet block `[18:53]`–`[20:01]`.
2. Ep2 `[23:35]`–`[23:47]` report cover five names + `[55:21]` Marjorie F E R R I N.
3. Ep7 `[46:17]` Erika Fron intro + `[40:03]` Bernett/Burnett + `[27:24]` Bowyer applied.
4. Ep5/ep6 Buscher/Busher military thank-you segments.

---

## Files scanned

```
projects/monuments/bride_of_charlie/transcripts_corrected/episode_001_ZAsV0fHGBiM.txt
projects/monuments/bride_of_charlie/transcripts_corrected/episode_002_1IY2oD-_xVA.txt
projects/monuments/bride_of_charlie/transcripts_corrected/episode_003_cZxHqYsWRYg.txt
projects/monuments/bride_of_charlie/transcripts_corrected/episode_004_jTj9Ip46r4w.txt
projects/monuments/bride_of_charlie/transcripts_corrected/episode_005_2tFYJf1klgY.txt
projects/monuments/bride_of_charlie/transcripts_corrected/episode_006_y8lak3CRwDw.txt
projects/monuments/bride_of_charlie/transcripts_corrected/episode_007_DdPjoy5W-wY.txt
projects/monuments/bride_of_charlie/transcripts_corrected/episode_008__vg7ucP1E0g.txt
```

Reference configs (not modified): `config/transcript_canonical_glossary.json`, `config/transcript_suspicious_patterns.json`.

---

*Draft audit for human/video confirmation. No overrides applied. No merge.*
