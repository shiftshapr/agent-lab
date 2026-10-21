# CKA tweet ledger (ROADMAP 1.5)

- **`tweets.jsonl`:** every @RealCandaceO post since 2025-09-09, one JSON record per post: id, date (UTC), url, status
  (`live` or `deleted`), retweet, reply and quote flags, the full text, and the sources it was collected from.
  - Deleted posts were recovered from Wayback and syndication and are kept with their text (Daveed, 2026-10-21).
  - Built and extended by `scripts/tweets/build_ledger.py`.
- **`links.jsonl`:** one entry per post. A post is either linked or explicitly unlinked:
  - `claims`: archived claims with the same specific assertion, a direct follow-up, or the post shown on air.
  - `relation`: `same_allegation`, `shown_on_air`, `follow_up` or `contradicts`.
  - `nodes`: the people, topics, organisations and places it names.
  - `unlinked`: one of `off_topic`, `personal`, `promotion`, `retweet_no_comment`, `reply_chatter` or `unclear`.

Opus reviewers make the links (`docs/tweets/LINK_PROMPT.md`, `scripts/tweets/link_pack.py`), and
`scripts/tweets/merge_links.py` merges them. `merge_links.py --check` is a CI gate: every post must have a valid entry.
The daily pipeline fetches and links new posts (`scripts/daily/tweets_intake.py`, runbook step T) using the spare
twscrape account, never the main X account.

The episode archive is unchanged: claims record what is said on the show, and posts cross-reference them.
`renumber_claims.py` and `merge_person_nodes.py` rewrite ids in `links.jsonl`, never in `tweets.jsonl`.
