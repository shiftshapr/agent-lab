# CKA tweet linking: reviewer instructions

`<PACK>/tweets_<NNN>.md` lists posts by Candace Owens (@RealCandaceO) on X, in date order, deleted ones included.
`<PACK>/claims_<NNN>.tsv` lists the archive's claims from the episodes she aired around those dates. Each claim has an id,
episode, upload date, label, claim text and the person ids it mentions. `<PACK>/nodes.tsv` lists every person, topic,
organisation and place node. Read `docs/EPISTEMIC_GRAPH.md` in the repository for what the relations mean.

For **every** post decide what it links to. Use only what the post itself says, plus the claims and nodes given. Do not
judge whether anything is true. Edit no file except your links file.

## Fields
- `claims`: claim ids for the same proposition, a direct continuation of it, or the post being shown or read on air.
  Use at most 5 claims, best first. Link a claim only when the post makes the same specific assertion (same person, same act, same detail). A post that merely shares a topic or a person gets nodes only.
- `relation` describes the strongest claim link:
  - `same_allegation`: the post asserts what the claim records her saying.
  - `shown_on_air`: the claim or its artifact is this post being shown or read.
  - `follow_up`: the post updates, extends, corrects or walks back the claim; say which in `note`.
  - `contradicts`: the post says the opposite of the claim.
  - Omit `relation` when `claims` is empty.
- `nodes`: ids of the people, topics, organisations and places the post names or clearly refers to. Match names and
  aliases carefully, and only when it is clearly the same one.
- `unlinked`: when no claim and no node applies, give one reason and omit the other fields:
  - `off_topic`: unrelated to the archive's subjects.
  - `personal`: family, faith, greetings.
  - `promotion`: the show, merch, sponsors, schedule; a bare link to an episode counts.
  - `retweet_no_comment`
  - `reply_chatter`: a short reply with no substance.
  - `unclear`: a bare link or fragment you cannot interpret.
- A post can have `nodes` without `claims`. That is common: she comments on a person or topic but the show did not
  record the same proposition.
- `note`: optional, under 200 characters.

## Output
Write `<PACK>/links_<NNN>.json`: a JSON list with one object per post, in order.

```json
{"id": "1965961464034066647", "claims": ["C-1203"], "relation": "same_allegation", "nodes": ["N-40", "N-10012"], "note": ""}
{"id": "1965437462957940832", "nodes": ["N-10026"]}
```

Validate the file with `python3 -c "import json;json.load(open('<file>'))"`. Reply with one line: posts linked to claims,
posts with nodes only, and posts unlinked.
