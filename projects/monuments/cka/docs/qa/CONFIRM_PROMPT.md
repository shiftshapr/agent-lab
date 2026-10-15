# CKA verification pass: confirming proposed fixes

A first reviewer checked each claim against its transcript and proposed fixes. You decide, for each item in
`<PACK>/confirm_<NNN>.md`, whether each proposed fix is right. Each item gives the claim as recorded, the first
reviewer's finding and proposed fix, and the transcript around the timestamp. You may read more of the transcript
(the file is named in the item) when the excerpt is not enough.

The archive records **what is said or shown in the episode**, attributed to whoever says it.

## Rules
- Accept a fix only if the transcript supports it. Reject it if the original was right, or if the fix adds anything
  the transcript does not say. Amend it when the problem is real but the fix is not quite right.
- **Mentions** lists the people the claim names or clearly refers to. That includes someone the claim describes
  without naming (the recipient of a text it quotes, "her husband" when that is clear). Do not strip such a person.
  The host (N-3) need not be listed for "The host says". Remove anyone the claim does not refer to.
- **Names** (`names` in the fix): accept a transcription correction only with a source you have checked yourself.
  Web-search `"<name>" "Charlie Kirk"` (or with Candace Owens / TPUSA) in "extended" mode with spelling variants, or
  open the cited source. If you cannot confirm it, reject the name fix and say "unresolved".
- **Timestamps**: the corrected timestamp should be about 5 seconds before the content is spoken.
- Keep the archive's attribution style ("The host says …", "In a clip the host plays, X says …").

## Output
Write `<PACK>/confirmed_<NNN>.json`: a JSON list, one object per item, in order:

```json
{"claim": "C-1205", "episode": 6, "decision": "accept", "fix": {"mentions": ["N-1", "N-62"]}, "note": ""}
```

`decision` is `accept` (use the proposed fix as is), `amend` (use your `fix` instead), or `reject` (change nothing).
For `accept`, copy the proposed fix into `fix`. For `amend`, give the full corrected fix. `note` is a reason in under
200 characters. Validate the file with `python3 -c "import json;json.load(open('<file>'))"`. Reply with one line:
the counts of accept, amend and reject.
