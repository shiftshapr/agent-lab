# CKA roadmap (from 2026-10-14)

The order of work from here to the public site. Rules are in [POLICY.md](POLICY.md). Each phase finishes before the next one starts, except where a step is marked as parallel.

## Where we are (2026-10-14)
- 161 episodes in the manifest. The 19 skeleton episodes are filled, and supplement batches 1–5 are merged to `main`: about 6,800 claims added to the 100 lowest-density episodes.
- Batch 6 (20 episodes) is staged, and about 22 episodes remain after it.
- The person band is dense from N-1 to N-910, and mis-transcribed names are corrected at the source.

## Phase 0 — Foundations (now, in parallel with Phase 1)
- [x] Policy document (`docs/POLICY.md`).
- [x] CI: `.github/workflows/cka-gates.yml` runs the gate suite and the derived-files freshness check on every PR.
- [ ] Daveed turns on branch protection for `main`, requiring the "CKA gates" check.
- [ ] Move the integration tooling from Claude's scratchpad into the repo under `cka/scripts/supplement/`, with tests: `SUPPLEMENT_SPEC.md`, `check_supplement.py`, the inscription merge, the staging fuzzy-duplicate check and the per-episode count verification. Any silent drop, like the batch 2–3 meme bug, then fails a test instead of being caught afterwards.
- [ ] Make the inscription builder copy claim `Tags:` lines itself, so `sync_claim_tags.py` is only a safety net.

## Phase 1 — Finish ingest
- [ ] Supplement batch 6 (seq 5, 8, 16, 20, 23, 33, 42, 43, 56, 69, 78, 83, 91, 94, 99, 102, 121, 131, 139, 145).
- [ ] Supplement batch 7: the last ~22 episodes.
- [ ] Catch up on new episodes (Ep 399, Ep 400 and later), then start the Mon–Thu 4 p.m. PT daily ingest. Run `apply_name_corrections.py` on each new transcript before extraction.
- [ ] Tweets: link the 13-month backfill (3,355 posts plus 77 recovered deletions) to claims, nodes and artifacts.

## Phase 2 — Corrections sweep
- [ ] Names. For every person and topic name that differs between our transcript and HappyScribe, triage the difference, add the corrections to `config/transcript_name_corrections.json`, and re-check the remaining aliases against the policy rule (only spellings the host says).
- [ ] Clear the open review items in the batch audit READMEs, including:
  - the two misattributed older claims (C-1241 and C-3505)
  - Frank Carney vs N-505
  - the "Marina" node, which mixes Minas and Medvin
  - Slauson vs Christiansen
  - Bowyer in Romania, 2010 vs 2011
- [ ] Cross-batch links collected so far, such as ep106's concession qualifying the ep104–105 email claims, and the ep118 self-corrections.
- [ ] Remaining skeleton name checks (the 13 names in `audits/skeleton_fill_2026-10-13/README.md`).

## Phase 3 — Wave 4: events and things (after all ingest)
This waits until ingest is complete, so topics are consolidated once, over the whole corpus.
- [ ] Introduce event and thing nodes with `event_time`, for example a Sept 10 event that absorbs N-10002 Death and Memorial.
- [ ] Consolidate the topic sprawl: about 1,300 topic nodes, including more than ten Fort Huachuca topics. Split topics where approved.
- [ ] Fix the companion's corroboration mapping: same-host `Supports` currently maps to `isCorroboratedBy`.

## Phase 4 — Revisions and Contradictions (the site's differentiator)
- [ ] An Opus pass that walks each person and topic chronologically and links real host walk-backs (`Revises`), explicit rejections (`Contradicts`) and narrowings (`Qualifies`) across episodes. Today there are only 85 `Contradicts` links and few `Revises`.
- [ ] Output: a reviewable ledger of "what she said then vs. now", with both clips for each pair.

## Phase 5 — Adversarial re-audit (Bill D and Transit)
- [ ] One full-archive adversarial pass after Phases 1–4. Findings come back as PRs or rulings for Daveed.

## Phase 6 — Interop
- [ ] Re-vendor BRC-222 2.1 and emit CrosswalkBridges (KnowledgeGraphNode, SKOS match types) with `external_ids`.

## Phase 7 — Public site and app (decentralizedintel.agency, Gov Hub campaign)
- [ ] **Data release.** Each release exports a versioned bundle of the inscriptions, canonical files and companion, with its hash recorded, and loads it into Gov Hub (`structure_json`) or a small API with search.
- [ ] **Views:**
  - Episode: the video with claim markers on the scrubber.
  - Claim: the snippet, a "play this moment" link, and its typed edges.
  - Person and topic: first appearance, every claim, and stance over time.
  - Timeline: episodes plus real-world events.
  - Revisions and Contradictions ledger (the lead feature).
  - Meme and clip tracker: the "fed slop" / clip-economy narrative.
- [ ] Display rules settled with legal (POLICY.md section 6).
- [ ] Search and AI with mandatory citations; what-if scenarios per the design doc.
- [ ] **Go-public gate:** freeze ids, publish redirects from the id maps, and Daveed approves the deploy.
