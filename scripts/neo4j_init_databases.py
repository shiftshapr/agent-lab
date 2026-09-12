#!/usr/bin/env python3
"""
Create agent-lab project databases (meta, boc, dia, pacha) on one or both Neo4j instances.

Usage:
  python scripts/neo4j_init_databases.py
  python scripts/neo4j_init_databases.py --uri bolt://127.0.0.1:27687
  python scripts/neo4j_init_databases.py --all-instances
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from neo4j_platform import (  # noqa: E402
    DEFAULT_URI_PROD,
    DEFAULT_URI_STAGING,
    PLATFORM_DATABASES,
    connect,
    ensure_databases,
    neo4j_auth,
)

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)


def init_uri(uri: str) -> None:
    print(f"[neo4j-init] {uri} …")
    driver = GraphDatabase.driver(uri, auth=neo4j_auth())
    try:
        driver.verify_connectivity()
        from neo4j_platform import COMMUNITY_SHARED_DATABASE, list_database_names

        before = list_database_names(driver)
        ensure_databases(driver, PLATFORM_DATABASES)
        after = list_database_names(driver)
        created = sorted(after - before)
        if created:
            print(f"[neo4j-init] OK — created: {', '.join(created)}")
        elif COMMUNITY_SHARED_DATABASE in after:
            print(
                f"[neo4j-init] OK — Community edition; projects share `{COMMUNITY_SHARED_DATABASE}` "
                f"with label namespaces (BOC vs ML*)"
            )
        else:
            print(f"[neo4j-init] OK — databases: {', '.join(PLATFORM_DATABASES)}")
    finally:
        driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create agent-lab Neo4j project databases")
    parser.add_argument("--uri", action="append", help="Bolt URI (repeatable)")
    parser.add_argument(
        "--all-instances",
        action="store_true",
        help=f"Init prod ({DEFAULT_URI_PROD}) and staging ({DEFAULT_URI_STAGING})",
    )
    args = parser.parse_args()

    uris = list(args.uri or [])
    if args.all_instances:
        uris.extend([DEFAULT_URI_PROD, DEFAULT_URI_STAGING])
    if not uris:
        conn = connect("boc", ensure_database=False)
        try:
            ensure_databases(conn.raw, PLATFORM_DATABASES)
            print(f"[neo4j-init] OK on {conn.raw.get_server_info().address} — {', '.join(PLATFORM_DATABASES)}")
        finally:
            conn.close()
        return

    seen: set[str] = set()
    for uri in uris:
        if uri in seen:
            continue
        seen.add(uri)
        init_uri(uri)


if __name__ == "__main__":
    main()
