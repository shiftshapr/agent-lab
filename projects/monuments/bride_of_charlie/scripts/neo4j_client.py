"""Bride of Charlie Neo4j client (wraps agent-lab ``neo4j_platform``)."""

from __future__ import annotations

import sys
from pathlib import Path

_AGENT_LAB = Path(__file__).resolve().parents[4]
_scripts = str(_AGENT_LAB / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from neo4j_platform import (  # noqa: E402
    browser_url_for_uri,
    clear_boc_graph,
    connect_boc,
    connect_boc_or_exit,
    database_for_project,
    neo4j_uri,
)

__all__ = [
    "browser_url_for_uri",
    "clear_boc_graph",
    "connect_boc",
    "connect_boc_or_exit",
    "database_for_project",
    "neo4j_uri",
]
