#!/usr/bin/env bash
# CKA catch-up extract: seq 21–156 (normalize to episode_NNN.md after each ep).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../../" && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
LO="${1:-21}"
HI="${2:-156}"
for ep in $(seq "$LO" "$HI"); do
  if [[ -f "projects/monuments/cka/drafts/episode_${ep}.md" ]]; then
    echo "=== skip CKA seq $ep (draft exists) ==="
    continue
  fi
  echo "=== CKA extract seq $ep ==="
  if ! timeout 2400 env \
    EPISODE_ANALYSIS_PROJECT=cka \
    EPISODE_ANALYSIS_OUTPUT=drafts \
    EPISODE_ANALYSIS_TWO_PHASE=0 \
    EPISODE_ANALYSIS_ONLY="$ep" \
    EPISODE_ANALYSIS_FORCE=1 \
    EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS=32000 \
    "$PY" protocols/episode_analysis/episode_analysis_protocol.py; then
    echo "WARN: extract failed or timed out for seq $ep" >&2
  fi
  shopt -s nullglob
  long=(projects/monuments/cka/drafts/episode_${ep}_*.md)
  if ((${#long[@]})); then
    "$PY" projects/monuments/cka/scripts/batch2_normalize_draft.py "${long[@]}"
    rm -f "${long[@]}"
  fi
  if [[ ! -f "projects/monuments/cka/drafts/episode_${ep}.md" ]]; then
    echo "ERROR: missing episode_${ep}.md after extract" >&2
    exit 1
  fi
done
echo "CATCHUP_EXTRACT_DONE"
