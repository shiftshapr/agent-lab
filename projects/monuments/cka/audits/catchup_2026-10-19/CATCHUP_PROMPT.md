# CKA catch-up extraction (new episodes, 2026-10-19)

You are extracting ONE new CKA episode from its transcript. Follow `SPEC.md` in this folder exactly. It was
written for skeleton episodes, and it applies unchanged to new ones: the skeleton draft
`projects/monuments/cka/drafts/episode_NNN.md` holds only the meta block and a short summary. Write
`staging/episode_NNN.md` in this folder. Do not edit anything in the repo.

Read `EPISTEMIC_GRAPH.md` and skim `example_episode_102.md` for house style. The repository root is
`/Users/shiftshapr/agent-lab-wt-p0b`.

## Additions to SPEC.md (rulings since it was written)

**Coverage.** Capture every substantive, checkable beat. Current episodes average about one claim per minute
(roughly 45–60 for a 50-minute episode). The "15–35" figure in SPEC.md is out of date.

**Relevance tag (required on every claim).** Add a `Tags:` line before `Investigative Direction:`:
- `Tags: relevance:core` covers the Kirk assassination and its investigation, Erika Kirk and TPUSA conduct,
  timelines, evidence and the people directly involved.
- `Tags: relevance:context` covers related politics, media, donors, legal fights and background on case figures.
- `Tags: relevance:tangential` covers fringe, historical or off-topic assertions recorded as said, and private
  individuals' personal lives.

**Attribution (the most common error).**
- `>>` in the transcript marks a change of speaker. Work out who says each line. A guest's, a caller's or a
  clip's words must not be given to the host, and the host's must not be given to them.
- A viewer comment the host reads is "A viewer comment the host reads says …".
- A clip is "In a clip the host plays, X says …".
- A document is "Per the <document> the host shows, …".
- Never state as fact what the host reports from a post, a chat or a rumour. Allegations are "The host alleges …".
- Add no detail the transcript does not contain: no count, date, duration, name, or "emails" for one email.
  Keep her hedges ("I think", "allegedly").

**Names.**
- A mis-transcribed name is never an alias. Use the real spelling in node names and claim prose only when you
  are sure. Keep Transcript Snippets verbatim.
- List each error under Optional Flags as `MISTRANSCRIPTION: "<as transcribed>" -> "<real name>" (<timestamp>) source: <url>`.
- Check unfamiliar names. You may web-search `"<name>" "Charlie Kirk"` or `"<name>" "Candace Owens"`, or check the
  HappyScribe transcript of the same episode (https://podcasts.happyscribe.com/candace). If you cannot confirm a
  name, keep the transcript spelling and flag it as unresolved.
- If the host herself says a wrong name, keep her words and add the correct name in brackets.
- Standing ids:
  - N-1 Charlie Kirk, N-2 Erika Kirk, N-3 Candace Owens (the host).
  - N-493 Marina Minas, N-217 Elizabeth McCoy (alias Eliza McCoy).
  - Check everyone else in `nodes.tsv`.
- Mentions lists only people named or clearly referred to in the claim. The host's husband is N-30.

**Timestamps.** The Claim Timestamp must be at or up to about 20 seconds before the moment the snippet is spoken.
The transcript's `[MM:SS]` marks give block starts. Inside a block, estimate by word position.

**Web searches** are shared with other agents. Search only the names that need it.

When done, run the checker and fix every error it reports:
`SKELETON_PACK=<this folder> python3 -I /Users/shiftshapr/agent-lab-wt-p0b/projects/monuments/cka/scripts/check_skeleton_staging.py NNN`

Then reply with the counts asked for in SPEC.md, plus any MISTRANSCRIPTION and unresolved names.
