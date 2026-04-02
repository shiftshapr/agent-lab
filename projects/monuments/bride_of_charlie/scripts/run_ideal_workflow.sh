#!/usr/bin/env bash
#
# Run the ideal workflow from agent-lab root.
#
# Usage:
#   cd ~/workspace/agent-lab
#   ./projects/monuments/bride_of_charlie/scripts/run_ideal_workflow.sh
#
# Options: pass through to run_full_workflow.py
#   --no-backup
#   --skip-search
#   --skip-fetch   (never fetch, even if episode transcripts missing)
#   --stop-after N
# Env: BRIDE_STOP_AFTER_GREEN_VALIDATE=1
#      BRIDE_EXPECTED_EPISODES — optional; if unset, expected count = non-comment lines in
#      input/youtube_links.txt (add a URL there → next run fetches missing transcripts)

set -e
# cd to agent-lab (4 levels up from scripts/)
cd "$(dirname "$0")/../../../.."
# Neo4j ingest / validate need NEO4J_*; API keys live here too
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
# Line-buffered output when logging to a file (tail -f works)
export PYTHONUNBUFFERED=1
exec uv run --project framework/deer-flow/backend python \
  -u projects/monuments/bride_of_charlie/scripts/run_full_workflow.py "$@"
