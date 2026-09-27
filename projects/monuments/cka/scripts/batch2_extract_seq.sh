#!/usr/bin/env bash
# Sequential CKA batch-2 extract: normalize to episode_NNN.md after each ep (no long-name ledger drift).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../../" && pwd)"
cd "$ROOT"
for ep in 11 12 13 14 15 16 17 18 19 20; do
  echo "=== CKA extract seq $ep ==="
  EPISODE_ANALYSIS_PROJECT=cka \
  EPISODE_ANALYSIS_OUTPUT=drafts \
  EPISODE_ANALYSIS_TWO_PHASE=0 \
  EPISODE_ANALYSIS_ONLY="$ep" \
  EPISODE_ANALYSIS_FORCE=1 \
  EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS=32000 \
  python3 protocols/episode_analysis/episode_analysis_protocol.py
  shopt -s nullglob
  long=(projects/monuments/cka/drafts/episode_${ep}_*.md)
  if ((${#long[@]})); then
    python3 projects/monuments/cka/scripts/batch2_normalize_draft.py "${long[@]}"
    rm -f "${long[@]}"
  fi
done
echo "BATCH2_EXTRACT_DONE"
