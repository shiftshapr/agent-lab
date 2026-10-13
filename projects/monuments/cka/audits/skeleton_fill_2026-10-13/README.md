# Skeleton episode fill (2026-10-13)

Fills the 19 CKA episodes whose drafts had empty registers: seq 84, 95, 100, 101, 103–106, 108, 109 and 111–119 (Candace Ep 317–353). Seq 118 had one claim, so it is included.

## Method

1. **Extraction.** One Claude agent per episode extracted the draft from `transcripts_corrected/` following `EXTRACTION_SPEC.md`.
   - Agents used placeholder ids and reused existing node and meme ids from `canonical/`.
   - Every Transcript Snippet was machine-checked as an exact transcript substring (`check_staging.py`).
   - DIA tip-line and bounty beats got the M-12 treatment from `config/dia_scan_terms.json`. This includes the deferred ep101 and ep117 beats from the Wave 3 `dia_gaps_triage.csv`.
2. **Integration.** `cka/scripts/fill_skeleton_integrate.py` assigned global ids in airing order.
   - New persons are Tip-minted from `next_person_id`, and new topic/org/place nodes from `next_investigation_id`. Both are listed on `Tip-minted Nodes (skeleton)` ledger lines.
   - Titles were deduped across the batch by name, with the extra merges in `title_merges.json`.
   - Existing items were kept with their ids: C-3751, C-3753, A-2522, N-16, the N-163 hole-mint, and the meme occurrences.
3. **Intro moves.** These episodes air before many episodes that introduced the people and topics they cite. The 55 nodes in `intro_moved_earlier.csv` therefore now have their introduction in the skeleton episode. That episode carries a `Hole-minted Nodes (reintro-epNNN)` line, and the later episode's New/Hole-minted entry moved to Reused. Node ids are unchanged.
4. **Gate fixes.**
   - Four ungrounded Mentions were dropped (C-4227 N-276, C-4304 N-30, C-4489 N-69, C-4761 N-221).
   - Four "her husband" role references were added to `mention_grounding.reviewed`.
   - Aliases were added: Nicci, Niecy → N-576; Rothschilds → N-532.
   - Three named-before-intro pairs were accepted with reasons: Marco Rubio (ep75), Scott Bessent (ep80) and Katherine Locastro (ep83). The node is minted in this batch, but older claim text already names the person.
5. **Inscriptions and companion.** Inscriptions were rebuilt for the 19 episodes only (series "Candace Kirk Archive", model_version from the draft). Older episodes' inscriptions are unchanged, because the intro moves touch draft ledger lines only. The BRC-222 companion was regenerated.

## Result

| | Count |
|---|---|
| Claims | 1,061 new (C-3777..C-4837) |
| Artifact families | 185 new (A-2525..A-2709) |
| New persons | 114 (N-608..N-721) |
| New topic/org/place | 98 (N-10903..N-11000) |
| New memes | 35 (M-85..M-119) |
| Bridges | 9,288 → 11,580 |

Claim density averages about 56 per episode, against about 20 in earlier waves. Every claim has a verbatim snippet.

## Needs your ear (open after web checks)

Each row has the node, why it is open, what the transcript says, and a link to the spoken moment.

| Node | Name as transcribed | Why open | Transcript says | Watch |
|---|---|---|---|---|
| N-609 | Sergeant Dupey | Sound-alike only: possibly Sgt. Nick Dupaix (Provo PD spokesperson); no source ties him to this call. | "Uh myself and Sergeant Dupey are uh in route to Provo Airport. Uh victim's wife is arriving at 3:30." (ep84 00:02:15) | [clip](https://youtu.be/DEtFh2Ff-58?t=135) |
| N-610 | Jamie (Charlie Kirk's pilot) | No public source names the pilot. | "I know that his first name is Jamie, but that's all I know. I think he might be from Texas and I would like to know more about Jamie." (ep84 00:11:05) | [clip](https://youtu.be/DEtFh2Ff-58?t=665) |
| N-636 | Gustav Anderly | Recipient on the disputed WHMO email as read by the host; no public record. | "Uh Steven Cheung was copied on the email. Um, Ryan Ripian was copied on the email and gentleman named Gustav Anderly was copied on the email." (ep104 00:04:55) | [clip](https://youtu.be/7FS1tUeSfdE?t=295) |
| N-640 | Richard Smaly | Same email; no public record (only an unrelated chemist). | "We covered some of this yesterday with Steven Chong who is the White House communications director. Richard Smaly who is the communications officer" (ep105 00:10:20) | [clip](https://youtu.be/Pb7UlpRdW6U?t=620) |
| N-641 | Michaela Mott | Same email; ep112 reads a fuller "Michaela Mott Marzuka"; no record. | "They also have someone named Michaela Mott who was on this email also Navy." (ep105 00:11:19) | [clip](https://youtu.be/Pb7UlpRdW6U?t=679) |
| N-615 | Father Klein | Weak lead: Fr. Don Kline, St. Bernadette, Scottsdale (Kirk spoke of him); not confirmed as the person meant. | "Dinner that night together, which I am aware of because it was with Father Klein." (ep100 00:21:38) | [clip](https://youtu.be/k1b1NDCrNFs?t=1298) |
| N-704 | Curtis Kolvet | Only source is the host ("Andrew Kolvet's brother Curtis"). | "Andrew Corbett's brother, Curtis, is currently stationed in Romania as a lieutenant colonel." (ep117 00:24:24) | [clip](https://youtu.be/G3zdOeHpvS0?t=1464) |
| N-693 | Courtney Thief | Transcript reads "Courtney Thief, who was a former ATF agent"; no match found. | "Allegedly, Mark A. Ley had confessed to his longtime high school friend just a week before he died um that he had illegally taken some explosives from his job." (ep115 00:08:45) | [clip](https://youtu.be/5NQyGuRYbU8?t=525) |
| N-716 | Robert Golow | Private AV worker the host asks for tips on; no match. | "He was brought on, I am told, of course after I stopped touring with Charlie, when they started doing the redundancy of the microphone in 2024. He's actually fr" (ep119 00:11:31) | [clip](https://youtu.be/VMNWMXX1vO8?t=691) |
| N-690 | Jonathan Barcelo | Named on the host's Long Beach flight list; no public record. | "This July 14th date, Erika travels aboard a private flight to Long Beach, California. She's got Katherine Loccastro." (ep114 00:19:42) | [clip](https://youtu.be/WoXd4oLwd3w?t=1182) |
| N-696 | Don Porter | Tied to Corey Comperatore by the host only; no record. | "It was Corey Comparators a friend who refused to let the circumstances go regarding the Butler assassination. He's actually the one that reached out to me and p" (ep116 00:02:16) | [clip](https://youtu.be/h76ZN-xXC6c?t=136) |
| N-699 | Dan Merrill | Likely "Dan Merrell" (single partisan source); confirm in clip. | "just a few days later, they had sent another government team to go in and to dig out all of the soil. 8 to 10 in of soil." (ep117 00:06:08) | [clip](https://youtu.be/G3zdOeHpvS0?t=368) |
| N-660 | Natalie Jean Beisner | Actress-commentator Natalie Beisner fits; middle name "Jean" unconfirmed; tweet not found. | "So, Natalie Jean Beisner tweeted this. Candace's daughter is going to grow up to be a mega Or in prison or both." (ep109 00:31:07) | [clip](https://youtu.be/BxN2-aeMYIs?t=1867) |

## Resolved since the first push
- **Name checks:** web searches confirmed or corrected 14 names. They are renamed, with the transcribed spelling kept as an alias, and listed in `name_verification.csv` with sources. Examples: Ed Gallrein (was Ed Galvin), Caleb Robinson (was "Kayla Robinson"), Jessica Ghawi (was "Jessica Garza"), Gabrielle Cuccia, Raphael Schreiber, Shawn Chenoweth, Vance Voetberg, Mark and Chris Liti, Delmer Martinez, James Kaddis (likely), Jon Bray (likely), Otto Busher (likely) and Ryan Rippeon (likely).
- **Caleb Robinson** is first named in ep90 (C-2688), so his introduction moved there, with a Mentions link on C-2688.
- **Paramount Tactical split (Daveed):** N-10899 is now **Paramount Tactical**, Gary Melton's channel. The old label "Paramount Tactical Valhalla" is kept as an alias.
  - New org **N-11001 Valhalla VFT**, a separate YouTuber. The ep51 transcript says "Paramount Tactical account in Valhalla", ep97 "Paramount Tactical and the Valhalla guy", and ep100 "You had Valhalla".
  - Valhalla is linked on C-2001 and A-1576.2 (ep51) and on C-3887 and C-3889 (ep100).
  - **Gary Melton (N-628)** is now linked as a person on C-3909 and C-3912 (ep100: "Andrew messaged Gary, that's Paramount Tactical"), and his introduction moved to ep100.
  - Merged claim text that says "Paramount Tactical Valhalla" (ep51) stays as aired.

## Still to do
- Add links between episodes in this batch (e.g. ep106's concession should Qualify the ep104/105 email claims, plus the ep118 self-corrections), and links to later episodes in Wave 4.
- Companion: same-host `Supports:` maps to `isCorroboratedBy` (9 → 114 edges); fix in the companion mapping.
