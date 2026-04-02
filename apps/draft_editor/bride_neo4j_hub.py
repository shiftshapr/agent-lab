"""
Optional Neo4j read-only summary for the Bride hub (Phase 3).

Uses the same env vars and Cypher as ``projects/.../scripts/neo4j_validate.py``.
If the ``neo4j`` package or the database is unavailable, returns a structured error — never raises to the client.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any


def _import_validate_module(bride_project: Path) -> Any | None:
    script = bride_project / "scripts" / "neo4j_validate.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("bride_neo4j_validate_queries", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fetch_neo4j_summary(
    bride_project: Path,
    *,
    validate: bool = False,
    connection_timeout_sec: float = 5.0,
) -> dict[str, Any]:
    """
    Return graph stats and optional validation issue counts.

    Keys: ``available``, ``stats`` (dict), ``validation`` (optional), ``error`` (optional),
    ``uri`` (sanitized, no password).
    """
    mod = _import_validate_module(bride_project)
    if mod is None:
        return {
            "available": False,
            "stats": {},
            "error": "neo4j_validate.py not found under bride project",
        }

    try:
        from neo4j import GraphDatabase
    except ImportError:
        return {
            "available": False,
            "stats": {},
            "error": "neo4j package not installed (uv add neo4j)",
        }

    uri = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:17687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "openclaw")

    out: dict[str, Any] = {
        "available": False,
        "stats": {},
        "uri": uri.split("@")[-1] if "@" in uri else uri,
        "validation": None,
        "error": None,
    }

    driver = None
    try:
        driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=connection_timeout_sec,
        )
        driver.verify_connectivity()
    except Exception as e:
        out["error"] = str(e)
        return out

    out["available"] = True
    stats_queries = getattr(mod, "STATS_QUERIES", {})
    validation_queries = getattr(mod, "VALIDATION_QUERIES", {})

    try:
        with driver.session() as session:
            for name, qry in stats_queries.items():
                try:
                    rec = session.run(qry).single()
                    out["stats"][name] = int(rec["count"]) if rec else 0
                except Exception as e:
                    out["stats"][name] = None
                    out.setdefault("stats_errors", {})[name] = str(e)

        if validate and validation_queries:
            val: dict[str, Any] = {}
            with driver.session() as session:
                for check_name, cfg in validation_queries.items():
                    try:
                        records = list(session.run(cfg["query"]))
                        val[check_name] = {
                            "count": len(records),
                            "severity": cfg.get("severity", ""),
                            "description": cfg.get("description", ""),
                            "sample": [dict(r) for r in records[:8]],
                        }
                    except Exception as e:
                        val[check_name] = {"count": None, "error": str(e)}
            out["validation"] = val
            crit = sum(
                1
                for v in val.values()
                if isinstance(v, dict)
                and v.get("count")
                and v.get("severity") == "CRITICAL"
            )
            warn = sum(
                1
                for v in val.values()
                if isinstance(v, dict)
                and v.get("count")
                and v.get("severity") == "WARNING"
            )
            out["validation_summary"] = {
                "critical_checks_with_issues": crit,
                "warning_checks_with_issues": warn,
            }
    except Exception as e:
        out["available"] = False
        out["error"] = str(e)
        out["stats"] = {}
    finally:
        if driver is not None:
            driver.close()

    return out
