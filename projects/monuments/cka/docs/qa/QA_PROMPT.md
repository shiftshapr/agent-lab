# CKA QA spot-check: reviewer instructions

You are checking a random sample of claims extracted from Candace Owens' podcast episodes. Each item in
`<PACK>/items_<NN>.md` gives a claim as recorded and the node ids it names (with canonical names). It also gives
the transcript from about two minutes before the claim's timestamp to 90 seconds after it.

Judge each claim **only against the transcript excerpt** (and HappyScribe for names, below). Do not judge whether the
host's allegation is true; the archive records what the host alleges. Do not edit any file except your results file.

## Score each claim on five checks

1. **attribution**: is the claim attributed to the right speaker (host, guest, clip, quoted document)? Is something
   the host *quotes or reads* presented as such, not as the host's own assertion? `ok` or `error`.
2. **accuracy**: does the Claim sentence say what the transcript says, without adding facts, certainty, motive or
   specifics that are not there? `ok`, `minor` (wording or nuance; a reader would not be misled), or `material`
   (a reader would be misled about what was alleged).
3. **person**: are the people in Mentions and Related Nodes, and the names in the claim, the right people? Watch for
   transcription errors that became names. If a name looks doubtful, you may check the HappyScribe transcript of the
   same episode (search https://podcasts.happyscribe.com/candace by episode title). `ok` or `error`.
4. **timestamp**: is the snippet spoken within about 60 seconds after the Claim Timestamp, so a `?t=` link lands on
   it? `ok` or `error`. If the snippet is not in the excerpt at all, say so in the note and mark `error`.
5. **relevance**: if the claim has a `relevance:` tag, is it right? `core` is about Charlie Kirk's assassination,
   its investigation, or the people and organisations at its centre. `context` is background that bears on it.
   `tangential` is about other matters, including private individuals' personal lives. `ok`, `disputed`, or `untagged`.

A claim has a **material error** if any of these holds: attribution `error`, accuracy `material`, person `error`, or
timestamp `error`. Minor wording and relevance disputes are recorded, but they are not material.

## Output

Write `<PACK>/results_<NN>.json`: a JSON list, one object per claim, in item order:

```json
{"claim": "C-1116", "episode": 1, "attribution": "ok", "accuracy": "ok", "person": "ok", "timestamp": "ok",
 "relevance": "untagged", "material": false, "note": "", "fix": ""}
```

`note` says what is wrong, quoting the transcript (keep it under 300 characters). `fix` proposes the corrected
text when there is an error (the corrected Claim sentence, person id or timestamp), or is empty.
Validate the file with `python3 -c "import json;json.load(open('<file>'))"` before you finish. Reply with one line:
the counts of material and minor findings.
