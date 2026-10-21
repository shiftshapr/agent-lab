#!/usr/bin/env bash
if [[ "${CKA_ALLOW_LEGACY:-}" != "1" ]]; then echo "$0: one-off script from before the JSON source of truth (ROADMAP 3.0); set CKA_ALLOW_LEGACY=1 to run, then cka_source.py sync" >&2; exit 1; fi
# Finalize CKA catch-up after catchup_extract_seq.sh: postprocess, inscription, preflight.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../../" && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3
"$PY" projects/monuments/cka/scripts/catchup_postprocess.py
"$PY" projects/monuments/cka/scripts/catchup_build_inscription.py 21 156
"$PY" projects/monuments/scripts/dia_preflight.py --monument cka --json /tmp/cka-catchup-preflight.json
echo "FINALIZE_OK"
