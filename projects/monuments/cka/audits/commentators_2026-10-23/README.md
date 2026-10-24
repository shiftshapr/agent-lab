# Commentator pilot (ROADMAP 4.1b) (2026-10-23)

**Scope.** Daveed chose the speakers (the Charlie Kirk Show, Erika Kirk, Harpole and Turek, Baron Coleman) and a
pilot of about 10 videos each.

**Selection.** 4 Opus agents found 44 YouTube videos with original-English captions (`PROMPT_select.md`,
`selection.md`). Daveed approved them with Baron Coleman trimmed to the 5 episodes that address Owens most directly,
leaving 37 videos and about 49 hours.

**Captions.** `scripts/commentary/fetch.py` fetched the `en-orig` captions to private storage. The sha256 of each
caption file is in `commentary/episodes.json`.

**Extraction.**
- 37 Opus agents ran `PROMPT_extract.md`, one per video. Each output passed `check_extract.py`: snippets are
  verbatim, timestamps fall where the snippet is spoken, and node ids are valid.
- That gave 2,084 claims. `consolidate.py` then:
  - removed 45 duplicates from two re-uploads (K-013 of K-011, K-030 of K-028);
  - resolved names: Andrew Cipher or Seifer to Andrew Sypher (N-331), Terrell to Terryl Farnsworth (N-261), and
    George Farmer and Tyler Bowyer to their existing nodes;
  - assigned the ids `CC-1..CC-2039`.
- 416 caption mis-hearings were logged (`mistranscriptions.json`).
- Ambiguous speaker turns were skipped, not guessed. The caption converter's front matter wrongly names Candace
  Owens as host on these transcripts; extraction used each video's own details instead.

**Linking.**
- TF-IDF matched 1,834 non-tangential claims (excluding the host's own words in clips) to up to 8 host claims each.
- 27 Opus agents proposed 664 links (`PROMPT_link.md`).
- 12 strict confirm agents (`PROMPT_link_confirm.md`) kept 524 and rejected 140 (`rejected_links.json`).
- The main rejection reasons:
  - The host claim only replays, quotes or paraphrases the same commentator.
  - The host claim is a guest's, clip speaker's or document's words that the host does not adopt.
  - The host claim is hedged speculation.
  - The two claims share only a topic.

**Result.** 524 links: 143 contradicts, 37 qualifies, 344 supports. `links_review.md` lists them by relation and speaker.

**Notes.**
- **Coleman:** he mostly backs Owens (flight logs, Fort Huachuca, the paving, doubts about Robinson). Turek, Harpole,
  Melton, Neff, Kolvet and Erika Kirk supply most of the contradictions: CPR, the rooftop texts, the hospital, the
  parents, the microphone theory, Aspen, and Mikey McCoy's first call.
- **Turek:** he now says there was no CPR for most of the ride and that he tried CPR for 20 to 30 seconds at the
  end. That conflicts with his earliest accounts and is recorded as he said it.
- **Harpole:** on the Shawn Ryan Show he describes the rooftop texts to Chief Long as his own. The court record
  (S-12) shows Dan Flood sent them. Turek later says the same (K-036). Commentator claims are recorded as said and
  are not used as evidence.
