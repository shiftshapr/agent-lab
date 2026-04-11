"""
Neo4j Quality Metrics Tracker
Tracks protocol compliance and quality improvement over time.

Usage:
    # Show quality metrics
    python scripts/neo4j_quality.py

    # Export report
    python scripts/neo4j_quality.py --output quality_report.md
    
    # Compare episodes
    python scripts/neo4j_quality.py --compare 1 7
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")


class QualityMetrics:
    """Tracks quality metrics across episodes."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def close(self):
        self.driver.close()
    
    # -------------------------------------------------------------------------
    # Metrics Queries
    # -------------------------------------------------------------------------
    
    def protocol_compliance_by_episode(self) -> list[dict]:
        """Calculate protocol compliance score for each episode."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                
                // Count total claims
                OPTIONAL MATCH (c:Claim)-[:FROM_EPISODE]->(e)
                WITH e, count(c) AS total_claims
                
                // Count substantiated claims without artifact anchor
                OPTIONAL MATCH (c2:Claim)-[:FROM_EPISODE]->(e)
                WHERE coalesce(c2.substantiated, true) = true
                AND NOT (:Artifact)-[:ANCHORS]->(c2)
                WITH e, total_claims, count(c2) AS claims_without_anchors
                
                // Count claims without INVOLVES or MENTIONS_TOPIC
                OPTIONAL MATCH (c3:Claim)-[:FROM_EPISODE]->(e)
                WHERE NOT (c3)-[:INVOLVES]->()
                AND NOT (c3)-[:MENTIONS_TOPIC]->()
                WITH e, total_claims, claims_without_anchors, count(c3) AS claims_without_nodes
                
                // Count artifacts without relationships
                OPTIONAL MATCH (e)-[:CONTAINS_FAMILY]->()-[:HAS_ARTIFACT]->(a:Artifact)
                WITH e, total_claims, claims_without_anchors, claims_without_nodes,
                     count(a) AS total_artifacts
                
                OPTIONAL MATCH (e)-[:CONTAINS_FAMILY]->()-[:HAS_ARTIFACT]->(a2:Artifact)
                WHERE NOT (a2)-[:ANCHORS]->() AND NOT (a2)-[:INVOLVES]->()
                WITH e, total_claims, claims_without_anchors, claims_without_nodes,
                     total_artifacts, count(a2) AS artifacts_without_rels
                
                RETURN e.episode_num AS episode,
                       total_claims,
                       claims_without_anchors,
                       claims_without_nodes,
                       total_artifacts,
                       artifacts_without_rels,
                       CASE 
                         WHEN total_claims = 0 THEN 0
                         ELSE round(100.0 * (total_claims - claims_without_anchors - claims_without_nodes) / total_claims, 2)
                       END AS compliance_score
                ORDER BY e.episode_num
            """)
            
            return [dict(record) for record in result]
    
    def evidence_density_by_episode(self) -> list[dict]:
        """Calculate evidence density (artifacts per claim)."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                OPTIONAL MATCH (c:Claim)-[:FROM_EPISODE]->(e)
                OPTIONAL MATCH (a:Artifact)-[:ANCHORS]->(c)
                WITH e, count(DISTINCT c) AS claims, count(a) AS artifacts
                RETURN e.episode_num AS episode,
                       claims,
                       artifacts,
                       CASE 
                         WHEN claims = 0 THEN 0
                         ELSE round(1.0 * artifacts / claims, 2)
                       END AS artifacts_per_claim
                ORDER BY e.episode_num
            """)
            
            return [dict(record) for record in result]
    
    def node_reuse_rate(self) -> list[dict]:
        """Calculate how many nodes are reused vs new in each episode."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                OPTIONAL MATCH (n)-[:APPEARS_IN]->(e)
                WHERE n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget
                WITH e, collect(DISTINCT n) AS nodes_in_episode
                
                UNWIND nodes_in_episode AS node
                OPTIONAL MATCH (node)-[:APPEARS_IN]->(prev_e:Episode)
                WHERE prev_e.episode_num < e.episode_num
                WITH e, node, count(prev_e) AS previous_appearances
                
                WITH e,
                     count(CASE WHEN previous_appearances = 0 THEN 1 END) AS new_nodes,
                     count(CASE WHEN previous_appearances > 0 THEN 1 END) AS reused_nodes
                
                RETURN e.episode_num AS episode,
                       new_nodes,
                       reused_nodes,
                       CASE 
                         WHEN (new_nodes + reused_nodes) = 0 THEN 0
                         ELSE round(100.0 * reused_nodes / (new_nodes + reused_nodes), 2)
                       END AS reuse_rate
                ORDER BY e.episode_num
            """)
            
            return [dict(record) for record in result]
    
    def overall_statistics(self) -> dict:
        """Get overall statistics across all episodes."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                WITH count(e) AS episodes
                
                MATCH (af:ArtifactFamily)
                WITH episodes, count(af) AS families
                
                MATCH (a:Artifact)
                WITH episodes, families, count(a) AS artifacts
                
                MATCH (c:Claim)
                WITH episodes, families, artifacts, count(c) AS claims
                
                MATCH (p:Person)
                WITH episodes, families, artifacts, claims, count(p) AS people
                
                MATCH (it)
                WHERE it:InvestigationTarget OR it:Topic OR it:Organization OR it:Place
                WITH episodes, families, artifacts, claims, people, count(it) AS targets
                
                OPTIONAL MATCH ()-[r:ANCHORS]->()
                WITH episodes, families, artifacts, claims, people, targets, count(r) AS anchors
                
                OPTIONAL MATCH ()-[r2:INVOLVES]->()
                WITH episodes, families, artifacts, claims, people, targets, anchors, count(r2) AS involves
                
                RETURN episodes, families, artifacts, claims, people, targets, anchors, involves
            """)
            
            record = result.single()
            return dict(record) if record else {}
    
    # -------------------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------------------
    
    def generate_quality_report(self) -> str:
        """Generate comprehensive quality report."""
        report = ["# Quality Metrics Report\n"]
        
        # Overall stats
        stats = self.overall_statistics()
        report.append("## Overall Statistics\n")
        report.append(f"- Episodes: {stats.get('episodes', 0)}")
        report.append(f"- Artifact Families: {stats.get('families', 0)}")
        report.append(f"- Artifacts: {stats.get('artifacts', 0)}")
        report.append(f"- Claims: {stats.get('claims', 0)}")
        report.append(f"- People: {stats.get('people', 0)}")
        report.append(f"- Investigation Targets: {stats.get('targets', 0)}")
        report.append(f"- ANCHORS relationships: {stats.get('anchors', 0)}")
        report.append(f"- INVOLVES relationships: {stats.get('involves', 0)}\n")
        
        # Protocol compliance
        compliance = self.protocol_compliance_by_episode()
        report.append("## Protocol Compliance by Episode\n")
        report.append("| Episode | Claims | Missing Anchors | Missing Nodes | Compliance Score |")
        report.append("|---------|--------|-----------------|---------------|------------------|")
        
        for item in compliance:
            report.append(
                f"| {item['episode']} | {item['total_claims']} | "
                f"{item['claims_without_anchors']} | {item['claims_without_nodes']} | "
                f"{item['compliance_score']}% |"
            )
        
        report.append("")
        
        # Evidence density
        density = self.evidence_density_by_episode()
        report.append("## Evidence Density\n")
        report.append("| Episode | Claims | Artifacts | Artifacts per Claim |")
        report.append("|---------|--------|-----------|---------------------|")
        
        for item in density:
            report.append(
                f"| {item['episode']} | {item['claims']} | "
                f"{item['artifacts']} | {item['artifacts_per_claim']} |"
            )
        
        report.append("")
        
        # Node reuse
        reuse = self.node_reuse_rate()
        report.append("## Node Reuse Rate\n")
        report.append("| Episode | New Nodes | Reused Nodes | Reuse Rate |")
        report.append("|---------|-----------|--------------|------------|")
        
        for item in reuse:
            report.append(
                f"| {item['episode']} | {item['new_nodes']} | "
                f"{item['reused_nodes']} | {item['reuse_rate']}% |"
            )
        
        report.append("")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Quality metrics tracker")
    parser.add_argument("--output", type=Path, help="Output file (markdown)")
    parser.add_argument("--compare", nargs=2, type=int, metavar=("EP1", "EP2"), 
                       help="Compare two episodes")
    args = parser.parse_args()
    
    print(f"[quality] Connecting to {NEO4J_URI}...")
    try:
        metrics = QualityMetrics()
    except Exception as e:
        print(f"ERROR: Could not connect to Neo4j: {e}")
        sys.exit(1)
    
    try:
        report = metrics.generate_quality_report()
        
        if args.output:
            args.output.write_text(report, encoding="utf-8")
            print(f"✓ Report written to {args.output}")
        else:
            print(report)
    
    finally:
        metrics.close()


if __name__ == "__main__":
    main()
