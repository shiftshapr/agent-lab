"""
Neo4j Pattern Detection for Cross-Episode Analysis
Auto-generates investigative insights from the graph.

Usage:
    # Run all pattern detection
    python scripts/neo4j_patterns.py all
    
    # Specific analyses
    python scripts/neo4j_patterns.py co-occurrence
    python scripts/neo4j_patterns.py contradictions
    python scripts/neo4j_patterns.py timeline --person N-2
    python scripts/neo4j_patterns.py network
    
    # Export report
    python scripts/neo4j_patterns.py all --output patterns_report.md
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

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")


class PatternDetector:
    """Detects patterns across episodes using Neo4j."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def close(self):
        self.driver.close()
    
    # -------------------------------------------------------------------------
    # Pattern Detection Queries
    # -------------------------------------------------------------------------
    
    def co_occurrence_analysis(self) -> list[dict]:
        """Find people who appear together frequently."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p1:Person)-[:APPEARS_IN]->(e:Episode)<-[:APPEARS_IN]-(p2:Person)
                WHERE p1.id < p2.id
                WITH p1, p2, collect(DISTINCT e.episode_num) AS episodes
                WHERE size(episodes) >= 2
                RETURN p1.id AS person1_id,
                       p1.canonical_name AS person1,
                       p2.id AS person2_id,
                       p2.canonical_name AS person2,
                       size(episodes) AS episodes_together,
                       episodes
                ORDER BY episodes_together DESC, p1.id
            """)
            
            return [dict(record) for record in result]
    
    def claim_clustering(self) -> list[dict]:
        """Group claims by investigation target."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Claim)-[:INVOLVES]->(it:InvestigationTarget)
                WITH it, collect(c) AS claims
                WHERE size(claims) >= 2
                RETURN it.id AS target_id,
                       it.canonical_name AS target,
                       size(claims) AS claim_count,
                       [c IN claims | {id: c.id, label: c.label, episode: c.episode_num}] AS claims
                ORDER BY claim_count DESC
            """)
            
            return [dict(record) for record in result]
    
    def evidence_accumulation(self, person_id: str) -> list[dict]:
        """Show how evidence builds over episodes for a person."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {id: $id})-[:APPEARS_IN]->(e:Episode)
                WITH p, e
                ORDER BY e.episode_num
                WITH p, collect(e.episode_num) AS all_episodes
                UNWIND all_episodes AS current_episode
                WITH p, current_episode, all_episodes
                WHERE current_episode IN all_episodes
                
                OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(p)
                WHERE a.episode_num <= current_episode
                WITH p, current_episode, count(DISTINCT a) AS cumulative_artifacts
                
                OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(p)
                WHERE c.episode_num <= current_episode
                WITH current_episode, cumulative_artifacts, count(DISTINCT c) AS cumulative_claims
                
                RETURN current_episode AS episode,
                       cumulative_artifacts,
                       cumulative_claims
                ORDER BY episode
            """, id=person_id)
            
            return [dict(record) for record in result]
    
    def find_contradictions(self, topic_keyword: str | None = None) -> list[dict]:
        """Find potentially contradictory claims."""
        with self.driver.session() as session:
            query = """
                MATCH (c1:Claim)-[:INVOLVES]->(n)<-[:INVOLVES]-(c2:Claim)
                WHERE c1.id < c2.id
                  AND c1.claim_text IS NOT NULL
                  AND c2.claim_text IS NOT NULL
            """
            
            if topic_keyword:
                query += """
                  AND (c1.claim_text CONTAINS $keyword OR c1.label CONTAINS $keyword)
                  AND (c2.claim_text CONTAINS $keyword OR c2.label CONTAINS $keyword)
                """
            
            query += """
                WITH c1, c2, n,
                     apoc.text.levenshteinSimilarity(c1.claim_text, c2.claim_text) AS similarity
                WHERE similarity > 0.3 AND similarity < 0.9
                RETURN c1.id AS claim1_id,
                       c1.label AS claim1_label,
                       c1.claim_text AS claim1_text,
                       c1.episode_num AS claim1_episode,
                       c2.id AS claim2_id,
                       c2.label AS claim2_label,
                       c2.claim_text AS claim2_text,
                       c2.episode_num AS claim2_episode,
                       n.canonical_name AS about,
                       round(similarity * 100, 2) AS similarity_pct
                ORDER BY similarity DESC
                LIMIT 20
            """
            
            result = session.run(query, keyword=topic_keyword)
            return [dict(record) for record in result]
    
    def network_centrality(self, limit: int = 10) -> list[dict]:
        """Calculate network centrality (who's most connected)."""
        with self.driver.session() as session:
            # Simple degree centrality (count of relationships)
            result = session.run("""
                MATCH (n)
                WHERE n:Person OR n:InvestigationTarget
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(DISTINCT r) AS degree
                RETURN n.id AS id,
                       n.canonical_name AS name,
                       labels(n)[0] AS node_type,
                       degree
                ORDER BY degree DESC
                LIMIT $limit
            """, limit=limit)
            
            return [dict(record) for record in result]
    
    def episode_summary(self) -> list[dict]:
        """Summarize each episode."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Episode)
                OPTIONAL MATCH (e)-[:CONTAINS_FAMILY]->(af:ArtifactFamily)
                OPTIONAL MATCH (c:Claim)-[:FROM_EPISODE]->(e)
                OPTIONAL MATCH (n)-[:APPEARS_IN]->(e)
                WHERE n:Person OR n:InvestigationTarget
                WITH e,
                     count(DISTINCT af) AS families,
                     count(DISTINCT c) AS claims,
                     count(DISTINCT n) AS nodes
                RETURN e.episode_num AS episode,
                       families,
                       claims,
                       nodes
                ORDER BY e.episode_num
            """)
            
            return [dict(record) for record in result]
    
    # -------------------------------------------------------------------------
    # Formatting
    # -------------------------------------------------------------------------
    
    def format_co_occurrence_report(self, results: list[dict]) -> str:
        """Format co-occurrence analysis as markdown."""
        if not results:
            return "No co-occurrences found.\n"
        
        report = ["# Co-Occurrence Analysis\n"]
        report.append("People who appear together frequently:\n")
        
        for item in results:
            episodes_str = ", ".join(map(str, item['episodes']))
            report.append(f"## {item['person1']} & {item['person2']}")
            report.append(f"- **Episodes together:** {item['episodes_together']} [{episodes_str}]")
            report.append(f"- **IDs:** {item['person1_id']}, {item['person2_id']}\n")
        
        return "\n".join(report)
    
    def format_contradiction_report(self, results: list[dict]) -> str:
        """Format contradictions as markdown."""
        if not results:
            return "No contradictions found.\n"
        
        report = ["# Potential Contradictions\n"]
        
        for item in results:
            report.append(f"## About: {item['about']}")
            report.append(f"**Similarity:** {item['similarity_pct']}%\n")
            report.append(f"### {item['claim1_id']} (Episode {item['claim1_episode']})")
            report.append(f"{item['claim1_text']}\n")
            report.append(f"### {item['claim2_id']} (Episode {item['claim2_episode']})")
            report.append(f"{item['claim2_text']}\n")
            report.append("---\n")
        
        return "\n".join(report)
    
    def format_network_report(self, results: list[dict]) -> str:
        """Format network centrality as markdown."""
        if not results:
            return "No network data found.\n"
        
        report = ["# Network Centrality\n"]
        report.append("Most connected entities:\n")
        
        for item in results:
            report.append(f"- **{item['name']}** ({item['id']}, {item['node_type']}): {item['degree']} connections")
        
        return "\n".join(report)
    
    def format_episode_summary(self, results: list[dict]) -> str:
        """Format episode summary as markdown."""
        report = ["# Episode Summary\n"]
        
        total_families = 0
        total_claims = 0
        total_nodes = 0
        
        for item in results:
            report.append(f"## Episode {item['episode']}")
            report.append(f"- Artifact Families: {item['families']}")
            report.append(f"- Claims: {item['claims']}")
            report.append(f"- Nodes: {item['nodes']}\n")
            
            total_families += item['families']
            total_claims += item['claims']
            total_nodes += item['nodes']
        
        report.append(f"\n## Totals")
        report.append(f"- Artifact Families: {total_families}")
        report.append(f"- Claims: {total_claims}")
        report.append(f"- Unique Nodes: {total_nodes}\n")
        
        return "\n".join(report)
    
    # -------------------------------------------------------------------------
    # Main Analysis
    # -------------------------------------------------------------------------
    
    def run_all_analyses(self) -> str:
        """Run all pattern detection analyses and return markdown report."""
        report = ["# Cross-Episode Pattern Detection Report\n"]
        report.append(f"Generated: {os.popen('date').read().strip()}\n")
        report.append("---\n")
        
        # Episode summary
        print("[patterns] Running episode summary...")
        episode_data = self.episode_summary()
        report.append(self.format_episode_summary(episode_data))
        report.append("---\n")
        
        # Co-occurrence
        print("[patterns] Analyzing co-occurrence...")
        co_occur = self.co_occurrence_analysis()
        report.append(self.format_co_occurrence_report(co_occur))
        report.append("---\n")
        
        # Network centrality
        print("[patterns] Calculating network centrality...")
        network = self.network_centrality(limit=15)
        report.append(self.format_network_report(network))
        report.append("---\n")
        
        # Contradictions
        print("[patterns] Detecting contradictions...")
        contradictions = self.find_contradictions()
        report.append(self.format_contradiction_report(contradictions))
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Pattern detection for cross-episode analysis")
    parser.add_argument("command", nargs="?", default="all",
                       choices=["all", "co-occurrence", "contradictions", "network", "summary"],
                       help="Analysis to run")
    parser.add_argument("--person", help="Person ID for person-specific analysis")
    parser.add_argument("--keyword", help="Keyword filter for contradictions")
    parser.add_argument("--output", type=Path, help="Output file (markdown)")
    args = parser.parse_args()
    
    print(f"[patterns] Connecting to {NEO4J_URI}...")
    try:
        detector = PatternDetector()
    except Exception as e:
        print(f"ERROR: Could not connect to Neo4j: {e}")
        sys.exit(1)
    
    try:
        if args.command == "all":
            report = detector.run_all_analyses()
            
            if args.output:
                args.output.write_text(report, encoding="utf-8")
                print(f"\n✓ Report written to {args.output}")
            else:
                print(f"\n{report}")
        
        elif args.command == "co-occurrence":
            results = detector.co_occurrence_analysis()
            print(detector.format_co_occurrence_report(results))
        
        elif args.command == "contradictions":
            results = detector.find_contradictions(args.keyword)
            print(detector.format_contradiction_report(results))
        
        elif args.command == "network":
            results = detector.network_centrality()
            print(detector.format_network_report(results))
        
        elif args.command == "summary":
            results = detector.episode_summary()
            print(detector.format_episode_summary(results))
    
    finally:
        detector.close()


if __name__ == "__main__":
    main()
