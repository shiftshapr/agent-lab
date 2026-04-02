"""
Re-exec the current process with agent-lab's .venv interpreter when jsonschema is
missing on the active Python. Covers SSH + Cursor using bare ``python3`` while
deps live in ``uv sync``'s ``.venv``.

Disable with env ``AGENT_LAB_NO_VENV_REEXEC=1``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_AGENT_LAB = Path(__file__).resolve().parent.parent.parent


def maybe_reexec_with_venv_if_jsonschema_missing() -> None:
    if os.environ.get("AGENT_LAB_NO_VENV_REEXEC"):
        return
    try:
        import jsonschema  # noqa: F401
        return
    except ImportError:
        pass
    bindir = _AGENT_LAB / ".venv" / "bin"
    for name in ("python3", "python"):
        candidate = bindir / name
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        try:
            if Path(sys.executable).resolve() == resolved:
                return
        except OSError:
            pass
        os.execv(str(resolved), [str(resolved), *sys.argv])
