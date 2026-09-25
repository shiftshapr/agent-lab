#!/usr/bin/env python3
"""Convenience wrapper — same as shared monuments preflight with default monument cka."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "scripts" / "dia_preflight.py"

if __name__ == "__main__":
    if "--monument" not in sys.argv:
        sys.argv[1:1] = ["--monument", "cka"]
    runpy.run_path(str(_SHARED), run_name="__main__")
