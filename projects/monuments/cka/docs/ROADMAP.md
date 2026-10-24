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
| 0.1 | ✅ Policy document and roadmap | merged (#74) |
| 0.2 | ✅ CI gate workflow with the derived-files freshness check | merged (#74, #75); required on `main` |
| 0.3 | ✅ 2026-10-14 (as `build_pack.py`, `verify_batch.py --pre/--post` and `merge_inscriptions.py`, with tests in `test_supplement_tools.py`; steps chained per POLICY §7). Move the integration tooling from the scratchpad to `cka/scripts/supplement/`: agent spec, `check_supplement.py`, inscription merge, staging fuzzy-duplicate check, per-episode count verification | one `integrate_batch.py STAGING` command runs steps 2–7 of POLICY §7, and tests cover the batch 2–3 meme drop and the uppercase-header case |
| 0.4 | ✅ 2026-10-14 (`_add_claim_tags` in the builder). Make the inscription builder copy claim `Tags:` itself | `sync_claim_tags.py` reports 0 on a fresh build |
| 0.5 | ✅ 2026-10-14 (`check_claim_timestamps.py`, CI step; 26 timestamps corrected, see `audits/claim_timestamps_2026-10-14/`). **Timestamp verifier.** Every claim's timestamp falls inside the transcript block that contains its snippet, so the `?t=` link lands on the sentence | it runs as a CI step and fails on any drift |
| 0.6 | ✅ 2026-10-14 (`scripts/qa/qa_pack.py`, `docs/qa/QA_PROMPT.md`, `scripts/qa/qa_report.py`; archive baseline in `audits/qa_baseline_2026-10-14/`: **14.0% material, target not met**, see 2.5). **Spot-check QA harness.** Opus re-checks a random 2–3% of each batch's claims against the transcript and HappyScribe, scoring attribution, accuracy, person, timestamp and relevance | it reports a material-error rate per batch to `audits/<batch>/qa.md`; target < 2% |
| 0.7 | ✅ 2026-10-14 (`neo4j_ingest.extract_claims` is the one claim parser: builder, tag sync, timestamp check; parity with preflight and inscriptions tested in `test_draft_parser.py`). **Source of truth (ruled: JSON primary from Wave 4).** Until then, keep Markdown primary but route every parse through one tested parser module | one parser module used by integrator, builder and gates |
| 0.8 | Privacy rules in POLICY §10 | merged (this PR) |

## Phase 1 — Finish ingest and automate staying current
**Owner:** Claude · **Gate:** first week reviewed (every daily PR waits); then auto-merge when green except privacy or sensitive-allegation hits (POLICY §9)

| # | Task | Done when |
|---|---|---|
| 1.1 | ✅ Supplement batch 6 (20 episodes) | merged (#76) |
| 1.2 | ✅ Supplement batch 7 (the last 22 episodes) | merged (#77); all 161 episodes filled or supplemented |
| 1.3 | ✅ 2026-10-19 Ep 399–403 (seq 162–166, `audits/catchup_2026-10-19/`). Catch up on new episodes: Ep 399, Ep 400 and later | the manifest matches the channel |
| 1.4 | 🚧 2026-10-19 tooling: `scripts/daily/` (intake.py, finalize.py, run_daily.sh), `docs/daily/RUNBOOK.md`. **Automated daily pipeline**, Mon–Thu at 4 p.m. PT: watch the channel feed → fetch our transcript and the HappyScribe one → apply name corrections, and flag any HappyScribe name differences for review → extract → integrate → QA sample → PR → merge when CI is green → push notification to Daveed with that day's review items | runs unattended for a week |
| 1.5 | ✅ 2026-10-21 (`tweets/`, `audits/tweets_backfill_2026-10-21/`; 3,403 posts: 1,134 linked to claims, 1,328 to people and topics only, 941 unlinked with a reason; daily intake in the pipeline). Daily X ingest from Daveed's account; tweet-to-claim, node and artifact linking for the 13-month backfill | every tweet is linked or explicitly unlinked |
| 1.6 | **Monitor throughput.** Log 5-hour and weekly usage per batch and per daily run | review only if the daily run slips more than one day (then move extraction to batch API or cloud jobs) |

## Phase 2 — Corrections sweep
**Owner:** Claude · **Gate:** Daveed rules on items that need his ear

| # | Task | Done when |
|---|---|---|
| 2.1 | **HappyScribe name diff across the whole archive.** For each person and topic name, compare our transcript with HappyScribe, triage, add to `transcript_name_corrections.json`, and re-check every alias against POLICY §4 | every name difference is resolved, or listed for Daveed |
| 2.2 | Clear the open review items in the batch READMEs: C-1241 and C-3505 misattributions, Frank Carney vs N-505, the "Marina" node (Minas vs Medvin), Slauson vs Christiansen, Bowyer 2010 vs 2011, and the 13 skeleton names | each is resolved or ruled |
| 2.3 | Collected cross-batch links (ep106 qualifying ep104–105, the ep118 self-corrections, …) | linked |
| 2.4 | **Privacy scrub** under POLICY §10: home addresses, minors' details, and private individuals' personal details | 0 hits by the privacy linter, which runs in CI |
| 2.5 | ✅ 2026-10-15 (full Sonnet verification pass, then full Opus re-check of all 13,915 claims with Opus confirmation; final sample `audits/qa_final_opus_2026-10-15/`: **1.4% material**, 3.6% under the old stricter timestamp rule). **QA remediation** (baseline 14.0% material: timestamps 24, persons 11, attribution 8, content 3 of 278). (a) Timestamp drift inside long paragraph blocks: estimate the spoken time by word position and correct; tighten `check_claim_timestamps.py` to match. (b) Names: fold the reviewers' mis-transcriptions (Strife, Kuchta, Robkea, Quail, Chellain, Kolbet, …) into the 2.1 name sweep. (c) Attribution: a pass that rewrites host allegations and read-out comments stated as fact into "the host alleges" form. Fix every material finding from the baseline | a fresh 2% QA sample is below 2% material. Pass 2 (names first, 2026-10-16 to 10-19, `audits/pass2_2026-10-16/`): fresh sample `audits/qa_after_pass2_2026-10-19/` **0.7% material** |

## Phase 3 — Wave 4: events and things (after all ingest)
**Owner:** Claude · **Ruled:** typed model aligned with schema.org and Wikidata, and the switch to JSON as source of truth happens here

| # | Task | Done when |
|---|---|---|
| 3.0 | ✅ 2026-10-21 (`docs/source/README.md`): phase A, the JSON source with byte-stable render and a CI schema check; phase B, every writing tool goes through the JSON, one-off scripts are fenced, and hand edits use `export`/`import`. **Migrate to JSON as source of truth.** The JSON is the master copy, Markdown is rendered from it, and agents write structured output; all with schema validation in CI | drafts regenerate byte-stable from JSON |
| 3.1 | ✅ 2026-10-21 (`audits/wave4_proposal_2026-10-21/`): 1,360 nodes typed; core events N-10002 assassination, N-11360 arrest, N-11361 memorial. Typed nodes: Event (with `event_time` and place), Thing (rifle, SD card, plane), Organization, Place, Person, and Investigation question; each mapped to a schema.org type and a Wikidata class. For example, a Sept 10 event absorbs N-10002 Death and Memorial, and the "… Question" topics become Investigation questions | each core event has a node with a time; every node has a type |
| 3.2 | ✅ 2026-10-21: 89 duplicate nodes merged into 75 (Fort Huachuca 19 to 1 topic and 1 place plus parented sub-questions). Consolidate the topics: about 1,300 now, including more than ten Fort Huachuca topics. Apply the approved splits | topic count reduced with a merge map; no near-duplicate topic pairs |
| 3.3 | ✅ 2026-10-21: same-host `Supports` now maps to `extends`; 1,150 of 2,477 former `isCorroboratedBy` edges. Fix the companion's corroboration mapping: a same-host `Supports` must not become `isCorroboratedBy` | fixed |

## Phase 4 — Primary sources and the verification layer
4.1–4.3 can start in parallel with Phase 1. Linking (4.5) waits for Wave 4.
**Owner:** Claude · **Ruled:** Tier 1 primary records and Tier 2 reputable reporting as evidence; commentators ingested as speakers, never as evidence; the five-value status (POLICY §11)

| # | Task | Done when |
|---|---|---|
| 4.1 | 🚧 2026-10-22: 13 Tier 1 sources fetched (`sources/manifest.json`, S-1..S-13: the Information, the preliminary and contempt hearings, County Attorney releases, the charging press conference, the UVU After-Action Report, the 2025-09-10 ADS-B archive); Tier 2: 119 articles approved (S-15..S-133; 116 fetched); warrants and FOIA to come. **Source streams** with provenance and a tier. Tier 1: Utah v. Robinson docket and preliminary-hearing transcripts, public warrants, FOIA responses, ADS-B and FAA flight data, and official statements. Tier 2: reputable reporting | each stream has an ingest script, a manifest and a tier |
| 4.1b | 🚧 2026-10-23 pilot (`commentary/`, `audits/commentators_2026-10-23/`): 37 videos (Charlie Kirk Show, Erika Kirk, Harpole, Turek, Baron Coleman), 2,039 claims `CC-*`, 524 confirmed links to host claims (143 contradicts, 37 qualifies, 344 supports); 2026-10-24: +3 Baron Coleman and +4 Paramount Tactical (Gary Melton) episodes from the monitors (K-038..K-044), now 44 videos, 2,537 claims and 623 links. **Commentator speakers.** The Charlie Kirk Show (Kolvet, Neff), Erika Kirk interviews, Baron Coleman and other creators on either side, ingested like the host, as claims | their claims can be linked by Supports, Contradicts and Qualifies; never used as evidence |
| 4.2 | ✅ 2026-10-24 (`audits/monitors_2026-10-24/`): `scripts/daily/monitors.py` polls the Utah court calendar (case 251403576) Google News for 8 key-name queries and 8 commentator YouTube channels (`config/monitors.json`) in every daily run; new alerts land in `ledger/monitor_alerts.{json,md}` and RUNBOOK step M triages them. **External monitors**: alerts on the court docket and on news for the key names, feeding the daily pipeline | alerts land as items in the pipeline |
| 4.3 | ✅ 2026-10-22 (`audits/open_questions_2026-10-22/`): 1,317 questions (1,213 open, 82 partly answered, 22 answered) in `ledger/open_questions.{json,md}`; all 4,888 core claims linked via `Open Questions:`; synced in finalize, daily step in the RUNBOOK. **Open-questions register.** Promote each Investigative Direction into a tracked question: what's known, what would settle it, status, and linked tips | every core claim has its questions registered |
| 4.4 | 🚧 2026-10-21: schema, CI check, inscriptions and companion done; 53 claims are `revised-by-host`; record-based statuses come with 4.5. **Verification status on claims** (POLICY §11): `unverified`, `corroborated`, `disputed`, `contradicted-by-record`, `revised-by-host`, each with cited evidence | schema in the drafts, inscriptions and companion; CI validates it |
| 4.5 | 🚧 2026-10-22 first pass (`audits/verification_record_2026-10-22/`): 4,046 quoted facts from S-1..S-12, 3,634 claims judged plus a wider-recall pass over 3,566, 351 `corroborated` and 37 `contradicted-by-record` set, ledger in `ledger/verification_record.md`; ADS-B 2025-09-10 done (`audits/adsb_2025-10-22/`: 9 corroborated, 1 contradicted); 9/11 file done; Tier 2 rounds 1–2 (`audits/tier2_2026-10-23/`: 100 articles, 216 corroborated). **Verification linking pass.** Link each source-stream document to the claims it bears on, and set the statuses | every core claim has a status other than `unverified`, or an open question explaining why |

## Phase 5 — Revisions and contradictions (the site's lead feature)
**Owner:** Claude (Opus) · **Gate:** Daveed samples the ledger

| # | Task | Done when |
|---|---|---|
| 5.1 | ✅ 2026-10-21 first pass (`audits/phase5_host_vs_herself_2026-10-21/`): 1,458 candidate pairs judged, 35 confirmed links added (31 Revises, 4 Qualifies). For each person and topic, walk the claims in airing order and link real `Revises`, `Contradicts` and `Qualifies` across episodes (the host vs. herself) | each pair is in the ledger with both clips |
| 5.2 | Cross-source contradictions: the host vs. the court record and the flight data (Tier 1), and the host vs. other speakers (commentators, speaker-to-speaker) | linked; record conflicts set `contradicted-by-record` |
| 5.3 | ✅ 2026-10-21 export (`ledger/then_vs_now.md`; 282 links, 87 host vs herself), awaiting Daveed's review. "Then vs. now" ledger export: a reviewable list of pairs with both clips, dates and the delta | Daveed reviews the top pairs that promotion will lead with, plus a random sample |

## Phase 6 — Adversarial re-audit
**Owner:** Bill D and Transit · **Gate:** Daveed rules on the findings

| # | Task | Done when |
|---|---|---|
| 6.1 | ✅ 2026-10-24 by Claude at Daveed's request (`audits/phase6_2026-10-24/`): statuses 4.8% material, then-vs-now 38–41%, allegations 2.2%, random 1.3%; 185 privacy flags; awaiting Daveed's rulings. **Risk-weighted adversarial pass:** every allegation about a named person, every then-vs-now pair and every verification status, plus a random sample of the rest, using the QA rubric from 0.6 and the policy | the findings are filed as PRs or rulings |
| 6.2 | 🚧 2026-10-24: then-vs-now ledger rebuilt (282 → 172 links), 949 titles reframed, 185 privacy claims tangential; status and allegation fixes pending. Claude fixes the findings; CI and QA are rerun | merged |
| 6.3 | **Decide on a second pass:** rerun the affected strata if any stratum's error rate is above the QA target, or if the findings show a systematic problem | Daveed decides from the 6.1 report |

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
| 8.4 | **Legal review** of the ruled display rules (POLICY §6: role-by-default for private individuals, tangential hidden, YouTube embeds), the privacy rules (§10) and the private audio preservation copy | signed off by counsel |
| 8.5 | **Private preservation copy** of the audio of every episode, for takedown resilience; never published | stored with hashes |

## Phase 9 — Site and app (decentralizedintel.agency, Gov Hub campaign)
**Owner:** Claude · **Open decision:** the launch approach (see Rulings, item 9)

| # | Task | Done when |
|---|---|---|
| 9.1 | Load each data release into Gov Hub (`structure_json`) or a small API with search | it loads from a release bundle |
| 9.2 | **Views.** Episode: the video with claim markers on the scrubber. Claim: the snippet, the clip at its timestamp, typed edges, verification status and evidence. Person and topic: first appearance, every claim, and stance over time. Timeline: episodes plus events. The "then vs. now" ledger as the lead feature. Meme and clip tracker for the clip-economy / "fed slop" narrative. Open-questions board with tip submission | usable on staging |
| 9.3 | Search and AI that answer only with citations (claim ids plus clips) and decline otherwise; what-if scenarios per the design doc | evaluated on a question set |
| 9.4 | **Go-public gate**: freeze ids, publish redirects built from the id maps, add share cards for every claim and pair, and Daveed approves the deploy | live |

## Phase 10 — Promotion (starts at launch; the digest can start earlier internally)
**Owner:** Claude drafts, Daveed approves · **Ruled:** a dedicated DIA/CKA account posts in a strictly neutral voice; Daveed amplifies with commentary from his own account

| # | Task | Done when |
|---|---|---|
| 10.1 | **Positioning**: "what was alleged, and what the record shows", stated on the site and in every post | messaging doc approved |
| 10.2 | **"Then vs. now" cards**: two clips, two dates and one link each, auto-generated from the Phase 5 ledger | a card set exists for the top pairs |
| 10.0 | Create the dedicated DIA/CKA account; Daveed holds the credentials | account live |
| 10.3 | **Weekly digest**: new claims, revisions, verification changes and open questions; posted from the DIA/CKA account with deep links, and amplified by Daveed | runs weekly |
| 10.4 | **Open-questions call-outs**: invite evidence on specific open questions (crowdsourced verification with citations) | the tip flow is live |
| 10.5 | **Partnerships**: cross-links with whokilledck.com; researcher and journalist access to the API | at least one partner is live |
| 10.6 | **Search visibility**: a crawlable page per node, claim and episode, with structured data | indexed |

---

## Rulings (Daveed, 2026-10-14)
| # | Decision | Ruling |
|---|---|---|
| 1 | Branch protection | Require the "CKA gates" check on `main`; admins may bypass only in an emergency (Daveed enables it in GitHub settings) |
| 2 | Source of truth | JSON primary, migrated at the start of Wave 4 (3.0); until then, one tested Markdown parser (0.7) |
| 3 | Daily pipeline | Auto-merge when green, except privacy or sensitive-allegation hits, which wait; every PR waits in week one |
| 4 | Event and topic model | Typed model aligned with schema.org and Wikidata |
| 5 | Sources | Tier 1 primary records and Tier 2 reputable reporting as evidence; commentators ingested as speakers, never as evidence; five-value status |
| 6 | Then-vs-now sign-off | Top pairs that promotion will lead with, plus a random sample |
| 7 | Adversarial scope | Risk-weighted first pass; then decide whether a second pass is warranted (6.3) |
| 8 | Display, privacy, clips | Private individuals by role by default, with names once they are public figures in the case; tangential hidden by default; YouTube embeds; a private preservation copy; counsel reviews |
| 9 | Go-public | **Open.** There is no established community of trusted Candace researchers; the engaged audience is X and YouTube creators and commenters on both sides. Options to weigh when the time comes: a beta with a few creators from each side (pressure-tests neutrality, but they may leak or spin it), a soft public launch of one slice (for example the then-vs-now ledger), or a full launch. Decide after Phase 6 |
| 10 | Voice and accounts | A dedicated DIA/CKA account in a strictly neutral voice; Daveed amplifies with commentary |

## Metrics we track
- **Coverage:** claims per minute, per episode; target about 0.9 or more.
- **Quality:** material-error rate from the QA sample, per batch; target < 2%.
- **Freshness:** time from an episode airing to its PR merging; target the same day.
- **Verification:** share of core claims with a status other than `unverified`.
- **Throughput:** 5-hour and weekly usage per batch and per daily run; watched only (Phase 1.6).
