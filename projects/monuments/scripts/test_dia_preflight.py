#!/usr/bin/env python3
"""Smoke tests for DIA preflight (run from repo root)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = ROOT / "projects" / "monuments" / "scripts" / "dia_preflight.py"


def test_self_test_exits_zero():
    proc = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_bride_of_charlie_main_tip_passes():
    proc = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--monument", "bride_of_charlie"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "RESULT: PASS" in proc.stdout


if __name__ == "__main__":
    test_self_test_exits_zero()
    test_bride_of_charlie_main_tip_passes()
    print("ok")
