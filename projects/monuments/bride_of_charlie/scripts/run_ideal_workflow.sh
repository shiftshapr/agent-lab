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
#   --skip-fetch
#   --stop-after N

set -e
# cd to agent-lab (4 levels up from scripts/)
cd "$(dirname "$0")/../../../.."
# Line-buffered output when logging to a file (tail -f works)
export PYTHONUNBUFFERED=1
exec uv run --project framework/deer-flow/backend python \
  -u projects/monuments/bride_of_charlie/scripts/run_full_workflow.py "$@"
