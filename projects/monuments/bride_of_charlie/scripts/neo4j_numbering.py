"""
Neo4j Cross-Episode Numbering Helper
Provides robust ID management and continuity validation.

Usage:
    from scripts.neo4j_numbering import NumberingManager
    
    manager = NumberingManager()
    next_ids = manager.get_next_ids()
    manager.validate_references(episode_num=3)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")


class NumberingManager:
    """Manages cross-episode numbering with Neo4j."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def close(self):
        self.driver.close()
    
    def get_next_ids(self) -> dict[str, int]:
        """
        Get next available IDs for all entity types.
        Returns: {artifact_family: 1005, claim: 1050, person: 15, investigation_target: 1003}
        """
        with self.driver.session() as session:
            result = session.run("""
                OPTIONAL MATCH (af:ArtifactFamily)
                WITH max(toInteger(substring(af.id, 2))) AS max_artifact
                OPTIONAL MATCH (c:Claim)
                WITH max_artifact, max(toInteger(substring(c.id, 2))) AS max_claim
                OPTIONAL MATCH (p:Person)
                WITH max_artifact, max_claim, 
                     max(toInteger(substring(p.id, 2))) AS max_person
                OPTIONAL MATCH (it)
                WHERE it:InvestigationTarget OR it:Topic OR it:Organization OR it:Place
                WITH max_artifact, max_claim, max_person,
                     max(toInteger(substring(it.id, 2))) AS max_target
                RETURN coalesce(max_artifact, 999) + 1 AS artifact_family,
                       coalesce(max_claim, 999) + 1 AS claim,
                       coalesce(max_person, 0) + 1 AS person,
                       coalesce(max_target, 999) + 1 AS investigation_target
            """)
            
            record = result.single()
            return dict(record) if record else {
                "artifact_family": 1000,
                "claim": 1000,
                "person": 1,
                "investigation_target": 1000
            }
    
    def validate_episode_sequence(self, episode_num: int) -> list[str]:
        """
        Check if all previous episodes exist.
        Returns list of missing episode numbers.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                WITH collect(e.episode_num) AS existing
                UNWIND range(1, $episode_num - 1) AS expected
                WHERE NOT expected IN existing
                RETURN expected AS missing
                ORDER BY expected
            """, episode_num=episode_num)
            
            return [record["missing"] for record in result]
    
    def validate_node_references(self, episode_num: int) -> dict[str, list[str]]:
        """
        Validate all node references in an episode.
        Returns: {missing_nodes: [...], missing_artifacts: [...]}
        """
        with self.driver.session() as session:
            # Check for missing node references
            missing_nodes = session.run("""
                MATCH (e:Episode {episode_num: $episode_num})
                MATCH (c:Claim)-[:FROM_EPISODE]->(e)
                WHERE c.related_nodes IS NOT NULL
                UNWIND split(c.related_nodes, ',') AS node_ref
                WITH trim(node_ref) AS node_id
                WHERE node_id <> '' 
                  AND node_id STARTS WITH 'N-'
                  AND NOT EXISTS {
                    MATCH (n) WHERE n.id = node_id 
                      AND (n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget)
                }
                RETURN DISTINCT node_id
            """, episode_num=episode_num)
            
            # Check for missing artifact references
            missing_artifacts = session.run("""
                MATCH (e:Episode {episode_num: $episode_num})
                MATCH (c:Claim)-[:FROM_EPISODE]->(e)
                WHERE c.anchored_artifacts IS NOT NULL
                UNWIND split(c.anchored_artifacts, ',') AS artifact_ref
                WITH trim(artifact_ref) AS artifact_id
                WHERE artifact_id <> '' 
                  AND artifact_id STARTS WITH 'A-'
                  AND NOT EXISTS {
                    MATCH (a:Artifact {id: artifact_id})
                }
                RETURN DISTINCT artifact_id
            """, episode_num=episode_num)
            
            return {
                "missing_nodes": [r["node_id"] for r in missing_nodes],
                "missing_artifacts": [r["artifact_id"] for r in missing_artifacts]
            }
    
    def get_node_reuse_stats(self) -> list[dict]:
        """
        Show which nodes are reused across episodes.
        Returns list of {id, name, episodes, count}
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)-[:APPEARS_IN]->(e:Episode)
                WHERE n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget
                WITH n, collect(DISTINCT e.episode_num) AS episodes
                RETURN n.id AS id,
                       n.canonical_name AS name,
                       episodes,
                       size(episodes) AS episode_count,
                       labels(n)[0] AS node_type
                ORDER BY episode_count DESC, n.id
            """)
            
            return [dict(record) for record in result]
    
    def get_id_ranges_by_episode(self) -> list[dict]:
        """
        Show ID ranges introduced in each episode.
        Returns list of {episode, artifact_range, claim_range, new_nodes}
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                OPTIONAL MATCH (e)-[:CONTAINS_FAMILY]->(af:ArtifactFamily)
                OPTIONAL MATCH (c:Claim)-[:FROM_EPISODE]->(e)
                OPTIONAL MATCH (n)-[:APPEARS_IN]->(e)
                WHERE n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget
                WITH e,
                     collect(DISTINCT af.id) AS artifacts,
                     collect(DISTINCT c.id) AS claims,
                     collect(DISTINCT n.id) AS nodes
                RETURN e.episode_num AS episode,
                       artifacts,
                       claims,
                       nodes
                ORDER BY e.episode_num
            """)
            
            episodes = []
            for record in result:
                artifacts = sorted(record["artifacts"]) if record["artifacts"] else []
                claims = sorted(record["claims"]) if record["claims"] else []
                nodes = sorted(record["nodes"]) if record["nodes"] else []
                
                episodes.append({
                    "episode": record["episode"],
                    "artifact_range": f"{artifacts[0]} to {artifacts[-1]}" if artifacts else "none",
                    "artifact_count": len(artifacts),
                    "claim_range": f"{claims[0]} to {claims[-1]}" if claims else "none",
                    "claim_count": len(claims),
                    "node_count": len(nodes),
                    "nodes": nodes
                })
            
            return episodes
    
    def detect_potential_duplicates(self, episode_num: int) -> list[dict]:
        """
        Check if any nodes in this episode might be duplicates of existing nodes.
        Returns list of potential duplicates.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode {episode_num: $episode_num})
                MATCH (new_node)-[:APPEARS_IN]->(e)
                WHERE new_node:Person OR new_node:Topic OR new_node:Organization OR new_node:Place OR new_node:InvestigationTarget
                MATCH (existing)
                WHERE (existing:Person OR existing:Topic OR existing:Organization OR existing:Place OR existing:InvestigationTarget)
                  AND existing.id <> new_node.id
                  AND NOT (existing)-[:APPEARS_IN]->(e)
                WITH new_node, existing,
                     apoc.text.levenshteinDistance(
                         new_node.canonical_name, 
                         existing.canonical_name
                     ) AS distance
                WHERE distance <= 3
                RETURN new_node.id AS new_id,
                       new_node.canonical_name AS new_name,
                       existing.id AS existing_id,
                       existing.canonical_name AS existing_name,
                       distance
                ORDER BY distance
            """, episode_num=episode_num)
            
            return [dict(record) for record in result]
    
    def generate_numbering_report(self, episode_num: int) -> str:
        """Generate a comprehensive numbering report for an episode."""
        report = []
        report.append(f"=== Numbering Report: Episode {episode_num} ===\n")
        
        # Check episode sequence
        missing = self.validate_episode_sequence(episode_num)
        if missing:
            report.append(f"⚠️  WARNING: Missing episodes: {missing}")
            report.append("   Cannot generate episode {episode_num} until previous episodes exist.\n")
            return "\n".join(report)
        else:
            report.append("✓ Episode sequence: OK\n")
        
        # Get next IDs
        next_ids = self.get_next_ids()
        report.append("Next Available IDs:")
        report.append(f"  Artifact Family: A-{next_ids['artifact_family']}")
        report.append(f"  Claim: C-{next_ids['claim']}")
        report.append(f"  Person: N-{next_ids['person']}")
        report.append(f"  Investigation Target: N-{next_ids['investigation_target']}\n")
        
        # Show ID ranges by episode
        report.append("ID Ranges by Episode:")
        for ep in self.get_id_ranges_by_episode():
            report.append(f"  Episode {ep['episode']}:")
            report.append(f"    Artifacts: {ep['artifact_range']} ({ep['artifact_count']} families)")
            report.append(f"    Claims: {ep['claim_range']} ({ep['claim_count']} claims)")
            report.append(f"    Nodes: {ep['node_count']} introduced")
        report.append("")
        
        # Show node reuse
        report.append("Node Reuse (Top 10):")
        for node in self.get_node_reuse_stats()[:10]:
            episodes_str = ",".join(map(str, node["episodes"]))
            report.append(f"  {node['id']} {node['name']}: {node['episode_count']} episodes [{episodes_str}]")
        
        return "\n".join(report)


def main():
    """CLI for numbering management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Neo4j cross-episode numbering helper")
    parser.add_argument("command", choices=["next", "validate", "report", "reuse"], 
                       help="Command to run")
    parser.add_argument("--episode", type=int, help="Episode number")
    args = parser.parse_args()
    
    manager = NumberingManager()
    
    try:
        if args.command == "next":
            next_ids = manager.get_next_ids()
            print("Next Available IDs:")
            print(f"  Artifact Family: A-{next_ids['artifact_family']}")
            print(f"  Claim: C-{next_ids['claim']}")
            print(f"  Person: N-{next_ids['person']}")
            print(f"  Investigation Target: N-{next_ids['investigation_target']}")
        
        elif args.command == "validate":
            if not args.episode:
                print("ERROR: --episode required for validate command")
                sys.exit(1)
            
            missing = manager.validate_episode_sequence(args.episode)
            if missing:
                print(f"⚠️  Missing episodes: {missing}")
                sys.exit(1)
            
            refs = manager.validate_node_references(args.episode)
            if refs["missing_nodes"] or refs["missing_artifacts"]:
                print("⚠️  Invalid references found:")
                if refs["missing_nodes"]:
                    print(f"  Missing nodes: {refs['missing_nodes']}")
                if refs["missing_artifacts"]:
                    print(f"  Missing artifacts: {refs['missing_artifacts']}")
                sys.exit(1)
            
            print(f"✓ Episode {args.episode}: All references valid")
        
        elif args.command == "report":
            if not args.episode:
                print("ERROR: --episode required for report command")
                sys.exit(1)
            
            print(manager.generate_numbering_report(args.episode))
        
        elif args.command == "reuse":
            print("Node Reuse Statistics:")
            for node in manager.get_node_reuse_stats():
                episodes_str = ",".join(map(str, node["episodes"]))
                print(f"  {node['id']} {node['name']}: {node['episode_count']} episodes [{episodes_str}]")
    
    finally:
        manager.close()


if __name__ == "__main__":
    main()
