# Phase 6 adversarial re-audit (ROADMAP 6.1) (2026-10-24)

## Summary for Daveed (ROADMAP 6.1 → 6.3)

**Strata.**
- **A, verification statuses:** all 619 records.
- **B, then-vs-now pairs:** all 282. 87 are host-vs-herself (B1) and 195 are cross-speaker (B2).
- **C, named-person allegations:** 1,419 claims. These mention a named person other than Kirk or the host and contain
  allegation wording (`C_allegations.txt`).
- **D, random sample:** 2% of the remaining 11,991 claims (240).

A pass that briefed every then-vs-now pair as host-vs-herself was discarded. The 195 cross-speaker pairs were
re-audited under `PROMPT_B2.md`.

**Systemic findings.**
1. **The then-vs-now ledger is not publishable as it stands** (B1 38%, B2 41% material). The pair builder (Phase 5)
   linked:
   - spelling and attribution **correction records** as if they were revisions;
   - **duplicates**, the same pair in both orders;
   - pairs with **the same speaker on both sides**, or no host claim at all;
   - pairs whose `later` claim precedes the `earlier`;
   - compatible statements labelled `contradicts`.

   Many claims also carry a **wrong `host_voice` flag**, which fed the errors. **Recommendation (6.3):** rebuild the
   ledger from the confirmed pairs only:
   - keep the `ok` pairs;
   - apply the `minor` relabels;
   - drop the `material` pairs;
   - re-file the handful of real self-revisions found on the cross-speaker side (for example pair 268 on Harpole,
     and 93 and 99) as host-vs-herself `revises`.

   Then fix the `host_voice` flags, and hold promotion of then-vs-now pairs until you review a fresh sample.
2. **Verification statuses: 4.8% material.**
   - **Corroborated on a side detail.** Several claims were corroborated on a detail while the core point (who, what,
     when) is not in the quote. Examples: C-114, C-1732, C-1930, C-6456, C-13855.
   - **Bare "Correct."/"Yes." answers.** Several rest on a witness's one-word answer cited without the question.
   - **Contradictions where both can be true.** Several `contradicted-by-record` statuses are of this kind: C-511,
     C-7397, C-8073, C-11451.

   **Fix (6.2):** set all 30 to `unverified`, or re-cite with stronger quotes where the auditors named one. Apply the
   ~70 note and evidence corrections.
3. **Allegation framing: 2.2%, just above target.**
   - Most material errors are titles that state the host's allegation as fact, or drop her hedge (concentrated in
     pack C-25, episodes about 97–100).
   - The rest are a guest's, clip's or viewer's words given to the host (C-254, C-2570, C-8357, C-12172, C-12403,
     C-14224), plus timestamps and one mis-transcribed name ("Hoole" for Hull, C-12046).
   - **Fix (6.2):** correct all 31.
   - **Recommendation (6.3):** a title-framing sweep over all claims. Titles are generated separately from claim
     sentences, and the pattern recurs.
4. **The random sample is within target** (1.3%). The bulk of the archive meets the QA target; the risk is concentrated
   in the strata above.

**Rulings needed from you.**
- **The 185 privacy flags** (`findings.json` → `privacy`). These cover:
  - Lance Twiggs and his family;
  - Robinson's parents;
  - George Zinn's alleged crimes;
  - private eyewitnesses and staff;
  - two cases that name minors (C-426, C-1246).

  For each, decide keep, redact the name, or mark tangential.
- **Whether to rebuild the then-vs-now ledger** as recommended in finding 1.
- **Whether to run the title-framing sweep** recommended in finding 3.
- **Whether this Claude-run pass suffices**, or Bill D / Transit should repeat strata A–C independently.

Run by fresh Opus agents with adversarial briefs, at Daveed's request (the ROADMAP names Bill D and Transit as owners; this pass is Claude checking Claude's work, so it is less independent). QA target: < 2% material.

| Stratum | Items | Material | Rate | Target met |
|---|---|---|---|---|
| A: Verification statuses | 619 | 30 | 4.8% | no |
| B1: Then-vs-now: host vs herself | 87 | 33 | 37.9% | no |
| B2: Then-vs-now: host vs other speakers | 195 | 80 | 41.0% | no |
| C: Allegations about named people | 1419 | 31 | 2.2% | no |
| D: Random sample of the rest | 240 | 3 | 1.2% | yes |

**Privacy flags for Daveed (stratum C):** 185 claims (`findings.json` → `privacy`).

## A: material findings (30)

- **C-114**: The only cited source (S-63) says surveillance video 'appears to show the man ... walking toward Utah Valley University's campus hours before'; it gives no 8:07 a.m. time or maroon shirt, and the note itself concedes those core details rest on unconfirmed TMZ facts. → _unverified_
- **C-126**: The only quote is Agent Hull's one-word answer 'Correct.', which read literally establishes nothing about FBI stairwell photos; the question it answers is not quoted. → _unverified (or re-cite with the question text that shows the released press images were the stairwell images)_
- **C-136**: The quotes show only that Exhibit 16.2 images are 'the Discord messages that Lance had talked about', that Lance confirmed them 'during his second interview', and 'Yeah, this is Discord'; none says the roommate opened the app, showed messages to investigators, or let them photograph the screen, and  → _unverified_
- **C-195**: The claim's core is the host's commentary that the note 'mixes past and present tense and is not proper English'; the S-1 quote ('I had the opportunity to take out Charlie Kirk and I'm going to take it') supports only the side detail of the wording, and the note itself says the commentary 'is opinio → _unverified_
- **C-511**: The claim is that ballistics experts are saying the front wound is an exit wound, with the host explicitly disclaiming her own judgment; the ruling 'The projectile did not exit his body' (S-7 08:16:02) contradicts the experts' theory, not the host's report of what experts are saying, so both can be  → _unverified_
- **C-1732**: The only evidence, Deseret News's "just behind his boss when the bullet hit", places McCoy near Kirk but says nothing about the tent, and 'behind the tent' is the host's core point. → _unverified_
- **C-1930**: S-66 shows only that "Owens was sued for defamation by Brigitte Macron ... for claiming she is transgender"; the core allegation that Macron was born Jean-Michel Trogneux is not corroborated, so a corroborated badge on this claim misleads. → _unverified_
- **C-3538**: The only quote cited, '"Charlie made sure the organization was audited by a third party every year," Neff said.', is about audits, not about Charlie personally signing off on every expense or bill. → _unverified (unless the S-49 sentence quoting Neff on personally signing off on every expense is cited)_
- **C-4268**: The only evidence is the host's own statement ('"Erika and I had an extremely productive 4 1/2 hour meeting..." Owens said.'), which is not an independent source for the meeting's length. → _unverified_
- **C-6290**: The quotes cover only the Uber-driver story ('the uber driver told the CEO that the employee ... was her, which Laitsch denied'); nothing shows the claim's core assertion that she was brought into a meeting with Andrew Kolvet and Marina Minas and questioned. → _unverified_
- **C-6456**: The evidence is Morgan's Dec. 17 face-to-face exchange with Owens ('It's making you very wealthy', 'spewing bulls--- to the public'), a different occasion from the played clip in which he speaks of her in the third person and calls it 'regrettable, kind of conspiracy theory nonsense just for clicks  → _unverified_
- **C-7397**: The only quote, "he'd come there with his parents and a family friend", does not name where 'there' is, so read literally it does not contradict 'drove up to Orem'; and the Orem destination is a side detail while the parents/family-friend core of the claim is actually consistent with the quote. → _unverified_
- **C-7730**: The only quotes are defense attorney Burt's question "in many cases, they were mixtures of sometimes four and five people, correct?" and a bare "Correct." with no stated subject, so read literally they show no witness or record assertion of the mixtures, and nothing about the FBI reports or the fili → _unverified (or cite Oliver's actual answer at 01:33:32 and the question she answered 'Correct.' to at 02:02:26)_
- **C-7732**: The quotes ("cannot be identified or excluded as having been fired from the Exhibit 1 rifle") only repeat the ATF finding already covered by C-7731; nothing supports the claim's distinct core, that "the state has not indicated an intent to produce this report" and the defense may call the ATF analys → _unverified_
- **C-8073**: The claim is that a search warrant states a 10:26 p.m. arrival; the ruling's "At approximately 9:00 PM, Mr. Robinson arrived" (and Davis's hearsay "I was told he arrived there about 9:00 PM") does not show the warrant does not say 10:26, so both can be true and no record contradicts the claim. → _unverified_
- **C-8074**: The quotes "These are the Discord messages that Lance had talked about" and "Yeah, this is Discord" do not show the roommate opening Discord and letting investigators photograph the screen, nor that Cox said so; the FBI-photograph detail is only in the note. → _unverified_
- **C-8673**: The evidence ("Chief Long: You want access to the roof?", "Chief Long coordinated directly with TPUSA Security Supervisor Dan Flood by text") supports only the side detail that the chain was Flood-Long; the core point, that Harpole presented it on Shawn Ryan as his own, is admittedly not covered. → _unverified_
- **C-8674**: The claim's core is that Harpole's lawsuit admits the messages were Flood-Long, but the only source is the UVU After-Action Report ("Chief Long coordinated directly with TPUSA Security Supervisor Dan Flood by text"), not the lawsuit, and nothing covers Harpole presenting them as his own. → _unverified_
- **C-10462**: The claim is that Turek said in the clip he did not believe there was an exit wound, but the only evidence is the ruling 'The bullet did not exit Mr. Kirk's body', which does not show Turek said anything. → _unverified_
- **C-10622**: The host's core point is that a witness saw someone else (a bald man) driving at 12:47 a.m., but the quotes are bare answers 'I do remember that being in the report, yes.' and 'I did not.', and the note itself concedes the time and the 'someone else' point are not established. → _unverified_
- **C-10853**: The record supports only the side detail that Robinson texted 'they grabbed some crazy old dude and interrogated someone in similar clothing'; the viewer's point, that a vest-and-mask description was not released until the next day, is admitted in the note to be 'not in the record'. → _unverified_
- **C-11451**: Hull's 'several people who were detained for questioning and who were interviewed throughout the investigation' covers the whole investigation (including later interviewees), while the host means the two people detained as suspects after the shooting; both statements can be true. → _unverified_
- **C-12054**: The quotes show only that he wore 'a maroon short sleeve shirt' that morning and 'a maroon shirt and jeans' on arriving at the sheriff's office the next night; nothing in the record addresses whether he changed his shirt after returning home, which is the host's inference. → _unverified_
- **C-12621**: The quotes only establish that Count 7 exists ('commission of a violent offense in the presence of a child'). The snippet's core point, the defense argument that on a college campus 'the presumption would be that there were no minor children present', is not supported, and the note wrongly calls it  → _unverified_
- **C-12689**: The claim is that Blake Neff said leaving was not abandonment because security got Charlie out, but the only quote is the After-Action Report's 'TPUSA security team was able to evacuate Charlie Kirk from the area immediately', which shows nothing Neff said. → _unverified_
- **C-13186**: The quotes 'This external and independent assessment was done at the request of Utah Valley University' and 'Retained two outside firms' show that a review existed, but they do not show the AP-reported Monday, September 22, 2025 announcement, which is the timing ('just 12 days after') that the claim → _unverified_
- **C-13541**: No quote says no TPUSA security member attended; p. 40 says only that "Maycee Crofts... participated at the request of TPUSA" and p. 42 is about no security contact as of September 2, so the absence is an inference, not a literal finding. → _unverified_
- **C-13588**: The snippet's core point is "There was limited time between chief long first learning of the event and the event date", but the only quote is about the assessment not producing "documented requirements for venue modification", and the note never mentions the limited-time finding. → _unverified (unless the S-12 sentence stating limited time between Long learning of the event and the event date is cited)_
- **C-13807**: The snippet's core point is the host's own search result ("September 2nd is the first time that this upcoming event that we could find is mentioned"), which cannot be corroborated; the quotes support only the side detail of the September 3 Flood call, and the note concedes the club-president detail  → _unverified_
- **C-13855**: The snippet's core assertion is that "Brian Harpole said that um CPR actually was not administered", but no quote shows Harpole saying this (the note concedes "Harpole's remark itself is not in the record"); the quotes support only the review's hospital-CPR detail. → _unverified_

## B1: material findings (33)

- **pair 4 (C-3195 → C-3388)**: Earlier snippet has no date and later snippet is empty, so neither supports the Sept 3 vs Sept 4 discrepancy, which is also a trivial unacknowledged date drift. → _drop_
- **pair 5 (C-2676 → C-4099)**: Later snippet is empty, so the claim that Michael is his real first name is unsupported. → _revises (only after attaching a supporting later snippet); otherwise drop_
- **pair 11 (C-3476 → C-4550)**: Earlier snippet is empty and the earlier item is a question asking whether the donor is Dupont, not an assertion she later replaced. → _drop_
- **pair 12 (C-5180 → C-5181)**: The two claims are the same statement 3 seconds apart (near-duplicate extractions), not a revision. → _drop_
- **pair 17 (C-8632 → C-9153)**: Not a revision: 'he never replied' was true at the time and 'he finally answered' is a later development compatible with it. → _drop_
- **pair 26 (C-7806 → C-10996)**: Both snippets are empty, so the Aug 19 vs Aug 18 dates are unsupported. → _drop_
- **pair 29 (C-7904 → C-11384)**: Earlier snippet does not mention September 8 or a video, so the date discrepancy is unsupported; also duplicates pair 28. → _drop_
- **pair 33 (C-1974 → C-11561)**: Later snippet only says why she believes Erika chose a Catholic mass; it does not say the burial was a mock or that he was not buried, so it does not contradict 'buried in a Catholic cemetery' as given. → _drop_
- **pair 36 (C-11033 → C-11750)**: Not a revision: not knowing the hotel at one time and later finding it out are compatible. → _drop_
- **pair 40 (C-10621 → C-13461)**: Both snippets are empty, so the single vs dual exhaust claims are unsupported. → _drop_
- **pair 44 (C-1081 → C-1082)**: Not host vs herself: the contradiction is between Shaner Broderick's post and Phil Lyman's statement, both relayed; earlier snippet is empty. → _drop_
- **pair 45 (C-4063 → C-4061)**: Not host vs herself: both claims relay Erika's statements (and Kolvet's), the earlier snippet is empty, and the 'earlier' timestamp is after the 'later' one. → _drop_
- **pair 46 (C-3193 → C-4497)**: Later is Erika's denial relayed by the host, not the host walking back her own claim. → _drop_
- **pair 47 (C-5180 → C-5331)**: Earlier relays Justin Streiff's statement, not the host's own claim, and its snippet is empty; the host is disputing TPUSA, not herself. → _drop_
- **pair 48 (C-5452 → C-5455)**: Both sides relay others (Erika's Glenn Beck statement vs TPUSA's response); not the host contradicting herself. → _drop_
- **pair 49 (C-4114 → C-5695)**: Earlier relays Kolvet's account (empty snippet) and later relays Erika's denial; not host vs herself. → _drop_
- **pair 50 (C-5705 → C-7453)**: Both sides are third-party narratives (Kolvet's and Elizabeth McCoy's) relayed by the host; not the host contradicting herself. → _drop_
- **pair 51 (C-10287 → C-10288)**: Both lines describe Erika Kirk contradicting herself (January vs June); the host is not contradicting herself. → _drop_
- **pair 52 (C-11580 → C-11581)**: The earlier line reports the prosecution's assertion and the later is the host disputing it; this is host vs prosecution, not host vs herself. → _drop_
- **pair 56 (C-13307 → C-13308)**: The earlier line reports Andrew Kolvet's claim and the later is the host's evidence against it; host vs Kolvet, not host vs herself. → _drop_
- **pair 57 (C-13307 → C-13309)**: The earlier line reports Kolvet's claim and the later is the host rebutting it; not host vs herself. → _drop_
- **pair 58 (C-13307 → C-13365)**: Both lines are the host rebutting Kolvet's claim about her friendship with Charlie; there is no conflict between her own statements. → _drop_
- **pair 59 (C-13724 → C-13725)**: The earlier line reports Doug DeGroote's account and the later is the host's fact-check against it; host vs DeGroote, not host vs herself. → _drop_
- **pair 62 (C-3719 → C-3720)**: The caller not being contacted and the question of why the filmer was not subpoenaed are compatible points in the same breath; nothing is narrowed, and the earlier snippet is empty. → _drop_
- **pair 64 (C-3944 → C-3942)**: The 'later' (00:39:36) comes before the 'earlier' (00:40:00), and it is a compatible account of how the ID was confirmed, not a narrowing. → _drop_
- **pair 65 (C-3944 → C-3957)**: The witness going from 60-65% to 100% once given the right Neff is consistent with the positive ID; it is an added detail, not a qualification. → _drop_
- **pair 67 (C-4064 → C-4068)**: Both lines carry the same 'cannot confirm' caveat a minute apart; the 'they' wording is a difference between sources (TPUSA vs her informant), not her narrowing her own claim. → _drop_
- **pair 68 (C-4409 → C-4408)**: The 'later' (00:32:56) comes before the 'earlier' (00:33:21), and the two lines are compatible statements that everything else is verified. → _drop_
- **pair 69 (C-4466 → C-4470)**: The earlier already places the sighting on the 8th; saying he did not see her on the 9th repeats that, it does not narrow it. → _drop_
- **pair 71 (C-4595 → C-4596)**: 'At least since 2014 on paper' and 'an indication it was earlier' are compatible and said 20 seconds apart; nothing is narrowed. → _drop_
- **pair 73 (C-4599 → C-4604)**: Not the same thing: the earlier concerns the 888 plane owners' charity, the later disclaims any suggestion about TPUSA. → _drop_
- **pair 85 (C-2134 → C-13613)**: The later only relays TPUSA's and Erika's private rebuttal; nothing shows the host adopting it or narrowing her own claim. → _drop_
- **pair 86 (C-13695 → C-13696)**: The later explains why George knows Hebrew in reply to a smear she describes; it does not narrow her own earlier claim. → _drop_

## B2: material findings (80)

- **pair 88 (C-455 → C-456)**: Correction record: the later claim is a spelling/name note restating the same host statement, so both sides are the same speaker and the claims agree. → _drop_
- **pair 89 (C-847 → C-848)**: Correction record: the later claim is a spelling/name note restating the same host statement, so both sides are the same speaker and the claims agree. → _drop_
- **pair 90 (C-861 → C-862)**: Correction record: the later claim is a spelling/name note restating the same host statement, so both sides are the same speaker and the claims agree. → _drop_
- **pair 91 (C-853 → C-854)**: Correction record: the later claim is a spelling/name note restating the same host statement, so both sides are the same speaker and the claims agree. → _drop_
- **pair 92 (C-2448 → C-2449)**: Correction record about C-2448's title; both sides are the same Stuckey tweet and the claims agree. → _drop_
- **pair 93 (C-2940 → C-2988)**: Not cross-speaker: the host misread the plates herself and later corrects her own reading, so this is a host-vs-herself revision, not a host-vs-other pair. → _drop (re-file as host_vs_herself revises)_
- **pair 94 (C-3183 → C-3273)**: The earlier claim is the content of Tucker Carlson's speech; the host's later correction is about the date she gave, which the earlier claim does not state, so they are not about the same thing. → _drop_
- **pair 95 (C-5800 → C-5802)**: Both sides are the same Bassem Youssef statement in the same clip and agree; duplicate/correction record, no host side. → _drop_
- **pair 97 (C-11568 → C-11567)**: The memo's injury details and the host's correction of who filed the memo (prosecution, not defense) are not the same specific claim, and the 'later' timestamp precedes the 'earlier'. → _drop_
- **pair 98 (C-11570 → C-11567)**: The memo's heart/lung hemorrhage detail and the host's correction of who filed the memo are not the same specific claim, and the 'later' timestamp precedes the 'earlier'. → _drop_
- **pair 99 (C-11819 → C-11898)**: Both sides are the host's own words (C-11819 is Candace Owens herself), so this is a host-vs-herself revision on Catholic cremation, not a cross-speaker pair. → _drop (re-file as host_vs_herself revises)_
- **pair 100 (C-12143 → C-12142)**: Speaker-attribution correction record: both sides are the same Erika Kirk clip line and agree. → _drop_
- **pair 101 (C-12228 → C-12230)**: Correction record: the later claim is a spelling/name note restating the same Kolvet statement, so both sides are the same speaker and the claims agree. → _drop_
- **pair 102 (C-12428 → C-12423)**: Correction record: the later claim is a spelling/name note restating the same host statement, so both sides are the same speaker and the claims agree. → _drop_
- **pair 103 (C-13892 → C-13894)**: Correction record: the later claim is a spelling/name note restating the same host statement, so both sides are the same speaker and the claims agree. → _drop_
- **pair 104 (C-13941 → C-13944)**: Correction record: the later claim is a spelling/name note restating the same host statement, so both sides are the same speaker and the claims agree. → _drop_
- **pair 106 (C-361 → C-362)**: Speaker-attribution correction record for the same Tucker Carlson clip line; the claims agree. → _drop_
- **pair 108 (C-464 → C-460)**: Duplicate of pair 109 (same two claims, C-460/C-464) in reversed order. → _drop_
- **pair 110 (C-464 → C-462)**: Host's TPUSA tour claim and Bolling's 'quiet breakup / too rabbit hole' remark are about different things (event appearances vs the relationship), and the order is swapped. → _drop_
- **pair 112 (C-72 → C-442)**: Netanyahu's 'it pains me to see support for Israel slip away' quote is not tied to the May 2 letter and is compatible with Kirk being concerned, so it does not contradict C-72. → _drop_
- **pair 115 (C-464 → C-479)**: The host's TPUSA tour claim and the Daily Mail 'no communication for many years' line are not the same specific claim; the host's direct rebuttal is C-553 (pair 122). → _drop_
- **pair 117 (C-531 → C-532)**: Speaker-attribution correction record for the same PBD 'receipts' line; not a disagreement between speakers. → _drop_
- **pair 118 (C-540 → C-534)**: Duplicate of pair 119 (same two claims, C-534/C-540) in reversed order. → _drop_
- **pair 120 (C-534 → C-535)**: Speaker-attribution correction record (board/last-sighting answer belongs to Bolling, not Kolvet) for the same PBD exchange; claims agree. → _drop_
- **pair 123 (C-458 → C-581)**: C-458 and C-533 are the same PBD line ('Andrew Kolvet was there in the room'), aired in ep 5 and replayed in ep 6; pairing both with C-581 duplicates pair 124. → _drop_
- **pair 130 (C-1358 → C-1363)**: Neither side is the host: Kolvet vs Bowyer, both third parties. → _drop_
- **pair 131 (C-1363 → C-1358)**: Neither side is the host (Bowyer vs Kolvet), and it duplicates pair 130 in reversed order. → _drop_
- **pair 134 (C-711 → C-1367)**: Kolvet's theft/evidence reason does not claim police asked staff to secure the footage, so the host's line about Bowyer's police claim does not contradict it. → _drop_
- **pair 145 (C-2748 → C-2740)**: Neither side is the host's own words: a Camino clip vs an LA Times article the host reads (both host_voice false); 'later' is also earlier in the episode. → _drop_
- **pair 148 (C-2927 → C-2968)**: Neither side is the host (show director Mark vs a friend's text the host reads), and it is a time-zone correction of the same data rather than a disagreement. → _drop_
- **pair 149 (C-2924 → C-2968)**: Neither side is attributed to the host (director Mark vs a friend's text), it is a UTC-offset correction record, and it near-duplicates pair 148. → _drop_
- **pair 150 (C-3106 → C-3113)**: Both sides are the host (the 'later' side is her own conclusion though tagged OTHER) and they agree that Harpole claimed no drones and lied. → _drop_
- **pair 153 (C-4104 → C-4101)**: Both sides are the host (the earlier is the host describing call logs, mis-tagged OTHER) and they agree; Neff's account should be the other side. → _drop_
- **pair 159 (C-6009 → C-6007)**: Neither side is the host and both are the same speaker (two Shapiro clips), with Shapiro relaying Bennett's denial against Tucker's claim. → _drop_
- **pair 170 (C-8289 → C-8208)**: Neither side is the host (CBS article vs Kolvet clip); 'later' is also earlier in time, and pair 172 duplicates it in reverse. → _drop_
- **pair 171 (C-8289 → C-8225)**: Neither side is the host (CBS article vs Erika's X post), and pair 173 duplicates it in reverse. → _drop_
- **pair 172 (C-8208 → C-8289)**: Neither side is the host (Kolvet clip vs CBS article) and it duplicates pair 170 in reverse order. → _drop_
- **pair 173 (C-8225 → C-8289)**: Neither side is the host (Erika's X post vs CBS article) and it duplicates pair 171 in reverse order. → _drop_
- **pair 174 (C-8289 → C-8290)**: The two claims agree: the host cites the CBS report to dispute Erika; CBS is not her opponent (pair should be Erika/Kolvet vs host). → _drop_
- **pair 176 (C-8596 → C-8598)**: The later side is mainly a viewer comment the host reads (host_voice false), not the host; the host's own denial is already paired in 177. → _drop_
- **pair 185 (C-9454 → C-9456)**: Both sides are Victor Marx and they agree ('helped' not 'rescued', some rescued). → _drop_
- **pair 186 (C-8169 → C-9479)**: Neither side is the host: Corby Hall's written statement vs Victor Marx's denial are both third parties. → _drop_
- **pair 208 (C-13293 → C-13241)**: This duplicates pair 212 in the opposite order (C-13241/C-13293), and 'earlier' is from ep154 while 'later' is ep153; the claims are not about the same specific thing either (see 212). → _drop_
- **pair 212 (C-13241 → C-13293)**: These are not the same specific thing: the notice's conclusion that UVU's misconduct caused the death vs ABC's report that TPUSA declined an ambulance on the form are rhetorically opposed but both can be true. → _drop_
- **pair 218 (C-13914 → C-13904)**: This duplicates pair 219 (same claims C-13904/C-13914, reversed), and its order is swapped (00:21:21 before 00:12:06). → _drop_
- **pair 219 (C-13904 → C-13914)**: Neither main claim is the host's own words (Discord messages vs Kolvet's Atlantic denial), and the messages do not show TPUSA working with the Latvian firm. The host-side rebuttals are covered by pairs 220 and 221. → _drop_
- **pair 223 (C-105 → C-107)**: Both sides are the same Charlie Kirk clip (same speaker, overlapping and agreeing text), so this is not a host-vs-other pair. → _drop_
- **pair 224 (C-361 → C-368)**: Both sides are the same speaker (Tucker Carlson in one clip), and the host is on neither side. → _drop_
- **pair 225 (C-527 → C-528)**: Both sides are the same viewer email/write-up with overlapping text, and the host is on neither side; this is effectively a duplicate. → _drop_
- **pair 226 (C-776 → C-825)**: This is a correction record: the viewer fixes the church's name, which is not the host's Beehive State claim, and the host accepts the fix. → _drop_
- **pair 227 (C-1108 → C-1109)**: The host's caveat qualifies her own hunch about Mitchell, not anything the 1999 article claims, so this is host vs herself. → _drop_
- **pair 228 (C-1885 → C-1897)**: This is a correction record: both sides are the host, and the later is her misspoke fix (UVU vs Utah Valley Hospital). → _drop_
- **pair 232 (C-2051 → C-2052)**: This is an attribution correction (which show the Seth Dillon clip came from), and the earlier claim already contains it; it is not a substantive disagreement. → _drop_
- **pair 233 (C-2001 → C-2060)**: The claims agree: the plane was over Provo only about 20 to 26 minutes after the shot, and Mark's screenshot supports the host rather than qualifying her. → _drop_
- **pair 234 (C-2510 → C-2512)**: The claims agree: the article's 'March 25th' and the host's '2024' describe the same event, and neither side is a different speaker's claim (both are the host reading or commenting). → _drop_
- **pair 235 (C-2715 → C-2716)**: Both sides are the host's own reading of the same Kanye tweet at the same timestamp; same speaker, same statement, no tension. → _drop_
- **pair 236 (C-3588 → C-3589)**: The host does not dispute the calendar entry; she hedges her own insinuation about the call, so the two claims agree. → _drop_
- **pair 237 (C-3610 → C-3612)**: Both sides are Blake Neff's same post (tweet summary vs host's reading of it); same source, agreeing. → _drop_
- **pair 240 (C-3690 → C-3687)**: Both sides are the host's own statements about Kasparian's earlier post; same speaker and they agree. → _drop_
- **pair 241 (C-3923 → C-3924)**: Both sides are Tucker Carlson in the same Theo Von clip; neither side is the host. → _drop_
- **pair 242 (C-3952 → C-3959)**: Both sides come from the same tipster email (12:31 vs 11:43 departure); an internal discrepancy in one source, not host vs another speaker. → _drop_
- **pair 247 (C-4179 → C-4184)**: Later claim is about Kolvet's separate ricochet statement versus the frangible account, not the surgeon quotation in the earlier claim; not the same specific thing. → _drop_
- **pair 248 (C-4238 → C-4239)**: Both sides are Brian Harpole in the same clip saying the same thing (Aug 24 start, intelligence before); same speaker, agreeing. → _drop_
- **pair 251 (C-4609 → C-4610)**: Host does not dispute the website's summit date; she hedges her own coincidence inference, so the claims agree. → _drop_
- **pair 257 (C-6757 → C-6759)**: Both sides are Tim Dillon in the same played clip; neither side is the host. → _drop_
- **pair 258 (C-6757 → C-6760)**: Both sides are Tim Dillon in the same played clip; neither side is the host. → _drop_
- **pair 259 (C-6781 → C-6779)**: Host introduces the headline and the headline says the same thing; the claims agree. 'Later' (00:40:38) also precedes 'earlier' (00:40:50). → _drop_
- **pair 260 (C-6790 → C-6789)**: Host merely introduces Gantz's clip; her title for him and his statement are not competing claims about the same thing. → _drop_
- **pair 264 (C-6997 → C-6999)**: Both sides are Erika Kirk's same clip statement; the later is an attribution/wording correction of the host's characterization, not a host vs other-speaker pair. → _drop_
- **pair 266 (C-7985 → C-7988)**: Both sides are from the same Tucker Carlson letter; neither is the host's own words. → _drop_
- **pair 267 (C-8182 → C-8204)**: Both sides are the host's own statements (her belief in Corby Hall's account vs her uncertainty about the gun); not cross-speaker. → _drop_
- **pair 268 (C-8662 → C-8726)**: Both sides are the host (her earlier defense of Harpole vs her later saying she was wrong); this is a host-vs-herself revision, not a cross-speaker pair. → _revises (reclassify host_vs_herself: true)_
- **pair 270 (C-10782 → C-10786)**: Both sides are Sergeant Faumuina's same hearing testimony; neither is the host. → _drop_
- **pair 271 (C-10873 → C-10874)**: Both sides are Officer Bagley's same testimony; neither is the host. → _drop_
- **pair 273 (C-11241 → C-11244)**: Host's later caution targets her own two-phone inference (in the earlier claim's note), not Neff's 'I put that phone away' statement. → _drop_
- **pair 275 (C-11521 → C-11523)**: Host only says she has never heard Neff's claim before; she neither narrows nor disputes it, so there is no qualification. → _drop_
- **pair 277 (C-11570 → C-11571)**: Host does not dispute the memorandum's hemorrhaging finding; she draws an inference from it, so the claims agree. → _drop_
- **pair 278 (C-12153 → C-12184)**: The later side is parody dialogue in an AI video, not a factual claim, and agrees with the host that Wilson repeated 'positive evidence'. → _drop_
- **pair 280 (C-12570 → C-12571)**: Both sides are Jack Hibbs (with Turek) in the same interview clip; neither is the host. → _drop_
- **pair 281 (C-13551 → C-13561)**: Both sides come from the same review timeline and concern different facts (Sept 3 ticketing vs 11:00 a.m. staffing request); not the same thing and not host vs other. → _drop_

## C: material findings (31)

- **C-123**: Stated as fact, not as host's account. Host: 'at 12:29 p.m., we have TMZ showing us... a person running'; 'very grainy'; 'they're alleging that that's him. We couldn't confirm that and the feds have not confirmed'. 'Released at 12:29' is not said; 12:29 is her timeline time. → _The host says that at 12:29 p.m. TMZ footage shows a person running through a backyard, which TMZ says appears to be the suspect; she says it is very grainy and neither she nor the feds have confirmed_
- **C-254**: Clip words given to Kirk are Megyn Kelly's: after the 'kneejerk... very irritating... Epstein... Mossad' monologue, Kirk replies 'I would second that, Megan' (53:07). Host's 'take Charlie in his own words' misleads. Claim C-257 correctly gives these words to Kelly. → _The host says Charlie Kirk appeared on Megyn Kelly on August 6, the day after the Ackman meeting, and plays a clip in which Kelly says some in the pro-Israel camp are so kneejerk about calling people _
- **C-1026**: No Transcript Snippet and range timestamp '00:34:00-00:35:30'. Lyman's Instagram clip begins ~34:57 ('Hey, it's September 10th, 2025 and I was just heading back') and '200 yard kill shot' is ~35:49, >75s after 34:00. → _Claim Timestamp: 00:34:55; Transcript Snippet: I was just heading back from Salt Lake to Blanding._
- **C-1158**: No Transcript Snippet; Graf/coroner content is at ~6:17+ (>75s after 4:53). Claim says officials 'involved in the case' incl. Zenger, but host said 'it would be interesting to learn whether or not that new CEO and surgeon worked on Charlie'. 'FBI SAC' not said (host: Patel 'installs' Bohls). → _The host says several people connected to the case were new in their roles: Robert Bohls, installed by Kash Patel after a long DC tenure; Andrew Zenger, the new hospital CEO (she wants to learn whethe_
- **C-1486**: Transcript [41:24] segment is empty: nurses/doctors, 'not yet been paid' and 'vetted' tip are not in excerpt. [42:20] only says 'relatively strong tip... I'm not saying they are... Why wouldn't George Zinn know where the payment was coming from?' Privacy: private individual, medical setting. → _Re-check against video/HappyScribe; if content is at 41:24 keep ts, else move; drop 'vetted' unless the host says it; add her hedge 'I'm not saying they are'._
- **C-1962**: Claim sentence is hedged ("found only one"), but title states as fact "Trump's Only 'Investigation' Truth Social Post Was About Jack Smith's..."; host said "only one tweet that we could find". Title drops the hedge. → _Title: Host Says the Only Trump Truth Social Post Her Team Found on an 'Investigation' Was About Jack Smith's TPUSA Probe, Not Kirk's Murder_
- **C-2570**: Host's own appositive "uh the alleged person who dropped off these pipe bombs" is put in quotes inside what CIA spokeswoman Liz Lyons "stated", so it reads as a CIA characterization. Privacy flag: crime allegation against a private individual plus her town (Alexandria, VA). → _The host says CIA spokeswoman Liz Lyons stated that Shauni Kerkhoff worked in Capitol Police campus security; the host calls Kerkhoff "the alleged person who dropped off these pipe bombs" and adds tha_
- **C-3237**: Host is mocking the official account as 'the tin foil hat conspiracy theory... I don't want you guys to believe that'; claim presents 'Robinson wrote every minute of the crime to his partner' as her assertion, with only the GPA attributed to the official account. → _The host mocks the official account, which she calls 'the conspiracy theory', in which Robinson, said to have about a 4.3 GPA and be a 'boy genius', texted every minute of the crime to his partner; sh_
- **C-3755**: Omits what host read next: 'then he gets cleared on an appeal, okay? So, technically he was found not guilty of this crime and then was sentenced to a reduced 2 and 1/2 years'. Title states conviction as standing fact. → _According to 'Corruption Tracker' material the host reads, Pierre Falcone was convicted of arms trafficking, breach of trust, misuse of corporate assets and bribery and sentenced to six years, but was_
- **C-7228**: Title 'Netanyahu Misses Security Council Meeting' states as fact what the host hedged: 'despite being there, allegedly, he missed the Security Council meeting, which is purportedly highly unusual'. Claim sentence itself keeps the hedges. → _Title: Host Says Netanyahu Allegedly Missed a Security Council Meeting_
- **C-7328**: 'speculation she was "Charlie's handler"' appears nowhere in the clip excerpt. Clip says 'some weird CIA documents or CIA films... internal films' (not a documentary) and 'Wasn't she in like Miss USA'. Speakers in the clip are not individually identified. → _In a clip of his podcast that the host plays, Joe Rogan and his guest discuss Erika Kirk appearing in what one calls 'weird CIA documents or CIA films' and her pageant background._
- **C-7441**: Title 'Stacy Sheridan Was Not at TPUSA Offices on September 10' states the host's assertion ('I can confirm she was not at the Turning Point USA office') as established fact. Claim sentence is correctly framed. → _Title: Host Says She Can Confirm Stacy Sheridan Was Not at TPUSA Offices on September 10_
- **C-7544**: Title 'Kolvet fed information to podcasters to attack the host over Fort Huachuca' states the host's allegation as fact. Claim sentence ('The host alleges') is fine; 'Some fort. Said Andrew' is the host's mocking paraphrase, not a sourced quote. → _Title: Host Alleges Kolvet Fed Information to Podcasters to Attack Her Over Fort Huachuca_
- **C-8265**: Claim says brother is 'still involved in the trafficking game' but omits host's immediate hedge: 'Is it charitably? ... I can't be sure' and 'these people are not involved in the trafficking. They are charitable' (brother runs anti-trafficking consultancy). Privacy flag: private relative. → _The host says that, according to current and former employees, Marcus Wada says his brother is still involved 'in the industry in some way'; she adds she cannot be sure whether this is charitable, tha_
- **C-8357**: Host introduces 'Top comment from yesterday's episode' and then reads it: 'Where was all of this amazing security when Charlie said they're going to kill me? They were receiving his messages. Dan Flood...' These are the viewer's words, not the host's; she reacts after ('Totally normal'). → _The host reads a top viewer comment saying Dan Flood was receiving Charlie's messages that they were going to kill him._
- **C-9724**: Body attributes ('The host says'), but title 'More than 60 million Russian Christians were murdered under communism' states the host's contested figure as fact. → _Title: Host says more than 60 million Russian Christians were murdered under communism_
- **C-9768**: Title 'Erika Kirk is treated as an "emotional asset" and the Department of War was involved in the emails' states as fact what host hedged: 'it looks like the Department of War was who was involved'. Body fine. → _Title: Host says Erika Kirk is considered an "emotional asset" and the Department of War appears involved in the emails_
- **C-9770**: Title 'Erika Kirk cut short her WLS speech...' states as fact what host sourced: 'I was told that. Um I'm told she shortened it.' Body keeps 'According to the host's sources'. → _Title: Host says she was told Erika Kirk cut short her WLS speech after being called a "pedophile protector"_
- **C-9776**: Title 'Greg Laurie is accused in court of trafficking people from Romania' states host's characterisation as fact; the suits accuse Havsgaard of abuse and name Laurie/Harvest for negligence. Body ('as she says') is fine. → _Title: Host says Greg Laurie is credibly accused in court of trafficking people from Romania_
- **C-9870**: Drops hedge: host says 'My understanding... of what he means is that this story... terrified Dan Bongino and terrified Kash Patel'. Tucker only said Bongino was terrified; Patel is the host's inference. → _Recapping Tucker Carlson's account..., the host says her understanding of what Carlson means is that the Butler story, "perhaps the butler cover up", terrified Bongino and Patel._
- **C-9876**: Host frames it as a premise ('If you almost get assassinated, and you do not fire the Secret Service agents... you determine that you are satisfied'); title 'Trump did not fire the Secret Service agents who failed at Butler' states it as fact. → _Title: Host says Trump did not fire the Secret Service agents who failed at Butler_
- **C-9903**: Title 'Erika Kirk had Kolvet deny the Catholic account and okayed Alex Clark calling the host a liar' states the host's allegation as fact; body ('The host alleges') is fine. → _Title: Host alleges Erika Kirk had Kolvet deny the Catholic account and okayed Alex Clark calling her a liar_
- **C-9955**: Title 'The Comperatore family is not satisfied with the Butler investigation' drops host's sourcing ('I have it on authority'); body keeps it. → _Title: Host says she has it on authority the Comperatore family is not satisfied with the Butler investigation_
- **C-10089**: Host is mocking the 'trans fairy' account ('We're supposed to believe he thought he was going to be killed by a trans fairy'); she rejects it (ep119). Claim presents it as her assertion. → _...he wrote on a group text, "You guys keep the money. I don't want it." She says his phone held texts expressing fear he would be killed, and mocks the account that he feared a "trans fairy" would ki_
- **C-10842**: Snippet 'I think that is the reason they are avoiding him because he is a credible witness' is near the end of the 43:22-44:53 block, est. ~44:43, about 81s after 00:43:22. → _00:44:30_
- **C-11893**: Piers's 'local law enforcement and sheriffs in the Mississippi area... have said there are no records' is spoken about 45:25-45:48, inside the [44:38] block; at 45:49 Marx's answer begins, so the link lands after the statement. → _Claim Timestamp: 00:45:20_
- **C-12046**: Claim and title use 'Hoole', a mis-transcription of FBI Agent Hull (transcript: 'Agent Hull's testimony'; transcript_name_corrections maps 'Agent Hoole' -> 'Agent Hull' for ep 140). Node N-860 David Hull is right. → _Title: Host Says She Wrongly Assumed Robinson Was Pulled Over and Now Reads Hull as Saying He Stopped to Ask an Officer. Claim: ...after re-listening to Agent Hull's testimony she thinks Hull is sayin_
- **C-12172**: Wilson says 'I think he's been charged with murder' / 'That's actually incorrect'; Wilson then says 'name all seven' and it is Owens who starts 'the first charge is aggravated murder because that's what carries the death sentence' and explains it. Claim gives her listing to Wilson. → _In a clip the host plays from the debate, when challenged to name any of the seven charges Tyler Robinson faces, Andrew Wilson said he thought Robinson had been charged with murder, which Owens said w_
- **C-12403**: Speaker is Blake Neff, not Kolvet: Kolvet says 'And Blake, you have that great video... Blake was early on', then Blake: 'I put out that tweet... Candace, your central foundational lie...'. Investigative Direction already says 'Neff's tweet'. Mentions N-14 should be N-159. → _Blake Neff says he tweeted that her central foundational lie is that she and Charlie were friends, asking for proof from the last 12 months, then 18 and 24 months, and that he thinks she showed someth_
- **C-13019**: Start 00:11:11 is inside the Sausalito/Turek clip; host's own words ('euphemisms for lie... discrepancy... incongruity... irrelevant detail... irrelevant consequence... it feels very relevant', 'as Bobby pointed out') are ~13:20-13:45 in [12:50] block, >75s after 11:11. → _Claim Timestamp: 00:13:10_
- **C-14224**: 'Erika has betrayed Charlie's legacy' is inside viewer Ali's comment the host reads ('Ali writes, "...because Erika has betrayed Charlie's legacy?"'); only 'obviously she doesn't author her tweets' is the host. Snippet is in [52:46] of full transcript (pack excerpt cut it); timestamp ok. → _After reading a viewer comment saying Erika has betrayed Charlie's legacy, the host says that "obviously" Erika Kirk does not author her own tweets._

## D: material findings (3)

- **C-1433**: Kolvet's line "I did share it with some people in government ... took 33 hours ... I shared it with a few people" sits at the end of the [13:40] block, est. ~15:00-15:15, so 15:24 lands after it. Quote "a few people in government" is stitched; "publicly identified" adds to "get their suspect". → _Timestamp 00:14:58. Claim: In the clip, Andrew Kolvet says he shared the screen grab with some people in government in the first moments, noting it took 33 hours for authorities to get their suspect._
- **C-1676**: At ~39:33 host says "It went to Page, Arizona"; the "intended destination" content ("it was supposed to land in Page, Arizona ... Million Air FBO. Last second, it made a change") is in the [40:07] block, est. ~40:30, about 80s after 00:39:09. → _Timestamp 00:40:07_
- **C-6928**: No snippet. The license material starts in the 14:38 segment ('I am indeed able to find a relic of it on a third-party site', licence number, 'issued on October 24th of 2018'); only 'valid at least until 2020' falls at 15:31, so the link lands ~40-50 s after the core content. → _00:14:38_

