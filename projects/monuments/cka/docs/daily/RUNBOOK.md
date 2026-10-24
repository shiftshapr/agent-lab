# CKA daily pipeline runbook (ROADMAP 1.4)

`scripts/daily/run_daily.sh` runs Mon–Fri at 4 p.m. PT (Thursday shows are picked up Friday). It runs `scripts/daily/intake.py`. If there are new
episodes, it starts a headless Claude Code session with this runbook. That session works in the dedicated daily
worktree, on a fresh branch from `origin/main`. `REPO` and `WORK` below come from the launcher.

All commands run from `REPO` (the agent-lab root). Use Opus for every subagent. Never write to Neo4j, deploy,
pack, promote, run `gh auth login`, send X cookies or accept SSH host keys.

## 0. Inputs
- `WORK/new_episodes.json` lists the episodes intake prepared (seq, Candace Ep, YouTube id, date, transcript).
  Their transcripts, skeleton drafts, manifest rows and name corrections are already in the working tree.
- `WORK/pack/` is the extraction pack: `EXTRACT_PROMPT.md`, `SPEC.md`, `nodes.tsv`, `memes.tsv`, `claims_index.tsv`
  and `staging/`.

## 1. Extract (one Opus subagent per episode, in parallel)
Prompt: "Follow `WORK/pack/EXTRACT_PROMPT.md` exactly for NNN = <seq>. `<REPO>` is `REPO`. The reference pack is
`WORK/pack`. Transcript: <path>. Skeleton draft: `REPO/projects/monuments/cka/drafts/episode_<seq>.md`. Write
`WORK/pack/staging/episode_<seq>.md` and edit no other file."

Wait for all of them. Then confirm each passes:
`SKELETON_PACK=WORK/pack python3 -I projects/monuments/cka/scripts/check_skeleton_staging.py <seqs>`.

## 2. Integrate
1. Run `python3 projects/monuments/cka/scripts/fill_skeleton_integrate.py WORK/pack/staging --batch daily-<YYYY-MM-DD> --dry-run`.
   - Read the notes: new nodes mapped onto existing names, and nodes cited before their introduction.
   - Make the same person minted in two episodes one name, so it dedupes.
   - Where a middle name or detail is unconfirmed, use the plainer name.
2. Run it again without `--dry-run`.
3. Run `python3 projects/monuments/cka/scripts/daily/finalize.py <seqs>`.

### Editing episodes (ROADMAP 3.0)
`source/episode_NNN.json` is the master copy, and `drafts/episode_NNN.md` is rendered from it. **Never write a draft
directly.** The tools (integrators, name corrections, apply_fixes, renumber and merge) already go through the JSON. For
a hand edit:
1. `python3 projects/monuments/cka/scripts/source/cka_source.py export NNN > WORK/epNNN.md`
2. Edit `WORK/epNNN.md`.
3. `python3 projects/monuments/cka/scripts/source/cka_source.py import NNN WORK/epNNN.md`
The CI gate `cka_source.py check` fails if a draft differs from its JSON.

### Fixing gate failures (known patterns)
- **mention_grounding:**
  - Drop a person id that rests only on inference or a first name.
  - For a real role reference ("her husband", "the governor"), add a `mention_grounding.reviewed` entry
    (`{"claim", "node", "reason"}`) in `config/preflight_gates.json`.
- **named_before_intro / cited_before_intro:**
  - Move the introduction to the first episode that names the node. In that episode:
    - add the id to a `Tip-minted Nodes (reintro-epNNN)` ledger line (or `Hole-minted …` for an older id), in
      ascending id order;
    - add a Node Register row before `**N-3** Candace Owens`, an inscription node and the Mentions link;
    - add the episode to the node's `episodes` list in `canonical/nodes.json`.
  - In the episode that had introduced it, take the id off its minted line and add it to `Reused Nodes Appearing`.
    Ids never change.
  - Use `named_before_intro.accepted` (`{"id", "episodes", "reason"}`) only for a known duplicate awaiting a merge.
- **remap_sync:** a scoped name rule renamed the register row but not the node. Rename the node's `canonical_name`
  directly.
- **Never add a mis-transcription as an alias.**

## 3. Names
Turn each `MISTRANSCRIPTION:` flag in the new drafts' Optional Flags into a rule in
`config/transcript_name_corrections.json`:
- `[pattern, replacement, [seqs]]`. Scope it to the new seqs unless the wrong form is unique and cannot be a real
  word or name elsewhere.
- Skip medium-confidence or inference-only flags. Skip flags where the host may have misspoken herself.
- Never "correct" the host's deliberate nicknames or jokes. For example, she calls Laura Loomer "Larry"; the
  captions are right. Check the source captions (`WORK/captions/*.en-orig.vtt`) when unsure.
- "Erica" becomes "Erika" only as a seq-scoped rule.

Rerun `finalize.py <seqs>`. Check that rules hitting older transcripts are correct:
`git diff -U0 -- projects/monuments/cka/transcripts_corrected/`.

For names flagged as unresolved, check the HappyScribe transcript of the same episode
(https://podcasts.happyscribe.com/candace, WebFetch; it may lag by a few days). Web-search
`"<name>" "Charlie Kirk"`. Correct only with a source.

## 4. Opus check at intake
1. Run `grep -ho "^\*\*C-[0-9]*\*\*" projects/monuments/cka/drafts/episode_<seq>.md | tr -d '*' > WORK/claims.txt`
   for all new seqs.
2. Run `python3 projects/monuments/cka/scripts/qa/verify_pack.py --chunk 60 --claims WORK/claims.txt WORK/verify`.
   Then write `WORK/verify/PROMPT.md` from `projects/monuments/cka/docs/qa/VERIFY_PROMPT.md`, with `<PACK>`
   replaced by `WORK/verify`.
3. One Opus subagent per chunk: "Follow `WORK/verify/PROMPT.md` for NNN = <chunk>. The repository is `REPO`;
   transcripts are in `projects/monuments/cka/transcripts_corrected/`. Edit no file other than `results_<NNN>.json`."
4. Run `python3 projects/monuments/cka/scripts/qa/drop_inwindow_timestamps.py WORK/verify`, then
   `python3 projects/monuments/cka/scripts/qa/norm_results.py WORK/verify`.
5. Run `python3 projects/monuments/cka/scripts/qa/confirm_pack.py WORK/verify WORK/confirm --chunk 40`. Then write
   `WORK/confirm/PROMPT.md` from `docs/qa/CONFIRM_PROMPT.md`, with `<PACK>` replaced by `WORK/confirm`.
6. One Opus subagent per confirm chunk.
7. Run `python3 projects/monuments/cka/scripts/qa/apply_fixes.py WORK/verify WORK/confirm WORK/applied.json WORK/names.json`.
8. Turn confirmed name fixes in `WORK/names.json` into rules (as in step 3). Where a scoped rule renames a node, also
   rename the node directly.
9. Run `finalize.py <seqs> --pytest`. Every gate must pass.

### Open questions (ROADMAP 4.3)
After finalize, `apply_register.py` reports "core claims without a question". Each new core claim must be linked to
the register in `ledger/open_questions.json`, so give one Opus subagent the new core claims, with their Investigative
Directions, and the register's questions on the same topics. For each claim it either links the claim to 1–3
existing questions, or drafts a new question with topic, question, known, settle, status (`open` unless an S-id
settles it), evidence, claims and tips, phrased neutrally. Write the result as a JSON list and run
`python3 projects/monuments/cka/scripts/questions/apply_register.py --add FILE --strict`, which must exit 0. List the
new questions in the audit README.

## T. Tweets (ROADMAP 1.5)
`tweets_intake.py` has already fetched new @RealCandaceO posts into `tweets/tweets.jsonl` and built `WORK/tweets_pack`.
1. Run one Opus subagent per `tweets_<NNN>.md` chunk with this prompt: "Follow `WORK/tweets_pack/PROMPT.md` for
   NNN = <n>. The repository is `REPO`. Edit no file other than `links_<n>.json`." If episodes were integrated in this
   run, rebuild the pack first so their claims are candidates:
   `python3 projects/monuments/cka/scripts/tweets/link_pack.py WORK/tweets_pack`.
2. Merge: `python3 projects/monuments/cka/scripts/tweets/merge_links.py WORK/tweets_pack --check`. It must report 0 problems.
3. In the audit README, add a short tweets section: posts added, linked to claims, nodes only, and unlinked. Add any
   post that contradicts or walks back an archived claim as a review item, with its URL.

## M. Monitor alerts (ROADMAP 4.2)
`monitors.py` has already polled the Utah court calendar, Google News and the commentators' YouTube channels
(`config/monitors.json`), written the new
alerts to `WORK/monitor_alerts.json` and appended them to `ledger/monitor_alerts.json` with `status: "new"`. Alerts
are leads, never evidence. Do not download any article.
1. Triage every new alert in `ledger/monitor_alerts.json` (one Opus subagent per 80 alerts if there are many):
   - set `status` to `triaged` when it bears on the case, or `ignored` when it is off-topic (another "Kirk", unrelated
     politics, a duplicate wire copy);
   - for triaged items set `triage` to one short sentence: what is new, and the open question ids it bears on
     (`ledger/open_questions.json`), if any;
   - **court calendar** entries: say what hearing is scheduled; a new or changed hearing is a review item.
   - **commentator videos** (`kind: youtube`): triage when the title shows the speaker discussing the case, and set
     `candidate: true` when it is a substantive, long-form discussion by a commentary-series speaker (4.1b). Ignore
     unrelated topics and short clips of material already in `commentary/episodes.json`.
2. Re-render: `python3 projects/monuments/cka/scripts/daily/monitors.py WORK --render`.
3. In the summary, list as review items:
   - every new court calendar entry;
   - triaged **Tier 2** news that reports something new about the case, as candidates for Daveed's approval. Only
     after he approves are they added to the `tier2-reporting` stream and fetched (`scripts/sources/fetch.py`);
   - candidate **commentator videos**, for Daveed's approval before they are added to the commentary series
     (`scripts/commentary/fetch.py`, then extraction and linking as in `audits/commentators_2026-10-23/`).
4. Commit the ledger with the rest of the run. A run with only monitor alerts uses the commit message
   `CKA daily <date>: monitor alerts` and the same PR and merge rules.

## 5. Record, PR, merge
1. Write `projects/monuments/cka/audits/daily_<YYYY-MM-DD>/README.md`, modelled on
   `audits/catchup_2026-10-19/README.md`:
   - per-episode table (seq, Ep, date, id, claims);
   - new nodes;
   - rules added;
   - intake check numbers;
   - **Review items**: each unresolved name or open question with the transcript text and a timestamped
     `https://youtu.be/<id>?t=<seconds>` link.
2. Copy `WORK/verify/results_*.json`, `WORK/confirm/confirmed_*.json` and `WORK/applied.json` into
   `audits/daily_<YYYY-MM-DD>/verify/`.
3. Commit with a message like `CKA daily <date>: Ep N (seq S), K claims`, ending with the Co-Authored-By line.
   Push the branch and open a PR to main whose body ends with the Claude Code line.
4. Wait for the `gates` check. Merge only when **all** of these hold (Daveed's ruling 3, 2026-10-14):
   - the check is green;
   - the run date is 2026-10-27 or later (every PR waits for Daveed during the pipeline's first week, from 2026-10-20);
   - the run has no privacy or sensitive-allegation hits.

   A hit is any new claim that does one of the following:
   - alleges a crime or sexual misconduct by a named private individual;
   - names a minor;
   - gives a private person's address, phone, licence plate or similar details;
   - concerns a private individual's personal life.

   Otherwise leave the PR open and put "Waiting for Daveed: <reason>" at the top of the summary. If the check fails,
   fix it, push and wait again; if you cannot fix it, leave the PR open and say why.

## 6. Notify
End with a short final message: episodes added, claims, monitor alerts (new, triaged, Tier 2 candidates, court entries), intake material rate, PR link and merge state, and the
review items (text + timestamped link). The launcher stores it in `WORK/summary.md` and sends Daveed a
notification.
