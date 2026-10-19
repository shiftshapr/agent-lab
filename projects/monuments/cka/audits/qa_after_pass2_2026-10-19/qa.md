# CKA QA after pass 2 (2026-10-19)

Sample: 278 of 13915 claims (rate 0.02, seed 20261019, whole archive).
Every sampled claim was reviewed.

**Material-error rate: 0.7%** (2 claims; target < 2%: met).

| Check | Results |
|---|---|
| attribution | ok 278 |
| accuracy | minor 13, ok 265 |
| person | error 1, ok 277 |
| timestamp | error 1, ok 277 |
| relevance | disputed 8, ok 157, untagged 113 |

## Material errors

- **C-10792** (ep13): Related Nodes include N-10898 'New York Post', but the host cites 'the New York Times has reported on uh Russian Ukrainian spies' (~20:38). Wrong outlet node. Proposed: Replace N-10898 (New York Post) with N-10968 (The New York Times) in Related Nodes.
- **C-1557** (ep23): Snippet 'He said he called him 2 weeks ago and he invited him to Israel' is in the [36:19] block, ~40-55s before the 00:37:15 Claim Timestamp (limit ~20s before). Proposed: Claim Timestamp: 00:36:19

## Minor findings

- **C-13592** (ep3): Tagged context, but the content is a viewer comment alleging Cox 'stole the election' (Utah 2024 race) and host says 'I obviously know nothing about that election'; unrelated to the assassination, so tangential. Proposed: relevance:tangential
- **C-3773** (ep10): Revision text says C-1295 spells the name 'Bill Ackman' and corrects it to 'Bill Ackman': the two spellings are identical, so the revision is a no-op. The substantive sentence matches [03:04] ('959 words... did not actually address... intervention'). Proposed: Drop the spelling-revision sentences or state the actual variant used in C-1295.
- **C-1717** (ep33): Crowder says Candace put Erika 'in the crosshairs' and 'Either Erika Kirk is evil and was in on it or Candace Owens is evil'; 'accused Erika of murdering her husband' is the host's paraphrase of his reading, slightly stronger than his words. Proposed: Steven Crowder, in a recorded clip played during the episode, asserted that Candace Owens' book club remarks put Erika Kirk 'in the crosshairs', saying either Erika Kirk 'was in on it' or Candace Owens is evil.
- **C-4970** (ep34): Claim text uses the transcript form 'Tim P'; the person is Tim Pool (N-267). Prefer the canonical name in the Claim sentence. Proposed: The host says she saw a clip on X of Tim Pool saying that people were investigating for clicks when she started the investigation, and says she has no response.
- **C-9780** (ep37): Relevance: a date correction for Tucker Carlson's speech (July 11 vs 18) is timeline background, better 'context' than 'core'.
- **C-3654** (ep48): Transcript: 'When I say investigators, I mean like mommy sleuths and investigators on the ground who have been looking into this story and not accepting the feds flop.' Nothing here about emailing tips; she says she intends to partner with them. Proposed: The host says that by investigators she means 'mommy sleuths and investigators on the ground' who have not accepted the federal account, and says she intends to partner with people doing that work.
- **C-6980** (ep53): Remark is a passing aside while answering a comment about French cattle culls; about Macron's lawsuits, not Kirk. Arguably tangential rather than context.
- **C-8251** (ep54): Host's remark about her vivid dreams and Charlie's 2018 'visions that he was going to die' is not about the assassination or investigation itself; context at most.
- **C-2154** (ep60): Transcript: 'leaving at 2:19 p.m. So, yeah, it's an hour and 5 minutes ... I'm told that Andrew was on that plane.' It does not say the gap is from Kolvet's plane, and which plane Andrew was on is ambiguous. N-217 = Elizabeth McCoy in nodes.json. Proposed: The host says Erika Kirk's plane (N102DZ), carrying a priest, Erika Kirk, Tyler Bowyer and Elizabeth McCoy, left at 2:19 p.m. ('it's an hour and 5 minutes') and arrived in Provo at 4:36 p.m., and that she was told Andrew Kolvet was on one of the two planes.
- **C-8269** (ep62): Excerpt calls the sender a self-described evangelical Christian Zionist; 'donor' is not said here ('say who sent Charlie that message'). Proposed: The host says it is becoming increasingly difficult to imagine how Turning Point is not naming and shaming the sender of the Christian Zionist message to Charlie, and challenges TPUSA to say who sent it.
- **C-2433** (ep76): The comments about Erika were Blake Neff's ('portion of him discussing Erika'); 'his comments' after 'Charlie Kirk podcast episode' reads as Charlie's. Proposed: A message relayed via the host's producer says Blake Neff confirmed the full Charlie Kirk podcast episode, including Neff's own comments about Erika, remains intact on Rumble; only the Twitter stream version was trimmed.
- **C-12744** (ep78): Tips requested here concern Nelda Buckman's adoptions and Next Model Management, not the assassination; 'context' fits better. Tag field also carries a stray 'dia' value. Proposed: Tags: relevance:context
- **C-3753** (ep118): Host says 'I'm going to show you this moment, how she dresses to go pick up her 5-year-old son' but the passage she then reads is about the 'villain... Poison Ivy, Catwoman' persona, not the pickup outfit. Snippet ~70s after timestamp (borderline ok). Proposed: The host reads the title of Emily Ratajkowski's article in The Cut, "Mother Effer", calls it pornographic in nature, and says she will show the passage describing how Ratajkowski dresses to pick up her 5-year-old son from school.
- **C-4835** (ep119): The 'she used a clip... for PR purposes because she gets heat for the sparklers' lines are likely still viewer Ali's comment (host follows with 'I know. I know.'); host endorses it, so not misleading. Proposed: A viewer comment the host reads says Erika Kirk's Father's Day post quoted Charlie as saying "more fog, more sparklers" and used a clip of him at a TPUSA event with sparklers as PR in response to criticism; the host agrees.
- **C-13097** (ep121): 'the cost' has no referent; transcript is about the Daily Wire's spending on Jeremy Boreing's Pendragon Cycle ('they spent $50 million on just seven episodes'). Proposed: The host says the Daily Wire's spending on the Pendragon Cycle was, as she has long said, more than $50 million, closer to 60, and that earlier reports of $10 million or $7 million were wrong.
- **C-8858** (ep122): Claim accurate. The lawsuit against Next/MC2 is background to the Erika Kirk allegation; 'context' fits better than 'core'.
- **C-7450** (ep134): Claim accurate. Remark is about the show's timing of releases; 'context' fits better than 'core'.
- **C-3375** (ep147): Quoted phrase 'disingenuous narrative' not in transcript; host says Walsh's tweet tries 'to delude the public' and that Walsh did not believe it (41:12). Proposed: The host rejects Matt Walsh's 'justifying political assassination' framing, saying the shared video was meant to delude the public.
- **C-3522** (ep155): Host reads 'Libs of Tik Tok upset prediction markets project Democrats have a 59% to sweep both chambers'; 'on X' and '2026' not stated explicitly.
- **C-11895** (ep155): Host says 'doesn't mean anything at all... a thread that can be pulled'; donation to UVU is background, 'context' fits better than 'core'.
- **C-3625** (ep160): 'I got you covered' was Long's reply to Flood's 'I need somebody on the roofs' text (36:45), not a Flood text. Rest matches. Proposed: ...Turek cites a text exchange Dan Flood showed him, in which Long replied 'I got you covered' to a request for roof coverage, as proof Long had the roofs...
