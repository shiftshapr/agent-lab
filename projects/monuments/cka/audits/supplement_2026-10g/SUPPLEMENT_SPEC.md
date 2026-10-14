# CKA supplement pass spec (pilot)

An earlier pass extracted this episode, but it captured only about a third of the checkable claims. Your job is to find what is MISSING and write only additions. Read SPEC.md in this folder first: every format and rule there applies, including placeholders, verbatim Transcript Snippets, DIA beats, memes and the rule against inventing anything.

Differences from SPEC.md:
- The existing draft `cka/drafts/episode_NNN.md` is the merged record. Its claims, artifacts, nodes and memes are immutable. Do not restate, rewrite or renumber them.
- Read the whole transcript and the whole existing draft. For every substantive, checkable beat that no existing claim covers, write a new claim (C-L#) with its artifacts (A-L#) when something was shown, played or read.
- A beat is "covered" when an existing claim states the same proposition. If an existing claim only partly covers a beat, add a new claim for the uncovered part.
- New claims may cite existing artifacts (A-xxxx.y) and existing claims (Supports / Contradicts / Revises), including claims in this same episode. You may also link to earlier episodes via `claims_index.tsv`.
- New nodes (N-P#, N-T#) and new memes (M-N#) are allowed under the same rules. Reuse existing ids first.
- In the Node Register, add rows only for nodes your new items cite that have no row in the existing draft.
- Add meme occurrences only if they are not already in the draft.

Output `staging_supplement/episode_NNN.md` with only these sections:
```
## 3. Artifact Register   (new artifacts only)
## 4. Node Register        (new rows only)
## 5. Claim Register       (new claims only)
## 6. Meme Register        (new memes/occurrences only)
## 7. Coverage Notes       (bullets: how many existing claims, how many beats you judged covered, how many you added, and the 5 most important things the earlier pass missed)
```

## Relevance tag (required on every new claim)
Add one line `Tags: relevance:core` | `relevance:context` | `relevance:tangential` before `Investigative Direction:` (add other tags on the same line, comma separated).
- core: the Kirk assassination, its investigation, Erika Kirk / TPUSA conduct, timelines, evidence, people directly involved.
- context: related politics, media, donors, legal fights, background on case figures.
- tangential: fringe, historical or off-topic assertions recorded as said (occult rituals, Mandela effect, sweeping group claims) with no direct bearing on the case.

## Names (ruling 2026-10-14)
- A mis-transcribed name is NOT an alias. Never put a transcription error in a node's `Aliases:` line. Use the real spelling in node names and claim prose.
- Transcript Snippets and meme Quotes must stay verbatim to the transcript file. If a name in a snippet is mis-transcribed, keep the snippet verbatim and list the error under **Doubts** as `MISTRANSCRIPTION: "<as transcribed>" -> "<real name>" (<timestamp>)`. The integrator corrects it at the source in the transcript, the snippets and the quotes together.
- Fort Wuka is always Fort Huachuca. When unsure of a name, you may check the HappyScribe transcript of the same episode (https://podcasts.happyscribe.com/candace, WebFetch) and cite it in the Investigative Direction.
