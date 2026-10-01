#!/usr/bin/env bash
set -euo pipefail
cd /workspace
while pgrep -f 'catchup_extract_seq.sh 25 156' >/dev/null; do
  n=$(python3 - <<'PY'
from pathlib import Path
eps={int(x.name.split('_')[1].split('.')[0]) for x in Path('projects/monuments/cka/drafts').glob('episode_*.md')}
print(len([e for e in range(21,157) if e in eps]))
PY
)
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) catchup_drafts=$n/136 $(tail -1 /tmp/cka-catchup-extract5.log 2>/dev/null || true)" >> /tmp/cka-catchup-status.log
  sleep 300
done
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) extract exited; running finalize" >> /tmp/cka-catchup-status.log
bash projects/monuments/cka/scripts/catchup_finalize.sh >> /tmp/cka-catchup-finalize.log 2>&1 || true
