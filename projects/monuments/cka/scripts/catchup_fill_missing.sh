#!/usr/bin/env bash
# Fill missing CKA catch-up drafts (seq 21–156): single-pass first, then two-phase.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../../" && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3

missing() {
  "$PY" - <<'PY'
from pathlib import Path
eps={int(x.name.split('_')[1].split('.')[0]) for x in Path('projects/monuments/cka/drafts').glob('episode_*.md')}
print(" ".join(str(e) for e in range(21, 157) if e not in eps))
PY
}

run_one() {
  local ep="$1" two="$2"
  echo "=== fill seq $ep two_phase=$two ==="
  timeout 10800 env \
    EPISODE_ANALYSIS_PROJECT=cka \
    EPISODE_ANALYSIS_OUTPUT=drafts \
    EPISODE_ANALYSIS_TWO_PHASE="$two" \
    EPISODE_ANALYSIS_ONLY="$ep" \
    EPISODE_ANALYSIS_FORCE=1 \
    EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS=32000 \
    "$PY" protocols/episode_analysis/episode_analysis_protocol.py || true
  shopt -s nullglob
  local long=(projects/monuments/cka/drafts/episode_$(printf '%03d' "$ep")_*.md)
  if ((${#long[@]})); then
    "$PY" projects/monuments/cka/scripts/batch2_normalize_draft.py "${long[@]}"
    rm -f "${long[@]}"
  fi
}

for ep in $(missing); do
  ep_file=$(printf 'projects/monuments/cka/drafts/episode_%03d.md' "$ep")
  [[ -f "$ep_file" ]] && continue
  run_one "$ep" 0
  [[ -f "$ep_file" ]] && continue
  run_one "$ep" 1
  [[ -f "$ep_file" ]] || echo "FATAL: still missing $ep_file" >&2
done
echo "FILL_MISSING_DONE"
