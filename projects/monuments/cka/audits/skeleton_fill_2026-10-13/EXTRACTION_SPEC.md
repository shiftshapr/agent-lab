# CKA skeleton-episode extraction spec

You are filling ONE empty CKA episode draft from its transcript. Output a single Markdown file in the exact format below. Work only from the transcript. Never invent facts, names, links, documents or timestamps.

Paths:
- Repo CKA dir: `projects/monuments/cka` (read only, do NOT edit anything in the repo).
- Reference pack: `<staging pack dir>` (scratch; built from canonical/ and drafts/)
  - `nodes.tsv` – every existing node (id, type, name, aliases). Reuse these ids.
  - `memes.tsv` – every existing meme M-1..M-84 (id, term, definition).
  - `claims_index.tsv` – every existing claim (id, episode, label), for optional cross-episode links.
  - `example_episode_102.md` – a complete draft in house style (older layout; use the section names below, not its roman numerals).
  - `EPISTEMIC_GRAPH.md` – rules for Supports / Contradicts / Qualifies / Revises / Mentions.
- Write your output to: `<staging pack dir>/staging/episode_NNN.md` (NNN = 3-digit seq).

## Inputs for your episode
- Transcript: `cka/transcripts_corrected/episode_NNN_<youtube_id>.md`. Paragraphs are preceded by `[MM:SS]` or `[H:MM:SS]` marks. Front matter has title, upload_date and duration.
- Current skeleton draft: `cka/drafts/episode_NNN.md`. It holds the meta block, a short executive summary and sometimes existing items. **Anything it already has with a real id (a `C-`, `A-`, `N-` or meme occurrence) must be kept exactly, with the same id and text.** Add to it; never renumber or drop it.

## People and well-known ids
- N-1 Charlie Kirk, N-2 Erika Kirk, N-3 Candace Owens (the host; she is the `Speaker` for her own lines). Look up everyone else in `nodes.tsv` (match canonical name or alias; transcripts often misspell names – match carefully, and only when it is clearly the same person).

## ID rules (placeholders)
Use real ids for anything that already exists. For new things use placeholders; the integrator replaces them with global ids later:
- New artifact family: `A-L1`, `A-L2`, … ; sub-items `A-L1.1`, `A-L1.2`, …
- New claim: `C-L1`, `C-L2`, … in order of claim timestamp.
- New person node: `N-P1`, `N-P2`, … New topic / organization / place node: `N-T1`, `N-T2`, …
- New meme: `M-N1`, `M-N2`, …
Number placeholders in order of first appearance in the episode.

## Output format (exact section headers)

```
## 1. Meta-Data
(copy the skeleton's meta bullet list verbatim, but:
 - set Video Timestamp Range to 00:00:00-<duration as HH:MM:SS from the transcript front matter>
 - set Extraction Timestamp (UTC) to now
 - add "- **Model Version**: claude-manual-extract-seqNNN"
 - leave "- **Episode Ledger Summary**:" with the single child line "  - (see registers)")

## 2. Executive Summary
(2–4 paragraphs, neutral and attributed: "The host says…", "According to the host…". Prose uses en dashes (–), never em dashes.)

## 3. Artifact Register
## 4. Node Register
## 5. Claim Register
## 6. Meme Register
## 7. Optional Flags
```

### Artifacts
An artifact is something shown, played or read on air: a document, post, clip, photo, record, article, flight data, audio. Group related items into a family. Format:

```
**A-L1** <family title> Bundle

**A-L1.1** <what was shown/played/read>

Quoted text: "<only if read aloud or shown as text; verbatim from transcript>"   (omit line if none)

Event Timestamp: 00:00:00-00:00:01
Video Timestamp: HH:MM:SS
Discovery Timestamp: 00:00:00-00:00:01
Confidence Level: High | Medium | Low

*Related: C-L3, C-L4, N-…*

---
```
A host's purely verbal reference with nothing shown may be an artifact ("Host verbal reference to …") only when a claim needs an anchor; flag it in Optional Flags.

### Nodes
Every node id cited anywhere in the episode (Mentions, Related Nodes, *Related:*) MUST have a row in the Node Register of THIS episode, reused nodes included.
- Reused node row: `**N-37** Bill Ackman` + one line on its role in this episode + `*Related: …*`.
- New person (`N-P#`): only real, named people who matter to a claim. Not viewers, commenters, chat handles, unnamed people, or generic roles. Row: name, one line ("First named by the host at HH:MM:SS in episode NNN."), aliases if the transcript spells them variously, `*Related: …*`. Every person must be cited by at least one claim (Mentions) or artifact.
- New topic/org/place (`N-T#`): an organization, place, or a persistent investigation target ("<X> Discrepancy", "<Y> Identification"). Before minting, check `nodes.tsv` for an existing topic covering it and reuse that instead. Row format:
```
**N-T1** <name>

Node Type: Topic | Organization | Place
<one-paragraph description>

*Related: C-…, A-…, N-…*
```

### Claims
A claim is one falsifiable proposition asserted on air (by the host, a guest, or a document/clip shown). Admission test: specific, checkable, attributable. Not framing, insults, opinions or rhetorical questions (list rejected ones under Optional Flags). Aim for every substantive factual beat; typically 15–35 claims per episode.

```
**C-L1** <short label>

Claim Timestamp: HH:MM:SS

Claim: <one or two sentences, attributed (e.g. "The host says …"); quote marks only around verbatim words>

Transcript Snippet: <verbatim span copied from the transcript at that time, 8–40 words, no edits except trimming>

Anchored Artifacts: A-L1.1   (always include this line; leave it empty if no artifact)
Mentions: N-…   (persons only; only people actually named in the transcript within ~4 minutes of the claim timestamp; N-3 when the host speaks of herself)
Related Nodes: N-…   (topics/orgs/places; persons go in Mentions, not here)
Supports: C-…   (optional, see below)
Contradicts: C-…   (optional)
Revises: C-…   (optional)
Investigative Direction: <the concrete record, document or person that would confirm or refute it>

---
```
- Claim Timestamp must be a real `[MM:SS]` mark area from the transcript, formatted HH:MM:SS, within the duration.
- Transcript Snippet must be copied character-for-character from the transcript (it will be machine-checked).
- Cross-episode links: only when a claim clearly restates (Supports), directly conflicts with (Contradicts), or corrects/walks back (Revises) a specific claim in `claims_index.tsv` from an EARLIER episode (lower episode number than yours), about the same proposition. When unsure, leave it out. Never link to a later episode.
- Defamation safety: never state accusations as fact; always attribute ("the host alleges", "according to the host's source").

### Memes
Recurring catchphrases. Reuse an `M-` id from `memes.tsv` when the same phrase recurs. Mint `M-N#` only for a distinctive phrase the host uses as a running bit. Keep any meme occurrences already in the skeleton. Format:
```
**M-48** (meme) Big Mad

### Occurrence 1

Video Timestamp: HH:MM:SS
Speaker: N-3
Quote: <verbatim>
Context: <one line>
Tags: <comma list>
Confidence: high

---
```

### DIA beats (required)
Scan the transcript (case-insensitive) for: "tips at", "more tips", "moretips@candaceowens", "candaceowens.com", "send us an email", "send them to us directly", "tip line", "decentralized intelligence", "dcia", "bounty" (not figurative uses). Each real hit (host asking for tips, offering a bounty, paying off a tip) gets: (1) its own claim, (2) a verbal-reference artifact, (3) an occurrence of meme **M-12** (Decentralized Intelligence Agency); add **M-14** (Candace Intelligence Agency) only when the CIA / Candace Intelligence Agency merch phrase airs. List any hit you judged not a DIA beat under Optional Flags with a reason.

### Memes (extra)
Recurring catchphrases and any funny or weird running bit by the host are meme candidates. Prefer reusing an existing M- id.

### Optional Flags
Bullets: artifacts referenced but not shown, transcription ambiguities (keep the transcript spelling), name spellings you could not match confidently, rejected claims (admission test).

## Style
- Prose: en dash (–), never em dash (—). Quoted/snippet text: exactly as the transcript, dashes included.
- No markdown other than the formats above. No tables.

## When done
Reply with: the output path, counts (artifacts, claims, new persons, new topics, new memes, reused nodes), and any doubts (uncertain name matches, possible cross-episode links you left out).
