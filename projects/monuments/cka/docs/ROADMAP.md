# CKA roadmap (from 2026-10-14)

The full execution plan from here to a verified, published and promoted archive. Rules are in [POLICY.md](POLICY.md). **Owner** is who does the work. **Gate** is the Daveed decision a phase needs before it can close. Phases run in order unless a step is marked *parallel*.

**Goal.** Move from a record of what the host alleged to an archive that also shows what the record says about each allegation, kept current automatically, published as versioned open data, and promoted on what only it can show.

## Status (2026-10-14)
- 161 episodes. The 19 skeleton episodes are filled, and supplement batches 1–5 are on `main` (about 6,800 claims added). Batch 6 is staged, and about 22 episodes remain after it.
- People are dense from N-1 to N-910, and mis-transcribed names are corrected at the source.
- This PR adds the policy document, this roadmap and CI.

---

## Phase 0 — Foundations (now; parallel with Phase 1)
**Owner:** Claude · **Gate:** Daveed turns on branch protection for `main` (requiring "CKA gates")

| # | Task | Done when |
|---|---|---|
| 0.1 | Policy document and roadmap | merged (this PR) |
| 0.2 | CI gate workflow with the derived-files freshness check | merged; the check runs on every PR |
| 0.3 | Move the integration tooling from the scratchpad to `cka/scripts/supplement/`: agent spec, `check_supplement.py`, inscription merge, staging fuzzy-duplicate check, per-episode count verification | one `integrate_batch.py STAGING` command runs steps 2–7 of POLICY §7, and tests cover the batch 2–3 meme drop and the uppercase-header case |
| 0.4 | Make the inscription builder copy claim `Tags:` itself | `sync_claim_tags.py` reports 0 on a fresh build |
| 0.5 | **Timestamp verifier.** Every claim's timestamp falls inside the transcript block that contains its snippet, so the `?t=` link lands on the sentence | it runs as a CI step and fails on any drift |
| 0.6 | **Spot-check QA harness.** Opus re-checks a random 2–3% of each batch's claims against the transcript and HappyScribe, scoring attribution, accuracy, person, timestamp and relevance | it reports a material-error rate per batch to `audits/<batch>/qa.md`; target < 2% |
| 0.7 | **Source-of-truth decision.** Today drafts (Markdown) are primary and JSON is derived. Write up the options and the cost of each | Daveed rules, before Phase 3 |
| 0.8 | Privacy rules in POLICY §10 | merged (this PR) |

## Phase 1 — Finish ingest and automate staying current
**Owner:** Claude · **Gate:** Daveed approves the daily pipeline's first week of auto-merged PRs

| # | Task | Done when |
|---|---|---|
| 1.1 | Supplement batch 6 (20 episodes) | merged; QA rate reported |
| 1.2 | Supplement batch 7 (the last ~22 episodes) | every episode is at or above about 0.9 claims/min, or explained |
| 1.3 | Catch up on new episodes: Ep 399, Ep 400 and later | the manifest matches the channel |
| 1.4 | **Automated daily pipeline**, Mon–Thu at 4 p.m. PT: watch the channel feed → fetch our transcript and the HappyScribe one → apply name corrections, and flag any HappyScribe name differences for review → extract → integrate → QA sample → PR → merge when CI is green → push notification to Daveed with that day's review items | runs unattended for a week |
| 1.5 | Daily X ingest from Daveed's account; tweet-to-claim, node and artifact linking for the 13-month backfill | every tweet is linked or explicitly unlinked |
| 1.6 | **Monitor throughput.** Log 5-hour and weekly usage per batch and per daily run | review only if the daily run slips more than one day (then move extraction to batch API or cloud jobs) |

## Phase 2 — Corrections sweep
**Owner:** Claude · **Gate:** Daveed rules on items that need his ear

| # | Task | Done when |
|---|---|---|
| 2.1 | **HappyScribe name diff across the whole archive.** For each person and topic name, compare our transcript with HappyScribe, triage, add to `transcript_name_corrections.json`, and re-check every alias against POLICY §4 | every name difference is resolved, or listed for Daveed |
| 2.2 | Clear the open review items in the batch READMEs: C-1241 and C-3505 misattributions, Frank Carney vs N-505, the "Marina" node (Minas vs Medvin), Slauson vs Christiansen, Bowyer 2010 vs 2011, and the 13 skeleton names | each is resolved or ruled |
| 2.3 | Collected cross-batch links (ep106 qualifying ep104–105, the ep118 self-corrections, …) | linked |
| 2.4 | **Privacy scrub** under POLICY §10: home addresses, minors' details, and private individuals' personal details | 0 hits by the privacy linter, which runs in CI |

## Phase 3 — Wave 4: events and things (after all ingest)
**Owner:** Claude · **Gate:** Daveed approves the event and topic model

| # | Task | Done when |
|---|---|---|
| 3.1 | Event and thing nodes with `event_time`. For example, a Sept 10 event absorbs N-10002 Death and Memorial | each core event has a node with a time |
| 3.2 | Consolidate the topics: about 1,300 now, including more than ten Fort Huachuca topics. Apply the approved splits | topic count reduced with a merge map; no near-duplicate topic pairs |
| 3.3 | Fix the companion's corroboration mapping: a same-host `Supports` must not become `isCorroboratedBy` | fixed |

## Phase 4 — Primary sources and the verification layer
4.1–4.3 can start in parallel with Phase 1. Linking (4.5) waits for Wave 4.
**Owner:** Claude · **Gate:** Daveed approves the source list and the verification taxonomy

| # | Task | Done when |
|---|---|---|
| 4.1 | **Source streams** as separate monuments or sources, each with provenance: Utah v. Robinson docket filings and preliminary-hearing transcripts, public warrants, FOIA responses, ADS-B and FAA flight data, TPUSA, Kolvet and Charlie Kirk Show statements, Erika Kirk interviews, and major news reporting | each stream has an ingest script and a manifest |
| 4.2 | **External monitors**: alerts on the court docket and on news for the key names, feeding the daily pipeline | alerts land as items in the pipeline |
| 4.3 | **Open-questions register.** Promote each Investigative Direction into a tracked question: what's known, what would settle it, status, and linked tips | every core claim has its questions registered |
| 4.4 | **Verification status on claims** (POLICY §11): `unverified`, `corroborated`, `disputed`, `contradicted-by-record`, `revised-by-host`, each with cited evidence | schema in the drafts, inscriptions and companion; CI validates it |
| 4.5 | **Verification linking pass.** Link each source-stream document to the claims it bears on, and set the statuses | every core claim has a status other than `unverified`, or an open question explaining why |

## Phase 5 — Revisions and contradictions (the site's lead feature)
**Owner:** Claude (Opus) · **Gate:** Daveed samples the ledger

| # | Task | Done when |
|---|---|---|
| 5.1 | For each person and topic, walk the claims in airing order and link real `Revises`, `Contradicts` and `Qualifies` across episodes (the host vs. herself) | each pair is in the ledger with both clips |
| 5.2 | Cross-source contradictions: the host vs. the court record, TPUSA statements and the flight data (from Phase 4) | linked, with `contradicted-by-record` statuses |
| 5.3 | "Then vs. now" ledger export: a reviewable list of pairs with both clips, dates and the delta | Daveed signs off on a sample |

## Phase 6 — Adversarial re-audit
**Owner:** Bill D and Transit · **Gate:** Daveed rules on the findings

| # | Task | Done when |
|---|---|---|
| 6.1 | A full-archive adversarial pass on the verified, linked data, using the QA rubric from 0.6 and the policy | the findings are filed as PRs or rulings |
| 6.2 | Claude fixes the findings; CI and QA are rerun | merged |

## Phase 7 — Interop
| # | Task | Done when |
|---|---|---|
| 7.1 | Re-vendor BRC-222 2.1; emit CrosswalkBridges (KnowledgeGraphNode, SKOS match types) with `external_ids` (Wikidata and others) | it validates against 2.1 |

## Phase 8 — Publishing
**Owner:** Claude, with legal review · **Gate:** Daveed and counsel approve the display and privacy rules

| # | Task | Done when |
|---|---|---|
| 8.1 | **Versioned data releases** (semver), each with a changelog, a public errata log (from POLICY §12) and its hash inscribed (BRC-222); every page shows "as of release X" | release v1.0.0 is cut |
| 8.2 | **Open data**: JSON and CSV downloads and a read API, with a license | published with the release |
| 8.3 | **Right-of-reply** and correction-request channel; requests are logged and answered within a set time | live before launch |
| 8.4 | **Legal review** of the display rules (POLICY §6), the privacy rules (§10) and the clip policy (embed from YouTube at the timestamp; never rehost) | signed off |

## Phase 9 — Site and app (decentralizedintel.agency, Gov Hub campaign)
**Owner:** Claude · **Gate:** go-public approval

| # | Task | Done when |
|---|---|---|
| 9.1 | Load each data release into Gov Hub (`structure_json`) or a small API with search | it loads from a release bundle |
| 9.2 | **Views.** Episode: the video with claim markers on the scrubber. Claim: the snippet, the clip at its timestamp, typed edges, verification status and evidence. Person and topic: first appearance, every claim, and stance over time. Timeline: episodes plus events. The "then vs. now" ledger as the lead feature. Meme and clip tracker for the clip-economy / "fed slop" narrative. Open-questions board with tip submission | usable on staging |
| 9.3 | Search and AI that answer only with citations (claim ids plus clips) and decline otherwise; what-if scenarios per the design doc | evaluated on a question set |
| 9.4 | **Go-public gate**: freeze ids, publish redirects built from the id maps, add share cards for every claim and pair, and Daveed approves the deploy | live |

## Phase 10 — Promotion (starts at launch; the digest can start earlier internally)
**Owner:** Claude drafts, Daveed approves · **Gate:** Daveed sets the voice and the accounts

| # | Task | Done when |
|---|---|---|
| 10.1 | **Positioning**: "what was alleged, and what the record shows", stated on the site and in every post | messaging doc approved |
| 10.2 | **"Then vs. now" cards**: two clips, two dates and one link each, auto-generated from the Phase 5 ledger | a card set exists for the top pairs |
| 10.3 | **Weekly digest**: new claims, revisions, verification changes and open questions; posted from Daveed's account with deep links | runs weekly |
| 10.4 | **Open-questions call-outs**: invite evidence on specific open questions (crowdsourced verification with citations) | the tip flow is live |
| 10.5 | **Partnerships**: cross-links with whokilledck.com; researcher and journalist access to the API | at least one partner is live |
| 10.6 | **Search visibility**: a crawlable page per node, claim and episode, with structured data | indexed |

---

## Decision points for Daveed (in order)
1. Branch protection on `main` (Phase 0).
2. The source-of-truth model, Markdown-primary vs. JSON-primary (0.7, before Wave 4).
3. The first week of the daily pipeline (Phase 1).
4. The event and topic model (Phase 3).
5. The source list and the verification taxonomy (Phase 4).
6. A sign-off sample of the then-vs-now ledger (Phase 5).
7. The adversarial findings (Phase 6).
8. Display, privacy and clip rules with counsel (Phase 8).
9. Go-public (Phase 9).
10. Voice, accounts and partners (Phase 10).

## Metrics we track
- **Coverage:** claims per minute, per episode; target about 0.9 or more.
- **Quality:** material-error rate from the QA sample, per batch; target < 2%.
- **Freshness:** time from an episode airing to its PR merging; target the same day.
- **Verification:** share of core claims with a status other than `unverified`.
- **Throughput:** 5-hour and weekly usage per batch and per daily run; watched only (Phase 1.6).
