# CKA daily 2026-10-22: Ep 405–406 (seq 168–169)

Headless daily run (`docs/daily/RUNBOOK.md`). Ep 407 (IAVSN4vuCx0) had no captions yet and waits for the next run.

| seq | Ep | date | YouTube | claims |
|---|---|---|---|---|
| 168 | 405 (inferred) | 2026-10-20 | ihLQRXxIfjU | 83 (C-14475–C-14557) |
| 169 | 406 (inferred) | 2026-10-21 | ZxlvNO8OVmc | 96 (C-14558–C-14653) |

## New nodes
- **Persons (12):** N-972 Lee Harvey Oswald, N-973 Carl Bernstein, N-974 Loretta Cole, N-975 Kimberly Guilfoyle,
  N-976 Eric Deters, N-977 Zee Cohen-Sanchez, N-978 Tammy Peters, N-979 Michelle Obama, N-980 Amy Acton,
  N-981 Donna Arthur, N-982 Paul Gosar, N-983 Mary Trump.
- **Topics, organisations, places (9):** N-11362 Losee Rooftop Return Figure ("Slender Man") Identification,
  N-11363 Kimberly Guilfoyle Greece Ambassadorship Exit, N-11364 Unfuck America Tour, N-11365 University of Nevada,
  Las Vegas, N-11366 Fayetteville Christian School, N-11367 CityView, N-11368 Tyler Robinson Trial-Setting Hearing
  Broadcast Ban, N-11369 Ramaswamy Campaign Amy Acton Mother Attack Ad, N-11370 Fort Bragg.
- **Meme (1):** M-369 Slender Man.
- Both extractions minted the rooftop-figure topic and the Slender Man meme; the names were unified so they deduped.
- **Intro move:** Lee Harvey Oswald (N-972) is named in ep48 (C-4259) and ep87 (C-7835). His introduction moved to
  ep48 (`Tip-minted Nodes (reintro-ep048)`), with Mentions and register rows added in ep48 and ep87; the id is
  unchanged and ep168 now lists him as reused. The inscriptions for ep48 and ep87 were patched in place, and the
  draft `Transcript SHA-256` of both was refreshed to the current corrected transcript.
- **Gate exception:** C-14651 → N-978 is a role reference ("the founder of the school"), added to
  `mention_grounding.reviewed`.

## Rules added (19)
- Seq 168: Brian Coole → Brian Cole; Taylor Robinson → Tyler Robinson; Lozi seat rooftop / Lowsey / Losi / Lussi →
  Losee; Cole's jacket / credit card, from Cole's → Kohl's ("Brian Cole's grandmother" untouched); Director Cash →
  Director Kash; Blake enough → Blake Neff.
- Seq 169: Loeffler → Losee; Z Cohen → Zee Cohen; going into Mitch → going into midterms; Darla Arthur → Donna Arthur
  and "and I may me act as my mother" → "and I'm Amy Acton's mother" (both from the intake check, source PBS).
- Seq 168–169: Erica → Erika.
- Global (unique forms): Eric Deeters → Eric Deters; Katie Zakharyia → Katie Zacharia; Ali Sokki → Allie Stuckey.
- **Skipped:** "un f America" / "Unf America" (the host censors herself); "Loews Hotel" (seq 168, 00:17:38 and
  00:27:25; the captions agree, and it may be the host's slip for Losee); "Howard Scripps" (kept as said, with
  "[Scripps-Howard]" in the claim).
- N-981 was renamed Darla Arthur → Donna Arthur directly.

## Opus check at intake
- 179 claims checked in 3 chunks; 3 material findings (rate **1.7%**), all accepted on confirm:
  - C-14618: the woman in the Ramaswamy ad is Donna Arthur, Acton's mother
    ([PBS](https://www.pbs.org/newshour/politics/ramaswamy-campaign-says-it-produced-ad-with-amy-actons-mother-and-will-spend-millions-to-promote-it)).
  - C-14536 and C-14550: wrong person ids in Mentions (N-366, N-1) removed.
- 1 minor finding amended (C-14487, Scripps-Howard bracket). 20 fixes applied in total (4 confirmed, 16 minor,
  mostly relevance re-tags of the Acton ad / Stuckey segment from context to tangential).
- Gates: all pass, pytest 87 passed.

## Open questions (ROADMAP 4.3)
74 new core claims: 44 linked to existing questions, 30 covered by 10 new questions:
- Q-1318 Scripps bodycam releases: how Scripps News obtained the Robinson and Cole bodycam footage.
- Q-1319 rooftop footage gap: whether UVU's logs show a gap in the Losee rooftop recording at about 12:40–12:42.
- Q-1320 rooftop figure height: the figure's height against Tyler Robinson's.
- Q-1321 TPUSA event Q&A: whether TPUSA bars or screens assassination questions at campus events.
- Q-1322 Erika school events: Erika Kirk's 2026-10-28 chapel visit to Fayetteville Christian School.
- Q-1323 Erika school events: military ties (Fort Bragg) of schools hosting Erika Kirk.
- Q-1324 Twiggs records: any record of an internet-crime matter involving Lance Twiggs (see review item 1).
- Q-1325 court media access: the broadcast ban at the 2026-10-23 trial-setting hearing.
- Q-1326 host's withheld evidence: what the host says she holds until trial.
- Q-1327 Wilson debate: what evidence the host's debate with Andrew Wilson covered.

## Tweets
9 new posts linked: 2 to claims (the ep169 rundown, `same_allegation`; the Baron Coleman handoff announcement,
`follow_up` to C-14653), 5 to nodes only, 2 unlinked (reply chatter). `merge_links.py --check`: 0 problems.
No post contradicts an archived claim. Three posts of 2026-10-22 deny that Erika Kirk offered to show the host
Charlie Kirk's autopsy at their meeting (N-11295); no archived claim says she did:
https://x.com/RealCandaceO/status/2113118985189302489, https://x.com/RealCandaceO/status/2113265874937221379,
https://x.com/RealCandaceO/status/2113286220038164902.

## Review items
1. **Lance Twiggs, crime speculation (privacy hit).** The host, labelling it her opinion, wonders whether he was
   blackmailed by the state over an internet crime and helped set Robinson up. He is a private individual.
   - C-14592, 00:14:53: "I myself have wondered aloud if Lance Twiggs was not blackmailed by the state for an internet
     crime." https://youtu.be/ZxlvNO8OVmc?t=893
   - C-14593, 00:15:08: "It's again my opinion that he may have helped to set Tyler Robinson up as a patsy because he
     got caught in something online." https://youtu.be/ZxlvNO8OVmc?t=908
2. **School founder's family details (privacy hit).** C-14651, 00:56:35: "the founder of the school has a military
   background, and her husband is a colonel in the military." https://youtu.be/ZxlvNO8OVmc?t=3395
3. **Loretta Cole (private person).** Brian Cole Jr.'s grandmother, named with her Christmas purchase and Kohl's
   credit card from Steve Baker's post (C-14494, C-14495), 00:08:30. https://youtu.be/ihLQRXxIfjU?t=510
4. **Amy Acton's childhood abuse.** Acton is a public figure; the abuse was when she was a minor, by an unnamed
   stepfather. C-14616 (00:28:26, https://youtu.be/ZxlvNO8OVmc?t=1706), C-14621 (00:30:45,
   https://youtu.be/ZxlvNO8OVmc?t=1845), C-14626 (00:31:55, "he had been accused of it in the past … with his prior
   family", https://youtu.be/ZxlvNO8OVmc?t=1915).
5. **Tammy or Jamie Peters (N-978).** The article read says "Tammy Peters, the Fayetteville Christian uh co-founder
   and head of school" (00:07:02, https://youtu.be/ZxlvNO8OVmc?t=422); the host later says "this Jamie Peters"
   (00:09:48, https://youtu.be/ZxlvNO8OVmc?t=588). Unconfirmed.
6. **C-14523 vs the record.** "Remember the screwdriver is the only thing that has tied Tyler Robinson to the
   rooftop" (00:25:30, https://youtu.be/ihLQRXxIfjU?t=1530). Q-1185 (answered) records his DNA on the screwdriver.
7. **Unresolved names:**
   - "Latin bot farms" (00:46:29, https://youtu.be/ihLQRXxIfjU?t=2789) and "Latif and bot farm" (00:48:05,
     https://youtu.be/ihLQRXxIfjU?t=2885).
   - "Kel Kelly Fuller", the X user in the Boreing thread (00:33:54, https://youtu.be/ihLQRXxIfjU?t=2034).
   - "Then it was Howard Scripps" (00:05:17, https://youtu.be/ihLQRXxIfjU?t=317), probably Scripps-Howard.
   - "Loews Hotel rooftop at 12:35" (00:17:38, https://youtu.be/ihLQRXxIfjU?t=1058).
   - "Uncle Fiasco" / "Uncle Theo" with a Netflix special (00:53:24, https://youtu.be/ZxlvNO8OVmc?t=3204), possibly
     Theo Von.
   - "C. F. Dalton", author quoted on Christian storytelling (C-14639, 00:43:16, https://youtu.be/ZxlvNO8OVmc?t=2596).
8. **Duplicate node:** Father Ripperger has two ids, N-324 and N-570 (Father Chad Ripperger); a merge is pending.
