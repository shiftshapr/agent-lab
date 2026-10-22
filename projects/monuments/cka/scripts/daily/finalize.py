#!/usr/bin/env python3
"""Daily CKA finalize: mechanical steps after fill_skeleton_integrate.py, then the local gate suite.

- builds the inscriptions for the given seqs (catchup_build_inscription.py) and sets their series to
  "Candace Kirk Archive" (the shared builder defaults to Bride of Charlie);
- applies name corrections, syncs relevance tags and regenerates the BRC-222 companion;
- runs the gates CI runs: dia_preflight (cka, bride_of_charlie, self-test), hostile_hard_gates, check_claim_timestamps
  and, with --pytest, the monuments test suite.
Prints a one-line summary per gate and exits non-zero if any gate fails.

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/daily/finalize.py SEQ [SEQ ...] [--pytest] [--gates-only]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
REPO = CKA.parents[2]
MON = CKA.parent


def sh(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("seqs", nargs="*", type=int)
    ap.add_argument("--pytest", action="store_true")
    ap.add_argument("--gates-only", action="store_true")
    a = ap.parse_args()
    py = sys.executable
    if not a.gates_only and a.seqs:
        for lo, hi in ((min(a.seqs), max(a.seqs)),):
            r = sh([py, str(CKA / "scripts" / "catchup_build_inscription.py"), str(lo), str(hi)])
            if r.returncode != 0:
                print(r.stdout[-2000:], r.stderr[-2000:])
                return 1
        for s in a.seqs:
            p = CKA / "inscription" / f"episode_{s:03d}.json"
            raw = p.read_text(encoding="utf-8")
            d = json.loads(raw)
            d["meta"]["series"] = "Candace Kirk Archive"
            p.write_text(json.dumps(d, indent=2, ensure_ascii="\\u" in raw) + "\n", encoding="utf-8")
    if not a.gates_only:
        for script, extra in ((CKA / "scripts" / "apply_name_corrections.py", []), (CKA / "scripts" / "sync_claim_tags.py", []),
                              (CKA / "scripts" / "sync_node_types.py", []),
                              (CKA / "scripts" / "ledger" / "export_then_vs_now.py", []),
                              (CKA / "scripts" / "verification" / "apply_record.py", []),
                              (CKA / "scripts" / "verification" / "derive_status.py", []),
                              (MON / "scripts" / "cka_brc222_companion.py", [])):
            r = sh([py, str(script)] + extra)
            if r.returncode != 0:
                print(f"FAIL {script.name}: {r.stderr[-1000:]}")
                return 1
    gates = [
        ("preflight cka", [py, str(MON / "scripts" / "dia_preflight.py"), "--monument", "cka"]),
        ("preflight bride_of_charlie", [py, str(MON / "scripts" / "dia_preflight.py"), "--monument", "bride_of_charlie"]),
        ("preflight self-test", [py, str(MON / "scripts" / "dia_preflight.py"), "--self-test"]),
        ("hostile hard gates", [py, str(MON / "scripts" / "hostile_hard_gates.py"), "--monument", "cka"]),
        ("claim timestamps", [py, str(CKA / "scripts" / "check_claim_timestamps.py")]),
        ("tweet links", [py, str(CKA / "scripts" / "tweets" / "merge_links.py"), "--check"]),
        ("source JSON", [py, str(CKA / "scripts" / "source" / "cka_source.py"), "check"]),
    ]
    if a.pytest:
        gates.append(("pytest", [py, "-m", "pytest", "-q", str(MON / "scripts")]))
    ok = True
    for name, cmd in gates:
        r = sh(cmd)
        out = (r.stdout + r.stderr).strip().splitlines()
        issues = [l.strip() for l in out if l.strip().startswith("- [")]
        print(f"{'PASS' if r.returncode == 0 else 'FAIL'} {name}: {out[-1] if out else ''}")
        for l in issues[:30]:
            print("   ", l)
        ok &= r.returncode == 0
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
