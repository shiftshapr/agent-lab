# CKA daily 2026-10-23: Ep 405–407 (seq 168–170)

Headless daily run (`docs/daily/RUNBOOK.md`), on a fresh branch from `origin/main`.

**Overlap with PR #126.** PR #126 (`cka-daily-2026-10-22`, seq 168–169) is still open and waiting for Daveed, so intake
offered 168 and 169 again together with 170 (Ep 407). This run re-extracted all three from scratch and **supersedes
#126**. The two PRs conflict; only one of them should be merged. Ids line up with #126 where the same node was
minted, for example N-972 to N-976 and the Oswald intro move.

| seq | Ep | date | YouTube | claims |
|---|---|---|---|---|
| 168 | 405 (inferred) | 2026-10-20 | ihLQRXxIfjU | 81 (C-14475–C-14555) |
| 169 | 406 (inferred) | 2026-10-21 | ZxlvNO8OVmc | 86 (C-14556–C-14641) |
| 170 | 407 | 2026-10-23 | IAVSN4vuCx0 | 233 (C-14642–C-14874) |

Total: 400 claims, with artifacts up to A-3446.

## New nodes
- **Persons (16):** N-972 Lee Harvey Oswald, N-973 Carl Bernstein, N-974 Loretta Cole, N-975 Kimberly Guilfoyle,
  N-976 Eric Deters, N-977 Zee Cohen, N-978 Tammi Peters, N-979 Amy Acton, N-980 Donna Arthur, N-981 Paul Gosar,
  N-982 Mary Trump, N-983 Alex Bruesewitz, N-984 Robby Starbuck, N-985 Noah Gonzalez, N-986 Fulier (FBI special
  agent), N-987 Lisa Farmer.
- **Topics, organisations and places (17):**
  - N-11362 Losee Center (place)
  - N-11363 "Slender Man" Losee Rooftop Return Identification
  - N-11364 Kimberly Guilfoyle Ambassador to Greece Resignation
  - N-11365 Unf*ck America Tour
  - N-11366 University of Nevada, Las Vegas
  - N-11367 Fayetteville Christian School
  - N-11368 CityView
  - N-11369 NBC
  - N-11370 Tyler Robinson Trial-Setting Hearing (October 2026)
  - N-11371 Deseret News
  - N-11372 Ramaswamy Campaign Ad Featuring Amy Acton's Mother
  - N-11373 Allie Beth Stuckey Horror Content Remarks
  - N-11374 Fort Bragg
  - N-11375 Tyler Robinson Trial Scheduling
  - N-11376 Discord Message Narrative Reversal
  - N-11377 Kash Patel DNA Announcement vs FBI Analyst Testimony
  - N-11378 TPUSA Influencer Autopsy-Offer Post (Deleted)
- **Memes (2):** M-369 "A Narrative That Glows" and M-370 "Slender Man".
- **Reused:** ep170's "Amanda Bakker" was matched to the existing N-776.
- **Intro move:** Lee Harvey Oswald (N-972) is first named in ep48 (C-4259) and also in ep87 (C-7835). Following #126:
  - his introduction moved to ep48 (`Tip-minted Nodes (reintro-ep048)`);
  - Mentions and register rows were added in ep48 and ep87, and ep168 now lists him as reused;
  - the ep48 and ep87 inscriptions were patched in place;
  - `canonical/nodes.json` gives his episodes as 48, 87 and 168.
- **Mention fixes (preflight `mention_grounding`):**
  - Mentions dropped because they rested on inference: N-978 from C-14636 and C-14637 (the school founder is
    not named there), N-505 from C-14792, and N-330 from C-14824.
  - Added to `mention_grounding.reviewed`: C-14658 → N-40 ("he", the alleged shooter, in the route timeline) and
    C-14754 → N-330 (Baron Coleman speaks the line).
- **Renamed:** N-978 Tammy Peters → Tammi Peters, from the CityView article; the intake check found it.

## Rules added (35 new, 3 widened)
- **Seq 168:**
  - Brian Coole → Brian Cole; Taylor Robinson → Tyler Robinson (rule widened to 168).
  - Lozi seat rooftop / Lowsey / Lussi → Losee.
  - Director Cash → Director Kash; Blake enough → Blake Neff.
- **Seq 169:**
  - Loeffler → Losee; Z Cohen → Zee Cohen; going into Mitch → going into midterms.
  - Darla Arthur → Donna Arthur, and "and I may me act as my mother" → "and I'm Amy Acton's mother".
  - Tammy Peters → Tammi Peters.
- **Seq 170:**
  - Amanda Baker → Amanda Bakker; Jennifer Fuina Fuina → Jennifer Faumuina; Samantha Carer → Samantha Karner.
  - Christopher Baggley → Christopher Bagley; Agent David Hall / David Hall who is the co-lead / Agent Ho → Hull.
  - Andrew Kobet → Andrew Kolvet (the Andrew Kovvette rule was widened to 170); Xavier Bousard → Xavier Poussard.
  - "Wolf in Finance, Wolves in Finance" → Wolves and Finance; Latafia → Latvia; bed slot → fed slop.
  - candacewowens.com / canowens.com → candaceowens.com.
  - Loi / Loy / "rooftop at Lozi" → Losee.
- **Seq 168 and 170:** Losi → Losee.
- **Seq 168–170:** Erica → Erika (rule widened).
- **Global (unique forms):** Eric Deeters → Eric Deters; Katie Zakharyia → Katie Zacharia; Ali Sokki → Allie
  Stuckey; Alex Bruce Witz → Alex Bruesewitz; Robbie Starbucks → Robby Starbuck.
- **Skipped:**
  - "un f America" / "Unf America": the host censors herself.
  - "Brian J. Cole": the host corrects herself on air.
  - "Dan flut" → Dan Flood: likely but not certain.
  - "Cole's" → Kohl's: not confirmed by a source this run (#126 applied it).
  - "Loews Hotel" (ep168): may be the host's own slip.
- No rule changed an older transcript. `git diff -- transcripts_corrected/` touches only the new files.

## Opus check at intake
- **Scope:** 400 claims in 7 chunks.
- **Material findings: 25, a rate of 6.3% before fixes.** The confirm pass accepted 24 and rejected 1 (C-14778,
  a speaker change that rested only on the caption `>>` markers).
  - 19 are Mentions fixes: missing or extra person ids.
  - 4 are speaker attributions between the host and Baron Coleman (C-14648, C-14835, C-14843, C-14863).
  - 1 is a wording fix: C-14717 says it was the Discord narrative, not the text messages, that was dropped.
  - 1 is a name: Tammi Peters
    ([CityView](https://www.cityviewnc.com/stories/erika-kirk-visit-to-fayetteville-christian-school-concerns-some-parents/)).
- **Fixes applied:** 50 (24 confirmed and 26 minor, including relevance re-tags of the midterm, Acton-ad and
  Loomer material). One minor fix was skipped: on C-14872 it would drop "September 10" (see review items).
- Ep170 is a two-host show with auto-caption speaker markers, which explains most of its material rate.
- **Gates:** all pass; pytest 87 passed.

## Open questions (ROADMAP 4.3)
257 new core claims: 203 linked to existing questions, and 54 covered by 18 new questions.
- Q-1318 rooftop person: the rooftop figure's height and build against Robinson's.
- Q-1319 campus footage: a gap at about 12:40 in UVU's recording of the Losee ledge.
- Q-1320 TPUSA campus events: the UNLV "conspiracy night", and whether presenters were told not to discuss the
  assassination.
- Q-1321 TPUSA campus events: whether audience questions are screened, and who the audiences are.
- Q-1322 Erika school events: arrangements for the 2026-10-28 Fayetteville Christian School visit.
- Q-1323 Erika school events: the backgrounds of schools hosting Erika Kirk, and any shared military tie.
- Q-1324 TPUSA child-abuse cases: documented cases involving people affiliated with TPUSA.
- Q-1325 host's unreleased evidence: what the host says she holds until trial.
- Q-1326 hearing media access: the no-broadcast order for the trial-setting hearing.
- Q-1327 trial schedule: the trial date and length, and the 2028 vs 2029 proposals.
- Q-1328 Agent Hull background: Hull's service history.
- Q-1329 Twiggs identification: how Twiggs identified Robinson from the photos.
- Q-1330 scene holster: the off-duty trooper and the holster he recovered.
- Q-1331 DNA testing: who asked the FBI lab to rush testing and to stop comparisons.
- Q-1332 message photographs: the photos of Twiggs's phone against the extraction.
- Q-1333 firearms examiner: Karner's proficiency record and her inconclusive results.
- Q-1334 autopsy report access: the deleted influencer post about an autopsy offer.
- Q-1335 Robinson custody: Robinson's custody conditions and safety.

## Tweets
- **Posts:** 22 new @RealCandaceO posts. 7 are linked to claims, 9 to nodes only, and 6 are unlinked (3 reply
  chatter, 2 off topic, 1 unclear).
- `merge_links.py --check`: 0 problems.
- **Contradictions or walk-backs:** none. Her posts denying that Erika Kirk offered her the autopsy match C-14819
  (`same_allegation`).
- **Review:** in https://x.com/RealCandaceO/status/2113286220038164902 she says the TPUSA influencer, not Erika,
  invented the autopsy-offer story. It is linked as a `follow_up` that extends C-14815 and C-14820.

## Review items
1. **Lance Twiggs: crime speculation and personal life (privacy hit).** He is a private individual.
   - C-14583, 00:14:55: "I myself have wondered aloud if Lance Twiggs was not blackmailed by the state for an
     internet crime." https://youtu.be/ZxlvNO8OVmc?t=895
   - C-14584, 00:15:08: "It's again my opinion that he may have helped to set Tyler Robinson up as a patsy because he
     got caught in something online." https://youtu.be/ZxlvNO8OVmc?t=908
   - C-14782, 01:07:05: "I do feel he's a federal asset on the basis of what we've been told about his background."
     https://youtu.be/IAVSN4vuCx0?t=4025
   - C-14783, 01:07:15: "He, you know, flies into rages. This is all true. He had substance abuse issues."
     https://youtu.be/IAVSN4vuCx0?t=4035
2. **School founder's family (privacy hit).**
   - C-14636, 00:56:36: "the founder of the school has a military background, and her husband is a colonel in the
     military." https://youtu.be/ZxlvNO8OVmc?t=3396
   - C-14637, 00:57:05: "her husband's a colonel in the military who lived and served in Eastern Europe."
     https://youtu.be/ZxlvNO8OVmc?t=3425
3. **Loretta Cole (private person).** She is Brian Cole Jr.'s grandmother. She is named with her Christmas purchase
   and store credit card in Steve Baker's post.
   - C-14493, 00:08:35: https://youtu.be/ihLQRXxIfjU?t=515
   - C-14494, 00:08:50: "purchase record from Cole's". "Kohl's" is unconfirmed. https://youtu.be/ihLQRXxIfjU?t=530
4. **Amy Acton's childhood abuse.** Acton is a public figure; the abuse happened when she was a minor.
   - C-14606, 00:28:25: "Her and her brother were removed from her mother's custody after abuse from their
     stepfather." https://youtu.be/ZxlvNO8OVmc?t=1705
   - C-14607, 00:28:40. https://youtu.be/ZxlvNO8OVmc?t=1720
5. **Unconfirmed hearing names, with person nodes minted.**
   - "Fulier", the FBI special agent (N-986), C-14745, 00:47:20: "she spoke to the FBI special agent Fulier and the
     Utah FBI, David Hull." https://youtu.be/IAVSN4vuCx0?t=2840
   - Lisa Farmer (N-987), C-14787, 01:08:35: "Lisa Farmer had gathered them." The verifier saw a hint of "Elisa".
     https://youtu.be/IAVSN4vuCx0?t=4115
   - Noah Gonzalez (N-985), C-14735, 00:43:45. The verifier found him in East Idaho News's hearing live blog.
     https://youtu.be/IAVSN4vuCx0?t=2625
6. **Tammi or Jamie Peters (N-978).** The article spells it Tammi; the host later says "this Jamie Peters", which is
   kept as an alias. https://youtu.be/ZxlvNO8OVmc?t=588
7. **Possible duplicate topics.** N-11370 Tyler Robinson Trial-Setting Hearing (ep169) and N-11375 Tyler Robinson
   Trial Scheduling (ep170) could be merged.
8. **The figure vs the press.** In C-14743 (00:46:45) the host gives Bakker's normal DNA turnaround as "90 and
   200 days"; press coverage says 180 to 200. The claim keeps her figure. https://youtu.be/IAVSN4vuCx0?t=2805
9. **C-14523 vs the record.** "Remember the screwdriver is the only thing that has tied Tyler Robinson to the rooftop"
   (00:25:35). Q-1185 (answered) records his DNA on the screwdriver. https://youtu.be/ihLQRXxIfjU?t=1535
10. **C-14872.** The claim says "the morning of September 10"; the transcript says only "that morning" (02:16:30). The
    minor fix was skipped because it would drop the date. https://youtu.be/IAVSN4vuCx0?t=8190
11. **Unresolved names:**
    - "Latif and bot farm" (00:48:05). A viewer comment just before says "Latin bot farms".
      https://youtu.be/ihLQRXxIfjU?t=2885
    - "Kelly Fuller", the X user in the Boreing thread (C-14529, 00:34:10). https://youtu.be/ihLQRXxIfjU?t=2050
    - "Then it was Howard Scripps" (00:05:17), probably Scripps-Howard. https://youtu.be/ihLQRXxIfjU?t=317
    - "Loews Hotel rooftop at 12:35" (00:17:38), probably the host's slip for Losee.
      https://youtu.be/ihLQRXxIfjU?t=1058
    - "the first Call to America" (C-14571, 00:07:55), possibly Club America. https://youtu.be/ZxlvNO8OVmc?t=475
    - "Uncle Fiasco" (00:53:24), possibly Theo Von. https://youtu.be/ZxlvNO8OVmc?t=3204
    - "C. F. Dalton", the X user whose post the host reads (C-14625, 00:43:16). https://youtu.be/ZxlvNO8OVmc?t=2596
    - "Dan flut" (01:37:47), probably Dan Flood (N-270). https://youtu.be/IAVSN4vuCx0?t=5867
12. **Duplicate node:** Father Ripperger has two ids, N-324 and N-570; a merge is pending.
