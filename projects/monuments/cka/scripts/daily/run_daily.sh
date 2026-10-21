#!/usr/bin/env bash
# CKA daily pipeline launcher (ROADMAP 1.4). Run by launchd Mon–Fri 16:00 PT, or by hand.
# 1. Refreshes the dedicated daily worktree to a fresh branch from origin/main.
# 2. Runs intake.py (new episodes -> transcripts, manifest, skeleton drafts, extraction pack).
# 3. If there is anything new, runs a headless Claude Code session on docs/daily/RUNBOOK.md.
# 4. Stores the session's final message in WORK/summary.md and shows a macOS notification.
# Usage: run_daily.sh [--intake-only]
set -euo pipefail
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
MAIN="${CKA_MAIN_REPO:-$HOME/agent-lab}"
REPO="${CKA_DAILY_WORKTREE:-$HOME/agent-lab-wt-daily}"
DATE="$(TZ=America/Los_Angeles date +%Y-%m-%d)"
WORK="$HOME/agent-lab-data/cka_daily/$DATE"
LOG="$WORK/run.log"
mkdir -p "$WORK"
exec >>"$LOG" 2>&1
echo "=== $(date) CKA daily $DATE ==="

if [[ ! -d "$REPO" ]]; then
  git -C "$MAIN" fetch -q origin
  git -C "$MAIN" worktree add -q "$REPO" origin/main
fi
cd "$REPO"
if [[ "${1:-}" != "--intake-only" ]] && ! claude -p "Reply with the single word ok." --model haiku >/dev/null 2>&1; then
  echo "claude CLI is not logged in (run 'claude' then /login on the Mac mini); nothing touched"
  osascript -e 'display notification "CKA daily: claude CLI login expired. Run claude, then /login." with title "CKA daily"' || true
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "daily worktree is dirty (an earlier run did not finish); leaving it for review"
  osascript -e 'display notification "CKA daily: worktree dirty from an earlier run; not started" with title "CKA daily"' || true
  exit 1
fi
git fetch -q origin
git checkout -q -B "cka-daily-$DATE" origin/main

set +e
python3 projects/monuments/cka/scripts/daily/intake.py "$WORK"
rc=$?
python3 projects/monuments/cka/scripts/daily/tweets_intake.py "$WORK"
trc=$?
set -e
if [[ $rc -ne 0 && $rc -ne 3 ]] || [[ $trc -ne 0 && $trc -ne 3 ]]; then
  osascript -e 'display notification "CKA daily: intake failed; see run.log" with title "CKA daily"' || true
  [[ $rc -ne 0 && $rc -ne 3 ]] && exit $rc
fi
if [[ $rc -ne 0 && $trc -ne 0 ]]; then
  echo "nothing new"
  git checkout -q -- . 2>/dev/null || true
  exit 0
fi
[[ "${1:-}" == "--intake-only" ]] && exit 0

STEPS=""
[[ $rc -eq 0 ]] && STEPS="episodes (steps 1-5; new episodes are in $WORK/new_episodes.json)"
[[ $trc -eq 0 ]] && STEPS="${STEPS:+$STEPS, then }tweets (step T; the pack is $WORK/tweets_pack)"
PROMPT="You are running the CKA daily pipeline unattended. REPO=$REPO WORK=$WORK DATE=$DATE.
Follow $REPO/projects/monuments/cka/docs/daily/RUNBOOK.md exactly for: $STEPS.
Use Opus for every subagent. Merge the PR only when the gates check is green. End with the summary described in step 6."
claude -p "$PROMPT" --model opus --permission-mode bypassPermissions --output-format text > "$WORK/summary.md" || true
echo "=== $(date) done; summary in $WORK/summary.md ==="
osascript -e "display notification \"$(head -c 180 "$WORK/summary.md" | tr '\n"' '  ')\" with title \"CKA daily $DATE\"" || true
