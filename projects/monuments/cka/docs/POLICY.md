# CKA policy

The rules for building and changing the Candace Kirk Archive. These are Daveed's rulings; where a rule changed, the date is noted and the newer rule wins. Every agent, script and reviewer that touches `projects/monuments/cka/` follows this document. The plan for upcoming work is in [ROADMAP.md](ROADMAP.md).

## 1. Roles
- **Daveed** makes the rulings. Anything not covered here, or anything that conflicts with this document, goes to him.
- **Claude Code** builds the archive. It runs ingest and supplements, integrates the results, makes corrections, and opens PRs. It merges its own PRs to `main` when the gates are green (section 9), without asking (2026-10-14).
- **Bill D and Transit** run the adversarial re-audit after everything is ingested, corrected and verified, not per PR (2026-10-14). It is **risk-weighted**: every allegation about a named person, every then-vs-now pair and every verification status, plus a random sample of the rest. After the first pass, a second pass is run if the findings warrant it, for example when the error rate in any stratum is above the QA target.
- **Locks.** No Neo4j production writes, inscription packs, promotes or deploys without Daveed. Never use the main X account's cookies for scraping.

## 2. Episodes
- Episodes use Candace's own episode numbers. Specials keep their `seq` in `input/episode_manifest.json`.
- Each episode is identified by its YouTube id. Its date is the YouTube publish time.

## 3. Node ids
- **Bands.** People are `N-1`..`N-9999`. Topics, organizations and places are `N-10000` and up.
- **Dense ids, no tombstones.** There are no gaps in the numbering and no retired-id ledger. A merged node simply stops existing as a node.
- **Merging duplicates.** `scripts/merge_person_nodes.py OLD:KEEP` keeps the id that was introduced first, so no first appearance moves. It closes the gap and writes an `id_map.csv` under `audits/`. Audits keep the ids that were current when they were written; read them through the id maps.
- **Stable public URLs come later.** Ids may be renumbered until the archive goes public. At launch the ids freeze, and the public site serves redirects built from the id maps. Planned URL forms are `https://decentralizedintel.agency/cka/node/N-123` and episodes by YouTube id.

## 4. Transcripts and names
- `transcripts_corrected/` is the analysis input.
- **A mis-transcribed name is not an alias, and it is corrected everywhere (2026-10-14).** It must not survive in node names, aliases, claim prose, transcript snippets or meme quotes. Fix it at the source:
  1. Add a word-bounded regex to `config/transcript_name_corrections.json`.
  2. Run `scripts/apply_name_corrections.py`. It rewrites the transcript, the drafts and the inscriptions together, so snippets stay verbatim, and it drops any matching aliases.
- **Aliases** are only spellings the host actually says, or genuine alternate names (maiden names, nicknames, handles).
- Fixed rulings:
  - "Fort Wuka" is always Fort Huachuca.
  - "Ike Promoter" is Ike Perlmutter.
  - "Don Oro" is Don Orrico.
  - "Saucelito" is Sausalito.
  - "Justin Strife" is Justin Streiff.
- **Second reading.** When a name or wording is unclear, check the HappyScribe transcript of the same episode (https://podcasts.happyscribe.com/candace) and cite it, with episode and timestamp, in the claim's Investigative Direction. Then web-search the name, with and without Candace, Charlie or Erika context, before asking Daveed to listen.

## 5. Claims
- **Attribution.** Every claim is attributed to its speaker: "The host says…", "In the clip, X says…", "According to the email read by the host…". It is never stated as fact.
- **Snippets.** Every claim carries a `Transcript Snippet` that is an exact substring of the corrected transcript, and a `Claim Timestamp` no later than the transcript's last marker.
- **Relevance tag required.** Each claim is tagged `relevance:core`, `relevance:context` or `relevance:tangential`; see `config/claim_lenses.json`. Sweeping or fringe statements by the host are kept and tagged, not dropped. Personal material about private individuals is tagged `tangential`; for example, the medical examiner's wife in ep135.
- **Typed links** follow `docs/EPISTEMIC_GRAPH.md`:
  - `Supports`, `Qualifies` and `Contradicts` connect only claims about the same proposition.
  - `Revises` is only for the host walking back or replacing her own earlier claim, and is written as a new claim pointing to the older one.
  - A possible conflict that is really a difference in kind (clinic vs hospital) is linked with `Qualifies` and explained in the Investigative Direction and the episode's Optional Flags.
- **Host walk-backs and extraction errors are handled differently:**
  - A walk-back by the host is never an edit. It becomes a new claim with `Revises:` (and `Contradicts:` if she explicitly rejects the earlier claim).
  - An extraction error (our mistake, not the host's) is corrected in place. Examples: conflating two people (C-2193), a wrong speaker, a wrong name. The erratum is recorded in that PR's audit README.
- **Supplements are add-only.** They add claims, artifacts, nodes and meme occurrences to an episode. They never rewrite existing items, except for the extraction-error corrections above.

## 6. Display (ruled 2026-10-14; counsel reviews before launch)
- An allegation is shown as **"The host alleges…"**, not "claims", and always next to its clip, played from the snippet's timestamp.
- **Tangential claims are hidden by default**, and can be shown with a toggle.
- **Private individuals are shown by role by default** ("the medical examiner's wife"). Their name stays in the data but is not displayed. A person's name is shown once they become a public figure in the case (for example, testifying, named in filings, or speaking publicly).
- **Clips are embedded from YouTube at the timestamp, never rehosted.** A private preservation copy of the audio is kept in case videos are taken down, and is not published.
- **Voice.** The archive's own pages and its account are strictly neutral: "what was alleged, and what the record shows". Commentary belongs to Daveed's personal account.
- Search and AI answer only from the archive and cite claim ids with timestamped clips. They decline to answer when they cannot cite.

## 7. Batch integration checklist (supplements and new episodes)
Scripts are in `scripts/supplement/` plus `scripts/supplement_integrate.py`. Agent instructions are in `docs/supplement/`.
1. `supplement/build_pack.py PACK --staging NAME` writes the reference tables, the specs, the filled-in `AGENT_PROMPT.md` and `batch.json`. Run one agent per episode: "Follow PACK/AGENT_PROMPT.md exactly. SEQ=n, TRANSCRIPT=file". Each staging file must pass `check_supplement.py`.
2. **Wait for every agent.** `supplement/verify_batch.py STAGING --pre --expect PACK/batch.json` refuses to proceed while any file is missing, and lists exact and near-duplicate nodes and memes. Map the duplicates through a title-merge JSON.
3. Run `supplement_integrate.py STAGING --batch NAME --merges JSON`, then `supplement/verify_batch.py STAGING --post`. Every episode's claim, artifact and meme-occurrence counts must equal the staged counts.
4. Name corrections. Turn the agents' MISTRANSCRIPTION reports into rules in `config/transcript_name_corrections.json`. Scope a rule to its episodes whenever the wrong rendering is a real name or a common word elsewhere, and check each scoped rule's hit count in its episode first. Preview the alias drops and renames, then run `apply_name_corrections.py`.
5. Fix the preflight findings: ground or drop Mentions, accept named-before-intro pairs with a reason, and add aliases only per section 4.
6. Run `supplement/merge_inscriptions.py STAGING` (it must report 0 lost ids), then `supplement_memes_backfill.py STAGING` (meme definitions; it should add no occurrences), `sync_claim_tags.py` and the companion generator.
7. Run the gate suite (section 9). Write `audits/<batch>/README.md` with the result table and review items (section 8), and include the agents' MISTRANSCRIPTION reports. Open the PR, run `gh pr update-branch`, and merge it when green.
8. **QA spot-check.** `qa/qa_pack.py PACK --since <base ref>` samples 2.5% of the new claims; one Opus reviewer per `items_NN.md` follows `docs/qa/QA_PROMPT.md`. Then `qa/qa_report.py PACK audits/<batch>/qa.md`. Fix every material finding; a batch above 2% material gets a second look before the next batch starts.

## 8. Review items
Each item that needs Daveed's eyes includes:
- the contextual transcript text
- a direct timestamped link: `https://youtu.be/<id>?t=<seconds>`, with the id taken from the manifest
- what was already checked (HappyScribe, web search)

## 9. Gates (the merge bar)
A CKA PR is green when all of these pass. This is what `.github/workflows/cka-gates.yml` runs:
- `dia_preflight.py --monument cka` PASS, and `--self-test` OK
- `hostile_hard_gates.py --monument cka` with 0 P0 and 0 P1
- `dia_preflight.py --monument bride_of_charlie` PASS
- `pytest projects/monuments/scripts`
- `check_claim_timestamps.py`: every claim's timestamp lies within 60s of the transcript block holding its snippet (nearest occurrence), so its `?t=` link lands on the words. Known drift goes in `config/claim_timestamp_baseline.json` (empty; never add to it)
- **Derived files are fresh.** Rerunning `apply_name_corrections.py`, `sync_claim_tags.py` and the companion generator changes nothing (`generated_at` aside).

Stacked PRs are retargeted to `main` before merging, so no commit is stranded on a merged branch. Use merge commits. `main` is protected: the "CKA gates" check is required, and admins may bypass only in an emergency.

**Daily pipeline merges (ruled 2026-10-14).** A daily-ingest PR auto-merges when green, **unless** its new claims trip the privacy linter or the sensitive-allegation triggers; those PRs wait for review. For the first week every daily PR waits, to calibrate.

## 10. Privacy
These rules apply to drafts, inscriptions and anything published. The privacy linter (ROADMAP 2.4) enforces them in CI.
- **Never record** home addresses, phone numbers, personal email addresses, license plates, or the names, schools or images of minors. Do not record them even when the host reads them on air: summarise the claim without the identifying detail, and trim the snippet to a passage that leaves it out.
- **Private individuals** are people who are not public figures, officials, or public-facing staff speaking in that role. Material about their personal lives is tagged `relevance:tangential` and is subject to the display rules in §6. Business filings and registered-agent addresses of companies may be recorded.
- When a private individual becomes central (for example, a named eyewitness), keep the claims, but stay with what the host alleges about the event, not their personal life.

## 11. Verification status
Every claim carries a verification status, set by evidence, never by opinion. The schema arrives in ROADMAP Phase 4; until then, every claim is `unverified`.
- `unverified`: no independent evidence linked yet (the default).
- `corroborated`: at least one independent primary or reputable secondary source agrees, and is cited.
- `disputed`: credible sources conflict, and both are cited.
- `contradicted-by-record`: a primary record (court filing, testimony, flight data, official document) says otherwise, and is cited.
- `revised-by-host`: the host later revised or rejected it; the claim is linked by `Revises` or `Contradicts`.

The host's own repetition is never corroboration. A same-host `Supports` is consistency, not evidence.

**Sources (ruled 2026-10-14).** Each source carries a reliability tier:
- **Tier 1, primary records:** court filings and testimony, warrants, FOIA responses, flight data (ADS-B, FAA), official documents and statements.
- **Tier 2, reputable reporting:** wire services, major and local papers, and broadcast news with editorial standards.
- **Commentators** (Kolvet and the Charlie Kirk Show, Baron Coleman, other podcasters and creators) are ingested as **speakers**. Their claims can support, contradict or be contradicted, exactly like the host's, but they are **never evidence** for a verification status. Only Tier 1 and Tier 2 sources can move a claim to `corroborated`, `disputed` or `contradicted-by-record`.

## 12. Errata and right of reply
- Every correction made after a claim is merged is logged in that PR's audit README. The release changelog compiles these into a public errata log.
- Before launch, a right-of-reply channel lets named people request a correction. Each request is logged, reviewed against the evidence, and answered. When a correction is warranted, it follows §5: an extraction error is fixed in place, and what the host said stays recorded as said.
