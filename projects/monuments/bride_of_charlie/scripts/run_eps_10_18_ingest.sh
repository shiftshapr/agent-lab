#!/usr/bin/env bash
set -euo pipefail
cd /workspace
export EPISODE_ANALYSIS_PROJECT=bride_of_charlie
export EPISODE_ANALYSIS_INPUT=transcripts_corrected
export EPISODE_ANALYSIS_OUTPUT=drafts
export EPISODE_ANALYSIS_TWO_PHASE=1
export EPISODE_ANALYSIS_MAX_OUTPUT_TOKENS=32768
export EPISODE_ANALYSIS_FORCE=1
export NEO4J_AUTO_INGEST=0

for ep in 10 11 12 13 14 15 16 17 18; do
  echo "========== EPISODE $ep =========="
  python3 agents/protocol/protocol_agent.py --protocol episode_analysis --project bride_of_charlie --force --only "$ep" || {
    echo "FAILED episode $ep" | tee -a /tmp/boc_eps_failures.log
  }
done
echo "ALL DONE"
