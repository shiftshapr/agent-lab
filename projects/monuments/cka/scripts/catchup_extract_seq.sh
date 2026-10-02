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
FAILED=()
for ep in $(seq "$LO" "$HI"); do
  ep_file=$(printf 'projects/monuments/cka/drafts/episode_%03d.md' "$ep")
  if [[ -f "$ep_file" ]]; then
    echo "=== skip CKA seq $ep (draft exists) ==="
    continue
  fi
  echo "=== CKA extract seq $ep ==="
  if ! timeout 10800 env \
    EPISODE_ANALYSIS_PROJECT=cka \
    EPISODE_ANALYSIS_OUTPUT=drafts \
    EPISODE_ANALYSIS_TWO_PHASE=1 \
    EPISODE_ANALYSIS_ONLY="$ep" \
    EPISODE_ANALYSIS_FORCE=1 \
    EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS=32000 \
    "$PY" protocols/episode_analysis/episode_analysis_protocol.py; then
    echo "WARN: extract failed or timed out for seq $ep" >&2
  fi
  shopt -s nullglob
  long=(projects/monuments/cka/drafts/episode_$(printf '%03d' "$ep")_*.md)
  if ((${#long[@]})); then
    "$PY" projects/monuments/cka/scripts/batch2_normalize_draft.py "${long[@]}"
    rm -f "${long[@]}"
  fi
  if [[ ! -f "$ep_file" ]]; then
    echo "ERROR: missing $ep_file after extract (will retry at end)" >&2
    FAILED+=("$ep")
    continue
  fi
done
if ((${#FAILED[@]})); then
  echo "=== retry failed episodes: ${FAILED[*]} ==="
  for ep in "${FAILED[@]}"; do
    ep_file=$(printf 'projects/monuments/cka/drafts/episode_%03d.md' "$ep")
    [[ -f "$ep_file" ]] && continue
    echo "=== CKA retry seq $ep ==="
    timeout 10800 env \
      EPISODE_ANALYSIS_PROJECT=cka \
      EPISODE_ANALYSIS_OUTPUT=drafts \
      EPISODE_ANALYSIS_TWO_PHASE=1 \
      EPISODE_ANALYSIS_ONLY="$ep" \
      EPISODE_ANALYSIS_FORCE=1 \
      EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS=32000 \
      "$PY" protocols/episode_analysis/episode_analysis_protocol.py || true
    shopt -s nullglob
    long=(projects/monuments/cka/drafts/episode_$(printf '%03d' "$ep")_*.md)
    if ((${#long[@]})); then
      "$PY" projects/monuments/cka/scripts/batch2_normalize_draft.py "${long[@]}"
      rm -f "${long[@]}"
    fi
    [[ -f "$ep_file" ]] || echo "FATAL: still missing $ep_file" >&2
  done
fi
echo "CATCHUP_EXTRACT_DONE"
