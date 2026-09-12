"""
Shared Neo4j connection helpers for agent-lab (prod/staging, per-project databases).

Community Edition uses the shared ``neo4j`` database with label namespaces (BOC vs ML*).
Enterprise can create separate databases (``boc``, ``meta``, …).

Environment:
    NEO4J_URI              Bolt URI (default prod: bolt://127.0.0.1:17687)
    NEO4J_URI_PROD         Production Bolt (Transit / Bill D queries)
    NEO4J_URI_STAGING      Staging Bolt (experiments, --force ingest)
    NEO4J_USER             Default: neo4j
    NEO4J_PASSWORD         Default: openclaw
    NEO4J_DATABASE         Override logical database for current script
    NEO4J_DATABASE_BOC     Default: boc
    NEO4J_DATABASE_META    Default: meta
    NEO4J_DATABASE_DIA     Default: dia
    NEO4J_DATABASE_PACHA   Default: pacha
"""

from __future__ import annotations

import os
import sys
from typing import Any, Iterable

try:
    from neo4j import Driver, GraphDatabase, Session
except ImportError:
    GraphDatabase = None  # type: ignore[misc, assignment]
    Driver = Any  # type: ignore[misc, assignment]
    Session = Any  # type: ignore[misc, assignment]

DEFAULT_URI_PROD = "bolt://127.0.0.1:17687"
DEFAULT_URI_STAGING = "bolt://127.0.0.1:27687"
COMMUNITY_SHARED_DATABASE = "neo4j"

PROJECT_DATABASES = {
    "boc": os.getenv("NEO4J_DATABASE_BOC", "boc"),
    "meta": os.getenv("NEO4J_DATABASE_META", "meta"),
    "dia": os.getenv("NEO4J_DATABASE_DIA", "dia"),
    "pacha": os.getenv("NEO4J_DATABASE_PACHA", "pacha"),
}

PLATFORM_DATABASES = tuple(PROJECT_DATABASES.values())

META_GRAPH_LABELS = (
    "MLSource",
    "MLChunk",
    "MLConcept",
    "MLFramework",
    "MLPrimitive",
    "MLProject",
    "MLEntity",
)

BOC_GRAPH_LABELS = (
    "Episode",
    "Artifact",
    "ArtifactFamily",
    "Claim",
    "Person",
    "Topic",
    "Organization",
    "Place",
    "InvestigationTarget",
    "LegalMatter",
    "Meme",
    "NameCorrection",
)


def neo4j_uri() -> str:
    return os.getenv("NEO4J_URI", DEFAULT_URI_PROD)


def neo4j_auth() -> tuple[str, str]:
    return (
        os.getenv("NEO4J_USER", "neo4j"),
        os.getenv("NEO4J_PASSWORD", "openclaw"),
    )


def database_for_project(project: str) -> str:
    """Logical project database name (``boc``, ``meta``, …)."""
    if project not in PROJECT_DATABASES:
        raise ValueError(f"Unknown project {project!r}; expected one of {sorted(PROJECT_DATABASES)}")
    override = os.getenv("NEO4J_DATABASE")
    if override:
        return override
    return PROJECT_DATABASES[project]


def list_database_names(driver: Driver) -> set[str]:
    with driver.session(database="system") as session:
        return {record["name"] for record in session.run("SHOW DATABASES")}


def resolve_session_database(driver: Driver, logical: str) -> tuple[str, str]:
    """Return ``(bolt_session_database, logical_database)``."""
    available = list_database_names(driver)
    if logical in available:
        return logical, logical
    return COMMUNITY_SHARED_DATABASE, logical


class DatabaseDriver:
    """Wraps a Neo4j driver with a default database for ``session()`` calls."""

    def __init__(self, driver: Driver, session_database: str, logical_database: str):
        self._driver = driver
        self.database = session_database
        self.logical_database = logical_database

    def session(self, **kwargs: Any) -> Session:
        if "database" not in kwargs:
            kwargs["database"] = self.database
        return self._driver.session(**kwargs)

    def verify_connectivity(self, **kwargs: Any) -> None:
        self._driver.verify_connectivity(**kwargs)

    def close(self) -> None:
        self._driver.close()

    @property
    def raw(self) -> Driver:
        return self._driver

    @property
    def uses_shared_community_database(self) -> bool:
        return self.database == COMMUNITY_SHARED_DATABASE and self.logical_database != COMMUNITY_SHARED_DATABASE


def _require_driver() -> None:
    if GraphDatabase is None:
        raise RuntimeError("neo4j driver not installed. Run: uv add neo4j")


def connect(project: str, *, uri: str | None = None, ensure_database: bool = False) -> DatabaseDriver:
    """Connect to Neo4j and return a database-scoped driver wrapper."""
    _require_driver()
    logical = database_for_project(project)
    resolved_uri = uri or neo4j_uri()
    driver = GraphDatabase.driver(resolved_uri, auth=neo4j_auth())
    driver.verify_connectivity()
    session_db, logical_db = resolve_session_database(driver, logical)
    if ensure_database:
        ensure_databases(driver, [logical_db])
    return DatabaseDriver(driver, session_db, logical_db)


def connect_boc(*, uri: str | None = None, ensure_database: bool = False) -> DatabaseDriver:
    return connect("boc", uri=uri, ensure_database=ensure_database)


def connect_boc_or_exit(*, ensure_database: bool = False, label: str = "neo4j") -> DatabaseDriver:
    """Connect to the BOC database or print an error and exit."""
    uri = neo4j_uri()
    logical = database_for_project("boc")
    print(f"[{label}] Connecting to {uri} (database: {logical})...")
    try:
        conn = connect_boc(uri=uri, ensure_database=ensure_database)
        if conn.uses_shared_community_database:
            print(f"[{label}] Community edition — using shared `{conn.database}` database (BOC labels only)")
        return conn
    except Exception as exc:
        print(f"ERROR: Could not connect to Neo4j: {exc}")
        print("Make sure Neo4j is running: docker compose up -d")
        sys.exit(1)


def connect_meta(*, uri: str | None = None, ensure_database: bool = False) -> DatabaseDriver:
    return connect("meta", uri=uri, ensure_database=ensure_database)


def ensure_databases(driver: Driver | DatabaseDriver, names: Iterable[str] | None = None) -> None:
    """Create project databases when supported (Neo4j Enterprise)."""
    raw = driver.raw if isinstance(driver, DatabaseDriver) else driver
    targets = list(names or PLATFORM_DATABASES)
    available = list_database_names(raw)
    missing = [name for name in targets if name not in available]
    if not missing:
        return
    try:
        with raw.session(database="system") as session:
            for name in missing:
                session.run(f"CREATE DATABASE `{name}` IF NOT EXISTS")
    except Exception as exc:
        if "UnsupportedAdministrationCommand" in type(exc).__name__ or "Unsupported administration" in str(exc):
            return
        raise


def _has_dedicated_database(conn: DatabaseDriver, project: str) -> bool:
    logical = PROJECT_DATABASES[project]
    return conn.database == logical and conn.database != COMMUNITY_SHARED_DATABASE


def clear_boc_graph(conn: DatabaseDriver, *, preserve_name_corrections: bool = True) -> None:
    """
    Clear Bride of Charlie graph data.

    On a dedicated ``boc`` database (Enterprise), wipe all nodes except NameCorrection.
    On Community (shared ``neo4j`` database), delete only BOC-labeled nodes.
    """
    with conn.session() as session:
        if _has_dedicated_database(conn, "boc"):
            if preserve_name_corrections:
                session.run(
                    """
                    MATCH (n)
                    WHERE NOT n:NameCorrection
                    DETACH DELETE n
                    """
                )
            else:
                session.run("MATCH (n) DETACH DELETE n")
            return

        label_match = " OR ".join(f"n:{label}" for label in BOC_GRAPH_LABELS)
        if preserve_name_corrections:
            session.run(
                f"""
                MATCH (n)
                WHERE ({label_match}) AND NOT n:NameCorrection
                DETACH DELETE n
                """
            )
        else:
            session.run(
                f"""
                MATCH (n)
                WHERE {label_match}
                DETACH DELETE n
                """
            )


def clear_meta_graph(conn: DatabaseDriver) -> None:
    """Clear meta-layer graph data (dedicated ``meta`` DB or ML* labels on Community)."""
    with conn.session() as session:
        if _has_dedicated_database(conn, "meta"):
            session.run("MATCH (n) DETACH DELETE n")
            return
        label_match = " OR ".join(f"n:{label}" for label in META_GRAPH_LABELS)
        session.run(
            f"""
            MATCH (n)
            WHERE {label_match}
            DETACH DELETE n
            """
        )


def browser_url_for_uri(uri: str | None = None) -> str:
    """Best-effort HTTP browser URL from a Bolt URI."""
    resolved = uri or neo4j_uri()
    if "27687" in resolved:
        return "http://localhost:27474"
    if "17687" in resolved:
        return "http://localhost:17474"
    return "http://localhost:7474"
