# CKA daily 2026-10-21: Ep 405 (seq 168)

The run followed `docs/daily/RUNBOOK.md` headless. A second new upload ("Hocus Pocus!", `ZxlvNO8OVmc`) had no captions
yet, so it waits for the next run. No new @RealCandaceO posts came in, so step T (tweets) did not run.

| seq | Ep | date | YouTube | claims |
|---|---|---|---|---|
| 168 | 405 (inferred; the title has no number) | 2026-10-20 | ihLQRXxIfjU | 81 (C-14475–C-14555) |

- **New nodes (batch `daily-2026-10-21`):**
  - Persons: Lee Harvey Oswald (N-972), Carl Bernstein (N-973), Brian Cole Sr. (N-974), Kimberly Guilfoyle (N-975)
    and Eric Deters (N-976).
  - Topics: Brian Cole Jr. January 5 Alibi Footage (N-11362), Losee Rooftop Return Figure ("Slenderman")
    Identification (N-11363) and Kimberly Guilfoyle Ambassadorship Resignation (N-11364).
  - No new memes; 20 existing memes recur.
- **Intro move:** Lee Harvey Oswald (N-972) was already named in ep48 (C-4259) and ep87 (C-7835). His introduction
  moved to ep48 (`Tip-minted Nodes (reintro-ep048)`), with the id unchanged. Ep87 C-7835 and ep168 now cite him as
  a reused node.
- **Name rules:** there are 16 new rules and 9 existing scoped rules extended to seq 168.
  - The new rules are scoped to seq 168, except "Kimberly Gilfoil/Goofoil/Gilfeld/Gilffill" → Kimberly Guilfoyle,
    which is global.
  - Examples: Losee rooftop (Losi, Loi, Losy, Loy and "low seat"), Eric Deters, Jeremy Boreing, Yashar Ali,
    Scripps Media, Director Kash, AmEx, Latvian and Togepi.
  - Extended to seq 168: Dan Bongino, Kathy Nester, Bagley, Tyler Bowyer, candaceowens.com, Erika, Katie Zacharia,
    Brian Cole Jr. and Tucker Carlson.
  - The rules hit no older transcript.
  - Not turned into rules:
    - "Howard Scripps", because the host may have said it herself;
    - "lawyer building", which is medium confidence;
    - "Steve Steven Baker", a stutter;
    - "non-rime" and "pathy", which are not names.
- **Opus check at intake:**
  - 81 claims were checked in 2 chunks. There were 5 material findings, all wrong Mentions. The confirm pass
    accepted 4 and amended 1 (C-14546 also gets Eric Trump). The material rate at intake was 6.2%.
  - 12 fixes were applied: 5 material and 7 minor. The minor ones include 6 Daily Wire firing claims retagged
    tangential.
  - The confirmed fix that added Kash Patel (N-69) to C-14528 was reverted. It rests only on inference: the
    caption reads "FBI now", and the gate found no grounding.
  - No name fixes.
- **Gates:** `finalize.py 168 --pytest` passes everything, with 86 tests.

## Review items
1. **Second trading card, "FBI now"** (C-14528, 00:31:11, https://youtu.be/ihLQRXxIfjU?t=1871).
   - Transcript: "We're also keen to release this one. FBI now. I mean, obviously the points here are 33 33. See you
     in Valhalla."
   - The details fit Kash Patel (possibly "FBI Kash"), but the name is not audible in the captions, so no person is
     cited. HappyScribe has not posted Ep 405 yet.
2. **Unnamed speakers in the Brian Cole Jr. clips** (00:07:27, https://youtu.be/ihLQRXxIfjU?t=447; 00:09:05,
   https://youtu.be/ihLQRXxIfjU?t=545).
   - One speaker says he found the jacket in Cole's room. The other refers to "Brian Senior" in the third person.
   - A web search did not identify them.
3. **Cole family, private individuals (possible privacy hit).**
   - C-14499 and C-14500 (00:09:58, https://youtu.be/ihLQRXxIfjU?t=598; 00:10:55,
     https://youtu.be/ihLQRXxIfjU?t=655) relay that Cole's mother handmade his masks and cried when she saw the
     mask.
   - In the clip, the speaker says he did not get "Brian Senior's" permission to share this.
   - Cole's grandmother is named "Loretta" (first name only) in Steve Baker's X post (A-3425.2, 00:08:31,
     https://youtu.be/ihLQRXxIfjU?t=511).
   - No nodes were minted for the mother or grandmother. Brian Cole Sr. is N-974.
4. **"Kelly Fuller"** (00:33:54, https://youtu.be/ihLQRXxIfjU?t=2034). This is a private X user in a thread with
   Jeremy Boreing that the host reads. The name is unconfirmed and no node was minted.
5. **"Howard Scripps"** (00:05:39, https://youtu.be/ihLQRXxIfjU?t=339): "Then it was Howard Scripps and he named
   them explicitly."
   - It is probably Scripps-Howard, but the host may have said it that way, so no rule was added.
6. **"The lawyer building"** (00:22:16, https://youtu.be/ihLQRXxIfjU?t=1336), in the Bagley hearing clip:
   ">> The lawyer building."
   - It is possibly "the Losee building". This is medium confidence, so no rule was added.
7. **Who reported the $100,000 request.** The host credits Axios, but news reports trace Eric Deters' account to The
   Wall Street Journal. The claims attribute it to the host.
