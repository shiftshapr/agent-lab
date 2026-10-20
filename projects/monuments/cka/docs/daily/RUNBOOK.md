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
4. Wait for the `gates` check. If it passes, merge it (`gh pr merge <n> --merge`); Daveed has authorized merging
   when green. If it fails, fix it, push, and wait again. If you cannot fix it, leave the PR open and say why.

## 6. Notify
End with a short final message: episodes added, claims, intake material rate, PR link and merge state, and the
review items (text + timestamped link). The launcher stores it in `WORK/summary.md` and sends Daveed a
notification.
