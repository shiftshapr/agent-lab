#!/usr/bin/env python3
"""CKA epistemic graph §5 acceptance smoke (staging only).

Defaults to bolt://127.0.0.1:27687 (neo4j/openclaw). Refuses prod host port
17687 unless an undocumented unsafe flag is passed. Does not start Neo4j,
does not wipe, does not write.

Design note §5 queries:
  1. As-of claim (Episode ASSERTS + MENTIONS)
  2. Evidence walk (SUPPORTED_BY + APPEARS_IN)
  3. Revision chain (REVISES)
  4. Disagreement set (CONTRADICTS)
  5. Competitors at locus (CAPTURED_AT + window)
  6. Person <-> org (CONNECTED_TO + co-APPEARS_IN)
  7. LLM retrieval spine (seed claim -> evidence -> competitors)
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

STAGING_URI_DEFAULT = "bolt://127.0.0.1:27687"
PROD_BOLT_PORT = "17687"
STAGING_BOLT_PORT = "27687"


def uri_looks_like_prod(uri: str) -> bool:
    u = (uri or "").strip().lower()
    return f":{PROD_BOLT_PORT}" in u or u.endswith(f"/{PROD_BOLT_PORT}")


QUERIES: list[tuple[str, str]] = [
    (
        "1_as_of_claim",
        """
        MATCH (e:Episode)-[:ASSERTS]->(c:Claim)
        OPTIONAL MATCH (c)-[:MENTIONS]->(p:Person)
        RETURN e.episode_num AS episode_num, c.id AS claim_id, c.claim_ts AS claim_ts,
               collect(DISTINCT p.id) AS mentioned_persons
        ORDER BY e.episode_num, c.claim_ts, c.id
        LIMIT 25
        """,
    ),
    (
        "2_evidence_walk",
        """
        MATCH (c:Claim)-[:SUPPORTED_BY]->(a:Artifact)-[:APPEARS_IN]->(e:Episode)
        RETURN c.id AS claim_id, a.id AS artifact_id, e.episode_num AS episode_num,
               a.video_ts AS video_ts
        ORDER BY c.id, a.id
        LIMIT 25
        """,
    ),
    (
        "3_revision_chain",
        """
        MATCH (newer:Claim)-[:REVISES]->(older:Claim)
        RETURN newer.id AS newer_id, older.id AS older_id,
               newer.claim_ts AS newer_ts, older.claim_ts AS older_ts
        ORDER BY newer.id
        LIMIT 25
        """,
    ),
    (
        "4_disagreement_set",
        """
        MATCH (c:Claim)-[:CONTRADICTS]-(other:Claim)
        OPTIONAL MATCH (other)-[:SUPPORTED_BY]->(a:Artifact)
        RETURN c.id AS seed_claim, other.id AS neighbor_claim,
               collect(DISTINCT a.id) AS neighbor_artifacts
        ORDER BY c.id, other.id
        LIMIT 25
        """,
    ),
    (
        "5_competitors_at_locus",
        """
        MATCH (a:Artifact)-[:CAPTURED_AT]->(place)
        MATCH (c:Claim)-[:SUPPORTED_BY]->(a)
        OPTIONAL MATCH (c)-[:CONTRADICTS|REVISES]-(rival:Claim)
        RETURN place.id AS place_id, c.id AS claim_id,
               collect(DISTINCT rival.id) AS rivals
        ORDER BY place.id, c.id
        LIMIT 25
        """,
    ),
    (
        "6_person_org",
        """
        MATCH (p:Person)-[:CONNECTED_TO]->(o)
        OPTIONAL MATCH (p)-[:APPEARS_IN]->(e:Episode)<-[:APPEARS_IN]-(other:Person)
        WHERE other.id <> p.id
        RETURN p.id AS person_id, o.id AS org_id,
               collect(DISTINCT other.id)[0..10] AS co_appear_persons
        ORDER BY p.id, o.id
        LIMIT 25
        """,
    ),
    (
        "7_llm_retrieval_spine",
        """
        MATCH (c:Claim)-[:SUPPORTED_BY]->(a:Artifact)-[:APPEARS_IN]->(e:Episode)
        OPTIONAL MATCH (c)-[:CONTRADICTS|REVISES|QUALIFIES]-(comp:Claim)
        RETURN c.id AS seed_claim, a.id AS artifact_id, e.episode_num AS episode_num,
               c.claim_ts AS claim_ts,
               collect(DISTINCT comp.id) AS competitors
        ORDER BY c.id
        LIMIT 25
        """,
    ),
]


def run_smoke(uri: str, user: str, password: str) -> int:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("ERROR: neo4j driver not installed. Run: pip install neo4j")
        return 2

    print(f"[epistemic-smoke] Connecting to {uri} ...")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
    except Exception as e:
        print(f"[epistemic-smoke] SKIPPED: cannot connect to staging: {e}")
        print(
            f"[epistemic-smoke] Expected staging bolt://127.0.0.1:{STAGING_BOLT_PORT}. "
            "Do not start openclaw-neo4j / bare 7687 / write to prod."
        )
        return 3

    failures = 0
    with driver.session() as session:
        # Edge presence counts (informational)
        count_q = """
        UNWIND $rels AS rel
        CALL {
          WITH rel
          MATCH ()-[r]->()
          WHERE type(r) = rel
          RETURN count(r) AS n
        }
        RETURN rel, n
        """
        rels = [
            "ASSERTS",
            "SUPPORTED_BY",
            "REVISES",
            "CONTRADICTS",
            "MENTIONS",
            "APPEARS_IN",
            "CONNECTED_TO",
            "CAPTURED_AT",
            "SUPPORTS",
            "QUALIFIES",
            "FROM_EPISODE",
        ]
        print("[epistemic-smoke] Edge counts:")
        for rel in rels:
            n = session.run(
                f"MATCH ()-[r:{rel}]->() RETURN count(r) AS n"
            ).single()["n"]
            print(f"  {rel}: {n}")

        print("[epistemic-smoke] §5 query pack:")
        for name, cypher in QUERIES:
            try:
                rows = list(session.run(cypher))
                print(f"  PASS {name}: {len(rows)} row(s)")
                if rows:
                    sample = {k: rows[0][k] for k in rows[0].keys()}
                    print(f"         sample: {sample}")
            except Exception as e:
                failures += 1
                print(f"  FAIL {name}: {e}")

    driver.close()
    if failures:
        print(f"[epistemic-smoke] FAIL ({failures} query error(s))")
        return 1
    print("[epistemic-smoke] PASS (queries executed; empty result sets are allowed)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run design §5 epistemic graph smoke queries on staging Neo4j"
    )
    parser.add_argument(
        "--uri",
        default=os.getenv("NEO4J_URI", STAGING_URI_DEFAULT),
        help=f"Bolt URI (default staging {STAGING_URI_DEFAULT})",
    )
    parser.add_argument("--user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "openclaw"))
    parser.add_argument(
        "--allow-prod-read",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if uri_looks_like_prod(args.uri) and not args.allow_prod_read:
        print(
            f"ERROR: Refusing prod URI {args.uri!r} (host port {PROD_BOLT_PORT}). "
            f"Smoke pack targets staging :{STAGING_BOLT_PORT} only."
        )
        return 2

    return run_smoke(args.uri, args.user, args.password)


if __name__ == "__main__":
    sys.exit(main())
