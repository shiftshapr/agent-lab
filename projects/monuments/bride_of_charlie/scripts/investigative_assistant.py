"""
Neo4j-Powered Investigative Assistant
Answers questions about the Bride of Charlie investigation with full citations.

Usage:
    # Interactive mode
    python scripts/investigative_assistant.py
    
    # Single question
    python scripts/investigative_assistant.py --query "What do we know about Erica Kirk's birth date?"
    
    # Export mode (generate report)
    python scripts/investigative_assistant.py --export person --id N-2 --output erica_kirk_report.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")


class InvestigativeAssistant:
    """Neo4j-powered assistant for investigating the Bride of Charlie case."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def close(self):
        self.driver.close()
    
    # -------------------------------------------------------------------------
    # Core Query Functions
    # -------------------------------------------------------------------------
    
    def search_person(self, name: str) -> list[dict]:
        """Find people by name (fuzzy match)."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person)
                WHERE p.canonical_name CONTAINS $name
                   OR any(alias IN p.aliases WHERE alias CONTAINS $name)
                RETURN p.id AS id,
                       p.canonical_name AS name,
                       p.aliases AS aliases
                ORDER BY p.id
            """, name=name)
            
            return [dict(record) for record in result]
    
    def get_person_summary(self, person_id: str) -> dict | None:
        """Get comprehensive summary for a person."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {id: $id})
                OPTIONAL MATCH (p)-[:APPEARS_IN]->(e:Episode)
                OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(p)
                OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(p)
                WITH p,
                     collect(DISTINCT e.episode_num) AS episodes,
                     count(DISTINCT c) AS claim_count,
                     count(DISTINCT a) AS artifact_count
                RETURN p.id AS id,
                       p.canonical_name AS name,
                       p.aliases AS aliases,
                       p.description AS description,
                       episodes,
                       claim_count,
                       artifact_count
            """, id=person_id)
            
            record = result.single()
            return dict(record) if record else None
    
    def get_claims_about(self, person_id: str) -> list[dict]:
        """Get all claims involving a person."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {id: $id})
                MATCH (c:Claim)-[:INVOLVES]->(p)
                OPTIONAL MATCH (a:Artifact)-[:ANCHORS]->(c)
                WITH c, collect(DISTINCT a.id) AS artifacts
                RETURN c.id AS claim_id,
                       c.label AS label,
                       c.claim_text AS text,
                       c.episode_num AS episode,
                       c.claim_ts AS timestamp,
                       c.investigative_direction AS direction,
                       artifacts
                ORDER BY c.episode_num, c.id
            """, id=person_id)
            
            return [dict(record) for record in result]
    
    def get_artifacts_about(self, person_id: str) -> list[dict]:
        """Get all artifacts involving a person."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {id: $id})
                MATCH (a:Artifact)-[:INVOLVES]->(p)
                RETURN a.id AS artifact_id,
                       a.description AS description,
                       a.episode_num AS episode,
                       a.event_ts AS event_timestamp,
                       a.video_ts AS video_timestamp,
                       a.confidence AS confidence
                ORDER BY a.episode_num, a.id
            """, id=person_id)
            
            return [dict(record) for record in result]
    
    def search_claims(self, keyword: str) -> list[dict]:
        """Search claims by keyword."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Claim)
                WHERE c.label CONTAINS $keyword
                   OR c.claim_text CONTAINS $keyword
                OPTIONAL MATCH (c)-[:INVOLVES]->(n)
                WHERE n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget
                WITH c, collect(DISTINCT n.canonical_name) AS entities
                RETURN c.id AS claim_id,
                       c.label AS label,
                       c.claim_text AS text,
                       c.episode_num AS episode,
                       entities
                ORDER BY c.episode_num, c.id
                LIMIT 20
            """, keyword=keyword)
            
            return [dict(record) for record in result]
    
    def find_contradictions(self, person_id: str | None = None) -> list[dict]:
        """Find contradictory claims (optionally filtered by person)."""
        with self.driver.session() as session:
            query = """
                MATCH (c1:Claim)-[:INVOLVES]->(n)<-[:INVOLVES]-(c2:Claim)
                WHERE c1.id < c2.id
            """
            
            if person_id:
                query += " AND n.id = $person_id "
            
            query += """
                WITH c1, c2, n,
                     apoc.text.levenshteinSimilarity(c1.claim_text, c2.claim_text) AS similarity
                WHERE similarity > 0.3 AND similarity < 0.9
                RETURN c1.id AS claim1_id,
                       c1.claim_text AS claim1_text,
                       c1.episode_num AS claim1_episode,
                       c2.id AS claim2_id,
                       c2.claim_text AS claim2_text,
                       c2.episode_num AS claim2_episode,
                       n.canonical_name AS about,
                       round(similarity * 100, 2) AS similarity_pct
                ORDER BY similarity DESC
                LIMIT 10
            """
            
            result = session.run(query, person_id=person_id)
            return [dict(record) for record in result]
    
    def get_timeline(self, person_id: str) -> list[dict]:
        """Get chronological timeline for a person."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person {id: $id})
                MATCH (c:Claim)-[:INVOLVES]->(p)
                WHERE c.claim_ts IS NOT NULL OR c.episode_num IS NOT NULL
                RETURN c.episode_num AS episode,
                       c.claim_ts AS timestamp,
                       c.claim_text AS event,
                       c.id AS claim_id
                ORDER BY c.episode_num, c.claim_ts
            """, id=person_id)
            
            return [dict(record) for record in result]
    
    def get_connections(self, person_id: str) -> list[dict]:
        """Find people connected to this person (co-appear in episodes)."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p1:Person {id: $id})-[:APPEARS_IN]->(e:Episode)<-[:APPEARS_IN]-(p2:Person)
                WHERE p1.id <> p2.id
                WITH p2, collect(DISTINCT e.episode_num) AS episodes
                RETURN p2.id AS person_id,
                       p2.canonical_name AS name,
                       episodes,
                       size(episodes) AS episode_count
                ORDER BY episode_count DESC, p2.id
            """, id=person_id)
            
            return [dict(record) for record in result]
    
    def get_investigation_targets(self) -> list[dict]:
        """Get Topic, Organization, Place, and legacy InvestigationTarget nodes with pressure scores."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (it)
                WHERE it:InvestigationTarget OR it:Topic OR it:Organization OR it:Place
                OPTIONAL MATCH (a:Artifact)-[:INVOLVES]->(it)
                OPTIONAL MATCH (c:Claim)-[:INVOLVES]->(it)
                OPTIONAL MATCH (it)-[:APPEARS_IN]->(e:Episode)
                WITH it,
                     count(DISTINCT a) AS artifacts,
                     count(DISTINCT c) AS claims,
                     count(DISTINCT e) AS episodes
                RETURN it.id AS id,
                       it.canonical_name AS name,
                       it.description AS description,
                       labels(it)[0] AS primary_label,
                       artifacts,
                       claims,
                       episodes,
                       (artifacts + claims * 2 + episodes) AS pressure_score
                ORDER BY pressure_score DESC
            """)
            
            return [dict(record) for record in result]
    
    # -------------------------------------------------------------------------
    # Formatting Functions
    # -------------------------------------------------------------------------
    
    def format_person_report(self, person_id: str) -> str:
        """Generate a comprehensive markdown report for a person."""
        summary = self.get_person_summary(person_id)
        if not summary:
            return f"Person {person_id} not found."
        
        report = []
        report.append(f"# {summary['name']}")
        report.append(f"\n**ID:** {summary['id']}")
        
        if summary['aliases']:
            report.append(f"**Aliases:** {', '.join(summary['aliases'])}")
        
        if summary['description']:
            report.append(f"\n{summary['description']}")
        
        report.append(f"\n**Episodes:** {', '.join(map(str, summary['episodes']))}")
        report.append(f"**Evidence:** {summary['artifact_count']} artifacts, {summary['claim_count']} claims")
        
        # Claims
        claims = self.get_claims_about(person_id)
        if claims:
            report.append(f"\n## Claims ({len(claims)})\n")
            for claim in claims:
                report.append(f"### {claim['claim_id']}: {claim['label']}")
                report.append(f"\n**Episode {claim['episode']}**")
                if claim['timestamp']:
                    report.append(f" (Timestamp: {claim['timestamp']})")
                report.append(f"\n\n{claim['text']}")
                
                if claim['artifacts']:
                    report.append(f"\n**Anchored Artifacts:** {', '.join(claim['artifacts'])}")
                
                if claim['direction']:
                    report.append(f"\n**Investigative Direction:** {claim['direction']}")
                
                report.append("\n")
        
        # Artifacts
        artifacts = self.get_artifacts_about(person_id)
        if artifacts:
            report.append(f"\n## Evidence ({len(artifacts)})\n")
            for artifact in artifacts:
                report.append(f"- **{artifact['artifact_id']}** (Episode {artifact['episode']}): {artifact['description']}")
                if artifact['confidence']:
                    report.append(f" [Confidence: {artifact['confidence']}]")
                report.append("")
        
        # Connections
        connections = self.get_connections(person_id)
        if connections:
            report.append(f"\n## Connections\n")
            for conn in connections[:10]:
                episodes_str = ", ".join(map(str, conn['episodes']))
                report.append(f"- **{conn['name']}** ({conn['person_id']}): {conn['episode_count']} episodes [{episodes_str}]")
        
        # Timeline
        timeline = self.get_timeline(person_id)
        if timeline:
            report.append(f"\n## Timeline\n")
            for event in timeline:
                ts = f" ({event['timestamp']})" if event['timestamp'] else ""
                report.append(f"- **Episode {event['episode']}{ts}**: {event['event']} [{event['claim_id']}]")
        
        return "\n".join(report)
    
    def format_answer(self, question: str, data: Any) -> str:
        """Format an answer with citations."""
        # This is a simple formatter - could be enhanced with LLM
        if isinstance(data, list) and len(data) == 0:
            return "No results found."
        
        if isinstance(data, dict):
            return str(data)
        
        if isinstance(data, list):
            return "\n".join([str(item) for item in data])
        
        return str(data)
    
    # -------------------------------------------------------------------------
    # Interactive Mode
    # -------------------------------------------------------------------------
    
    def interactive(self):
        """Run interactive question-answering session."""
        print("=" * 80)
        print("INVESTIGATIVE ASSISTANT - Bride of Charlie")
        print("=" * 80)
        print("\nCommands:")
        print("  person <name>        - Search for a person")
        print("  claims <keyword>     - Search claims")
        print("  contradictions       - Find contradictory claims")
        print("  targets              - List investigation targets")
        print("  report <person_id>   - Generate full report")
        print("  quit                 - Exit")
        print("\n" + "=" * 80 + "\n")
        
        while True:
            try:
                query = input("Q: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ["quit", "exit", "q"]:
                    break
                
                parts = query.split(maxsplit=1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if command == "person":
                    results = self.search_person(arg)
                    if not results:
                        print("No people found.\n")
                    else:
                        print(f"\nFound {len(results)} person(s):\n")
                        for person in results:
                            aliases = f" (aliases: {', '.join(person['aliases'])})" if person['aliases'] else ""
                            print(f"  {person['id']}: {person['name']}{aliases}")
                        print()
                
                elif command == "claims":
                    results = self.search_claims(arg)
                    if not results:
                        print("No claims found.\n")
                    else:
                        print(f"\nFound {len(results)} claim(s):\n")
                        for claim in results:
                            entities = ", ".join(claim['entities']) if claim['entities'] else "none"
                            print(f"  {claim['claim_id']} (Episode {claim['episode']}): {claim['label']}")
                            print(f"    Entities: {entities}")
                            print(f"    {claim['text'][:100]}...")
                            print()
                
                elif command == "contradictions":
                    results = self.find_contradictions(arg if arg else None)
                    if not results:
                        print("No contradictions found.\n")
                    else:
                        print(f"\nFound {len(results)} potential contradiction(s):\n")
                        for contra in results:
                            print(f"  About: {contra['about']}")
                            print(f"    {contra['claim1_id']} (Episode {contra['claim1_episode']}): {contra['claim1_text']}")
                            print(f"    {contra['claim2_id']} (Episode {contra['claim2_episode']}): {contra['claim2_text']}")
                            print(f"    Similarity: {contra['similarity_pct']}%")
                            print()
                
                elif command == "targets":
                    results = self.get_investigation_targets()
                    if not results:
                        print("No investigation targets found.\n")
                    else:
                        print(f"\nInvestigation Targets ({len(results)}):\n")
                        for target in results:
                            print(f"  {target['id']}: {target['name']}")
                            print(f"    Pressure Score: {target['pressure_score']} ({target['artifacts']} artifacts, {target['claims']} claims, {target['episodes']} episodes)")
                            if target['description']:
                                print(f"    {target['description']}")
                            print()
                
                elif command == "report":
                    report = self.format_person_report(arg)
                    print(f"\n{report}\n")
                
                else:
                    print(f"Unknown command: {command}\n")
            
            except KeyboardInterrupt:
                print("\n")
                break
            except Exception as e:
                print(f"Error: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Investigative Assistant")
    parser.add_argument("--query", help="Single question to answer")
    parser.add_argument("--export", choices=["person", "targets"], help="Export report type")
    parser.add_argument("--id", help="Entity ID for export")
    parser.add_argument("--output", type=Path, help="Output file for export")
    args = parser.parse_args()
    
    assistant = InvestigativeAssistant()
    
    try:
        if args.export:
            if args.export == "person":
                if not args.id:
                    print("ERROR: --id required for person export")
                    return
                
                report = assistant.format_person_report(args.id)
                
                if args.output:
                    args.output.write_text(report, encoding="utf-8")
                    print(f"✓ Report written to {args.output}")
                else:
                    print(report)
            
            elif args.export == "targets":
                targets = assistant.get_investigation_targets()
                print(f"Investigation Targets ({len(targets)}):\n")
                for target in targets:
                    print(f"{target['id']}: {target['name']}")
                    print(f"  Pressure: {target['pressure_score']} ({target['artifacts']} artifacts, {target['claims']} claims)")
                    print()
        
        elif args.query:
            # Simple query mode - could be enhanced
            if "person" in args.query.lower() or "who" in args.query.lower():
                # Extract name from query
                words = args.query.split()
                name = " ".join(words[-2:])  # Crude extraction
                results = assistant.search_person(name)
                print(assistant.format_answer(args.query, results))
            else:
                print("Query mode not fully implemented yet. Use interactive mode.")
        
        else:
            # Interactive mode
            assistant.interactive()
    
    finally:
        assistant.close()


if __name__ == "__main__":
    main()
