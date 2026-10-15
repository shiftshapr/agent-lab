# CKA full verification pass: reviewer instructions

You are checking claims extracted from Candace Owens' podcast episodes against the transcript. `<PACK>/items_<NNN>.md`
lists claims in airing order. Each episode starts with its person nodes (id and canonical name). Each claim gives the
claim as recorded, the node ids it names, and the transcript from about 60 seconds before its timestamp to 90 seconds after.

The archive records **what is said or shown in the episode**, attributed to whoever says it. Do not judge whether
an allegation is true. Edit no file except your results file.

## Five checks
1. **attribution**: is the claim attributed to the right speaker (the host, a guest, someone in a clip she plays,
   a viewer comment she reads, a document she shows)? A comment, clip or document must not be presented as the
   host's own words, and the host's words must not be given to someone else. `ok` or `error`.
2. **accuracy**: does the Claim say what the transcript says, with no added facts, certainty, motive, dates or
   details, and no dropped hedges ("I think", "allegedly")? `ok`, `minor` (wording; a reader would not be misled),
   or `material` (a reader would be misled about what was said).
3. **person**: are the people named in the claim, and the ids in Mentions, the right people?
   - Mentions lists people who are named or clearly referred to in the claim, and only those people.
   - A name that looks like a transcription error is **only** an error if you confirm the correct name with a
     source: web-search `"<name>" "Charlie Kirk"` (or with Candace Owens / TPUSA) in "extended" mode, with spelling
     variants. Security staff, staffers and other minor figures are real people, often named only on Instagram,
     Facebook or HappyScribe (https://podcasts.happyscribe.com/candace). If you cannot confirm, mark `ok` and
     write "unresolved name: <name>" in `note`.
   - `ok` or `error`.
4. **timestamp**: the Claim Timestamp should be at most about 20 seconds after, and at most about 75 seconds
   before, the moment the claim's content is spoken. Markers give exact times only at block starts; inside a
   block, estimate by word position. `ok` or `error`.
5. **relevance**: if there is a `relevance:` tag, is it right? `core`: Charlie Kirk's assassination, its
   investigation, or the people and organisations at its centre. `context`: background that bears on it.
   `tangential`: other matters, including private individuals' personal lives. `ok`, `disputed`, or `untagged`.

**material** is true if attribution is `error`, accuracy is `material`, person is `error`, or timestamp is `error`.

## Fixes
For every claim that is material **or** minor, give the fix as fields to set. Include only fields that change:
- `claim`: the corrected Claim sentence, in the archive's style ("The host says …", "In a clip the host plays,
  X says …", "A viewer comment the host reads says …", "Per the <document> the host shows, …"). Change only what is
  wrong; keep everything else exactly as written.
- `label`: a corrected title (Title Case) if the title is wrong.
- `timestamp`: `HH:MM:SS`, about 5 seconds before the content is spoken.
- `mentions`: the full corrected list of person ids, e.g. `["N-3", "N-162"]`. Use only ids from the episode's person
  list or the claim's named ids.
- `relevance`: `core`, `context` or `tangential`, if disputed.
- `names`: for a confirmed transcription error, `[{"wrong": "Bob Evan", "right": "Bob Evnen", "source": "<url>"}]`.

## Output
Write `<PACK>/results_<NNN>.json`: a JSON list, one object per claim, in item order:

```json
{"claim": "C-1116", "episode": 1, "attribution": "ok", "accuracy": "ok", "person": "ok", "timestamp": "ok",
 "relevance": "untagged", "material": false, "note": "", "fix": {}}
```

`note` explains any finding by quoting the transcript, in under 300 characters. Check every claim; do not skip any.
Validate the file with `python3 -c "import json;json.load(open('<file>'))"`. Reply with one line: the numbers of
claims checked, material and minor.
