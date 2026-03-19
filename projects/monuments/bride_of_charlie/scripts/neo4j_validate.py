"""
Neo4j Validation Script for OpenClaw Protocol Integrity
Runs Cypher queries to verify the investigative graph follows protocol rules.

Usage:
    python scripts/neo4j_validate.py

Environment:
    NEO4J_URI (default: bolt://localhost:7687)
    NEO4J_USER (default: neo4j)
    NEO4J_PASSWORD (default: openclaw)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")

# ---------------------------------------------------------------------------
# Validation queries
# ---------------------------------------------------------------------------

VALIDATION_QUERIES = {
    "claims_without_artifact_anchor": {
        "description": "Claims with no artifact anchor (violates Artifact Anchor Test)",
        "query": """
            MATCH (c:Claim)
            WHERE NOT (:Artifact)-[:ANCHORS]->(c)
            RETURN c.id AS claim_id, c.label AS claim_label, c.episode_num AS episode
            ORDER BY c.id
        """,
        "severity": "CRITICAL",
    },
    "artifacts_without_relationships": {
        "description": "Artifacts with no related claims or nodes (violates Cross-Reference Rule)",
        "query": """
            MATCH (a:Artifact)
            WHERE NOT (a)-[:ANCHORS]->() AND NOT (a)-[:INVOLVES]->()
            RETURN a.id AS artifact_id, a.description AS description, a.episode_num AS episode
            ORDER BY a.id
        """,
        "severity": "WARNING",
    },
    "nodes_without_evidence": {
        "description": "Nodes with zero evidence (no artifacts or claims reference them)",
        "query": """
            MATCH (n)
            WHERE (n:Person OR n:InvestigationTarget)
            AND NOT ()-[:INVOLVES]->(n)
            AND NOT ()-[:ANCHORS]->(n)
            RETURN n.id AS node_id, n.name AS name, labels(n)[0] AS node_type
            ORDER BY n.id
        """,
        "severity": "WARNING",
    },
    "claims_without_nodes": {
        "description": "Claims with no related nodes (violates protocol requirement)",
        "query": """
            MATCH (c:Claim)
            WHERE NOT (c)-[:INVOLVES]->()
            RETURN c.id AS claim_id, c.label AS claim_label, c.episode_num AS episode
            ORDER BY c.id
        """,
        "severity": "CRITICAL",
    },
    "broken_artifact_references": {
        "description": "Claims referencing non-existent artifacts",
        "query": """
            MATCH (c:Claim)
            WHERE c.anchored_artifacts IS NOT NULL
            UNWIND split(c.anchored_artifacts, ',') AS artifact_ref
            WITH c, trim(artifact_ref) AS artifact_id
            WHERE artifact_id <> '' AND NOT EXISTS {
                MATCH (a:Artifact {id: artifact_id})
            }
            RETURN c.id AS claim_id, artifact_id AS missing_artifact, c.episode_num AS episode
            ORDER BY c.id
        """,
        "severity": "CRITICAL",
    },
    "broken_node_references": {
        "description": "Claims or artifacts referencing non-existent nodes",
        "query": """
            MATCH (c:Claim)
            WHERE c.related_nodes IS NOT NULL
            UNWIND split(c.related_nodes, ',') AS node_ref
            WITH c, trim(node_ref) AS node_id
            WHERE node_id <> '' AND NOT EXISTS {
                MATCH (n) WHERE n.id = node_id AND (n:Person OR n:InvestigationTarget)
            }
            RETURN c.id AS claim_id, node_id AS missing_node, c.episode_num AS episode
            ORDER BY c.id
        """,
        "severity": "CRITICAL",
    },
}

# ---------------------------------------------------------------------------
# Statistics queries
# ---------------------------------------------------------------------------

STATS_QUERIES = {
    "total_episodes": "MATCH (e:Episode) RETURN count(e) AS count",
    "total_artifact_families": "MATCH (af:ArtifactFamily) RETURN count(af) AS count",
    "total_artifacts": "MATCH (a:Artifact) RETURN count(a) AS count",
    "total_claims": "MATCH (c:Claim) RETURN count(c) AS count",
    "total_people": "MATCH (p:Person) RETURN count(p) AS count",
    "total_investigation_targets": "MATCH (it:InvestigationTarget) RETURN count(it) AS count",
    "total_anchors_relationships": "MATCH ()-[r:ANCHORS]->() RETURN count(r) AS count",
    "total_involves_relationships": "MATCH ()-[r:INVOLVES]->() RETURN count(r) AS count",
}

# ---------------------------------------------------------------------------
# ID range queries
# ---------------------------------------------------------------------------

ID_RANGE_QUERIES = {
    "artifact_families": "MATCH (af:ArtifactFamily) RETURN af.id AS id ORDER BY af.id",
    "claims": "MATCH (c:Claim) RETURN c.id AS id ORDER BY c.id",
    "people": "MATCH (p:Person) RETURN p.id AS id ORDER BY p.id",
    "investigation_targets": "MATCH (it:InvestigationTarget) RETURN it.id AS id ORDER BY it.id",
}

# ---------------------------------------------------------------------------
# Validation runner
# ---------------------------------------------------------------------------

def run_validation(driver) -> bool:
    """Run all validation queries and return True if all pass."""
    all_passed = True
    
    print("\n" + "=" * 80)
    print("OPENCLAW PROTOCOL INTEGRITY VALIDATION")
    print("=" * 80)
    
    # Run statistics
    print("\n--- GRAPH STATISTICS ---\n")
    with driver.session() as session:
        for name, query in STATS_QUERIES.items():
            result = session.run(query)
            record = result.single()
            count = record["count"] if record else 0
            print(f"  {name.replace('_', ' ').title()}: {count}")
    
    # Run ID range checks
    print("\n--- ID RANGES ---\n")
    with driver.session() as session:
        for name, query in ID_RANGE_QUERIES.items():
            results = session.run(query)
            ids = [record["id"] for record in results]
            if ids:
                print(f"  {name.replace('_', ' ').title()}: {ids[0]} to {ids[-1]} ({len(ids)} total)")
            else:
                print(f"  {name.replace('_', ' ').title()}: (none)")
    
    # Run validation queries
    print("\n--- INTEGRITY CHECKS ---\n")
    
    for check_name, check_config in VALIDATION_QUERIES.items():
        description = check_config["description"]
        query = check_config["query"]
        severity = check_config["severity"]
        
        with driver.session() as session:
            results = session.run(query)
            records = list(results)
        
        if records:
            all_passed = False
            print(f"  [{severity}] {description}")
            print(f"           Found {len(records)} issue(s):")
            for record in records[:10]:  # Limit to first 10
                print(f"           - {dict(record)}")
            if len(records) > 10:
                print(f"           ... and {len(records) - 10} more")
            print()
        else:
            print(f"  [PASS] {description}")
    
    print("\n" + "=" * 80)
    if all_passed:
        print("RESULT: ALL CHECKS PASSED ✓")
    else:
        print("RESULT: INTEGRITY ISSUES FOUND ✗")
    print("=" * 80 + "\n")
    
    return all_passed


def compute_investigative_pressure(driver):
    """Compute and display investigative pressure for nodes."""
    print("\n--- INVESTIGATIVE PRESSURE (Top 10) ---\n")
    
    query = """
        MATCH (n)
        WHERE n:Person OR n:InvestigationTarget
        OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(n)
        OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(n)
        OPTIONAL MATCH (n)-[:APPEARS_IN]->(e:Episode)
        WITH n, 
             count(DISTINCT a) AS artifact_count,
             count(DISTINCT c) AS claim_count,
             count(DISTINCT e) AS episode_count
        WITH n, artifact_count, claim_count, episode_count,
             (artifact_count + claim_count * 2 + episode_count) AS pressure_score
        RETURN n.id AS node_id, 
               n.name AS name, 
               labels(n)[0] AS node_type,
               artifact_count AS artifacts,
               claim_count AS claims,
               episode_count AS episodes,
               pressure_score
        ORDER BY pressure_score DESC
        LIMIT 10
    """
    
    with driver.session() as session:
        results = session.run(query)
        records = list(results)
    
    if records:
        for record in records:
            print(f"  {record['node_id']} ({record['name']})")
            print(f"    Type: {record['node_type']}")
            print(f"    Artifacts: {record['artifacts']}, Claims: {record['claims']}, Episodes: {record['episodes']}")
            print(f"    Pressure Score: {record['pressure_score']}")
            print()
    else:
        print("  No nodes found.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"[neo4j-validate] Connecting to {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: Could not connect to Neo4j: {e}")
        print("Make sure Neo4j is running: docker compose up -d")
        sys.exit(1)
    
    all_passed = run_validation(driver)
    compute_investigative_pressure(driver)
    
    driver.close()
    
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
