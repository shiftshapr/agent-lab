"""
Neo4j Context Injection for Episode Analysis
Provides cross-episode context to help LLM reuse nodes and maintain continuity.
"""

from __future__ import annotations

import os
from typing import Any

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")


def get_episode_context(episode_num: int) -> str:
    """
    Get cross-episode context for the LLM.
    Returns markdown string with recurring entities and their IDs.
    """
    if not NEO4J_URI or not GraphDatabase:
        return ""
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception:
        return ""
    
    context_parts = []
    
    with driver.session() as session:
        # Get recurring people (appeared in 2+ previous episodes)
        result = session.run("""
            MATCH (p:Person)-[:APPEARS_IN]->(e:Episode)
            WHERE e.episode_num < $episode_num
            WITH p, collect(DISTINCT e.episode_num) AS episodes
            WHERE size(episodes) >= 2
            RETURN p.id AS id,
                   p.canonical_name AS name,
                   p.aliases AS aliases,
                   episodes,
                   size(episodes) AS appearance_count
            ORDER BY appearance_count DESC, p.id
            LIMIT 15
        """, episode_num=episode_num)
        
        recurring_people = list(result)
        
        if recurring_people:
            context_parts.append("RECURRING PEOPLE (reuse these IDs if they appear in this episode):")
            for person in recurring_people:
                aliases_str = f" (also known as: {', '.join(person['aliases'])})" if person['aliases'] else ""
                episodes_str = ", ".join(map(str, person['episodes']))
                context_parts.append(
                    f"- {person['id']}: {person['name']}{aliases_str} "
                    f"[appeared in episodes {episodes_str}]"
                )
        
        # Get recurring investigation targets
        result = session.run("""
            MATCH (it:InvestigationTarget)-[:APPEARS_IN]->(e:Episode)
            WHERE e.episode_num < $episode_num
            WITH it, collect(DISTINCT e.episode_num) AS episodes
            WHERE size(episodes) >= 1
            RETURN it.id AS id,
                   it.canonical_name AS name,
                   episodes,
                   size(episodes) AS appearance_count
            ORDER BY appearance_count DESC, it.id
            LIMIT 10
        """, episode_num=episode_num)
        
        recurring_targets = list(result)
        
        if recurring_targets:
            context_parts.append("\nRECURRING INVESTIGATION TARGETS (reuse these IDs if relevant):")
            for target in recurring_targets:
                episodes_str = ", ".join(map(str, target['episodes']))
                context_parts.append(
                    f"- {target['id']}: {target['name']} "
                    f"[appeared in episodes {episodes_str}]"
                )
        
        # Get name corrections
        result = session.run("""
            MATCH (nc:NameCorrection)
            WHERE nc.confidence IN ['high', 'medium']
            RETURN nc.incorrect AS incorrect,
                   nc.correct AS correct
            ORDER BY nc.incorrect
            LIMIT 20
        """)
        
        corrections = list(result)
        
        if corrections:
            context_parts.append("\nVERIFIED NAME SPELLINGS (use these spellings):")
            for corr in corrections:
                context_parts.append(f"- Use '{corr['correct']}' not '{corr['incorrect']}'")
    
    driver.close()
    
    if not context_parts:
        return ""
    
    return "\n".join(context_parts)


def validate_references_realtime(
    artifact_ids: list[str],
    claim_ids: list[str],
    node_ids: list[str]
) -> dict[str, list[str]]:
    """
    Validate that referenced IDs exist in Neo4j.
    Returns: {missing_artifacts: [...], missing_claims: [...], missing_nodes: [...]}
    """
    if not NEO4J_URI or not GraphDatabase:
        return {"missing_artifacts": [], "missing_claims": [], "missing_nodes": []}
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception:
        return {"missing_artifacts": [], "missing_claims": [], "missing_nodes": []}
    
    missing = {"missing_artifacts": [], "missing_claims": [], "missing_nodes": []}
    
    with driver.session() as session:
        # Check artifacts
        for artifact_id in artifact_ids:
            result = session.run(
                "MATCH (a:Artifact {id: $id}) RETURN count(a) AS count",
                id=artifact_id
            )
            if result.single()["count"] == 0:
                missing["missing_artifacts"].append(artifact_id)
        
        # Check claims
        for claim_id in claim_ids:
            result = session.run(
                "MATCH (c:Claim {id: $id}) RETURN count(c) AS count",
                id=claim_id
            )
            if result.single()["count"] == 0:
                missing["missing_claims"].append(claim_id)
        
        # Check nodes
        for node_id in node_ids:
            result = session.run(
                "MATCH (n) WHERE n.id = $id AND (n:Person OR n:InvestigationTarget) "
                "RETURN count(n) AS count",
                id=node_id
            )
            if result.single()["count"] == 0:
                missing["missing_nodes"].append(node_id)
    
    driver.close()
    return missing


def suggest_node_for_name(name: str) -> dict | None:
    """
    Check if a person with this name (or similar) already exists.
    Returns: {id, canonical_name, match_type} or None
    """
    if not NEO4J_URI or not GraphDatabase:
        return None
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception:
        return None
    
    with driver.session() as session:
        # Exact match
        result = session.run("""
            MATCH (n)
            WHERE (n:Person OR n:InvestigationTarget)
              AND (n.canonical_name = $name OR $name IN n.aliases)
            RETURN n.id AS id, n.canonical_name AS name, 'exact' AS match_type
            LIMIT 1
        """, name=name)
        
        record = result.single()
        if record:
            driver.close()
            return dict(record)
        
        # Fuzzy match
        result = session.run("""
            MATCH (n)
            WHERE (n:Person OR n:InvestigationTarget)
            WITH n, apoc.text.levenshteinDistance(n.canonical_name, $name) AS distance
            WHERE distance <= 3
            RETURN n.id AS id, n.canonical_name AS name, 'fuzzy' AS match_type, distance
            ORDER BY distance
            LIMIT 1
        """, name=name)
        
        record = result.single()
        driver.close()
        
        return dict(record) if record else None
