#!/usr/bin/env python3
"""BOC convenience entrypoint → shared DIA preflight."""
from __future__ import annotations

import runpy
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "scripts" / "dia_preflight.py"

if __name__ == "__main__":
    import sys

    if "--monument" not in sys.argv:
        sys.argv[1:1] = ["--monument", "bride_of_charlie"]
    runpy.run_path(str(_SHARED), run_name="__main__")
