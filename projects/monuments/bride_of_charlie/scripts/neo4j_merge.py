"""
Neo4j Node Merge Tool
Interactive tool to find and merge duplicate nodes in the investigative graph.

Usage:
    python scripts/neo4j_merge.py [--auto] [--threshold N]

Options:
    --auto          Auto-merge nodes with distance <= threshold (no prompts)
    --threshold N   Levenshtein distance threshold for fuzzy matching (default: 3)
    --dry-run       Show what would be merged without making changes

Environment:
    NEO4J_URI (default: bolt://localhost:7687)
    NEO4J_USER (default: neo4j)
    NEO4J_PASSWORD (default: openclaw)
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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")

# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def normalize_name(name: str) -> str:
    """Normalize name for comparison."""
    return " ".join(name.lower().split())


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def find_potential_duplicates(session, node_type: str, threshold: int = 3) -> list[dict]:
    """Find pairs of nodes with similar names."""
    result = session.run(
        f"MATCH (n:{node_type}) "
        "RETURN n.id AS id, n.canonical_name AS name, n.aliases AS aliases "
        "ORDER BY n.id"
    )
    
    nodes = list(result)
    duplicates = []
    
    for i, node1 in enumerate(nodes):
        for node2 in nodes[i+1:]:
            name1 = node1["name"] or ""
            name2 = node2["name"] or ""
            
            distance = levenshtein_distance(normalize_name(name1), normalize_name(name2))
            
            if distance <= threshold:
                duplicates.append({
                    "node1_id": node1["id"],
                    "node1_name": name1,
                    "node2_id": node2["id"],
                    "node2_name": name2,
                    "distance": distance,
                    "node_type": node_type
                })
    
    return duplicates


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------

def merge_nodes(session, keep_id: str, merge_id: str, node_type: str, add_alias: str | None = None):
    """
    Merge merge_id into keep_id:
    1. Transfer all relationships from merge_id to keep_id
    2. Add merge_id's name as alias to keep_id (if provided)
    3. Delete merge_id node
    """
    # Transfer all incoming relationships
    session.run(
        f"MATCH (source)-[r]->(merge:{node_type} {{id: $merge_id}}) "
        f"MATCH (keep:{node_type} {{id: $keep_id}}) "
        "WITH source, keep, type(r) AS rel_type, properties(r) AS props "
        "CALL apoc.create.relationship(source, rel_type, props, keep) YIELD rel "
        "RETURN count(rel) AS transferred",
        keep_id=keep_id,
        merge_id=merge_id
    )
    
    # Transfer all outgoing relationships
    session.run(
        f"MATCH (merge:{node_type} {{id: $merge_id}})-[r]->(target) "
        f"MATCH (keep:{node_type} {{id: $keep_id}}) "
        "WITH keep, target, type(r) AS rel_type, properties(r) AS props "
        "CALL apoc.create.relationship(keep, rel_type, props, target) YIELD rel "
        "RETURN count(rel) AS transferred",
        keep_id=keep_id,
        merge_id=merge_id
    )
    
    # Add alias if provided
    if add_alias:
        session.run(
            f"MATCH (keep:{node_type} {{id: $keep_id}}) "
            "SET keep.aliases = coalesce(keep.aliases, []) + "
            "CASE WHEN $alias IN coalesce(keep.aliases, []) THEN [] ELSE [$alias] END",
            keep_id=keep_id,
            alias=add_alias
        )
    
    # Delete the merged node
    session.run(
        f"MATCH (merge:{node_type} {{id: $merge_id}}) "
        "DETACH DELETE merge",
        merge_id=merge_id
    )


# ---------------------------------------------------------------------------
# Interactive merge
# ---------------------------------------------------------------------------

def interactive_merge(session, duplicates: list[dict], dry_run: bool = False):
    """Prompt user for each potential duplicate pair."""
    merged_count = 0
    skipped_count = 0
    
    for i, dup in enumerate(duplicates, 1):
        print(f"\n[{i}/{len(duplicates)}] Potential duplicate (distance: {dup['distance']}):")
        print(f"  1. {dup['node1_id']}: {dup['node1_name']}")
        print(f"  2. {dup['node2_id']}: {dup['node2_name']}")
        print()
        
        while True:
            choice = input("  Merge? [1→2 / 2→1 / skip / quit]: ").strip().lower()
            
            if choice == "quit" or choice == "q":
                print(f"\n[neo4j-merge] Stopped. Merged: {merged_count}, Skipped: {skipped_count}")
                return
            
            if choice == "skip" or choice == "s" or choice == "":
                skipped_count += 1
                break
            
            if choice == "1→2" or choice == "12":
                # Merge node1 into node2 (keep node2)
                keep_id = dup["node2_id"]
                merge_id = dup["node1_id"]
                add_alias = dup["node1_name"]
                
                if dry_run:
                    print(f"  [DRY RUN] Would merge {merge_id} into {keep_id}, add alias '{add_alias}'")
                else:
                    merge_nodes(session, keep_id, merge_id, dup["node_type"], add_alias)
                    print(f"  ✓ Merged {merge_id} into {keep_id}")
                
                merged_count += 1
                break
            
            if choice == "2→1" or choice == "21":
                # Merge node2 into node1 (keep node1)
                keep_id = dup["node1_id"]
                merge_id = dup["node2_id"]
                add_alias = dup["node2_name"]
                
                if dry_run:
                    print(f"  [DRY RUN] Would merge {merge_id} into {keep_id}, add alias '{add_alias}'")
                else:
                    merge_nodes(session, keep_id, merge_id, dup["node_type"], add_alias)
                    print(f"  ✓ Merged {merge_id} into {keep_id}")
                
                merged_count += 1
                break
            
            print("  Invalid choice. Use: 1→2, 2→1, skip, or quit")
    
    print(f"\n[neo4j-merge] Complete. Merged: {merged_count}, Skipped: {skipped_count}")


def auto_merge(session, duplicates: list[dict], dry_run: bool = False):
    """Auto-merge duplicates (keep lower ID, merge higher ID)."""
    merged_count = 0
    
    for dup in duplicates:
        # Keep the node with lower ID
        if dup["node1_id"] < dup["node2_id"]:
            keep_id = dup["node1_id"]
            merge_id = dup["node2_id"]
            add_alias = dup["node2_name"]
        else:
            keep_id = dup["node2_id"]
            merge_id = dup["node1_id"]
            add_alias = dup["node1_name"]
        
        if dry_run:
            print(f"  [DRY RUN] Would merge {merge_id} into {keep_id}, add alias '{add_alias}'")
        else:
            merge_nodes(session, keep_id, merge_id, dup["node_type"], add_alias)
            print(f"  ✓ Merged {merge_id} ({dup['node2_name']}) into {keep_id} ({dup['node1_name']})")
        
        merged_count += 1
    
    print(f"\n[neo4j-merge] Auto-merged {merged_count} node(s)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Find and merge duplicate nodes in Neo4j")
    parser.add_argument("--auto", action="store_true", help="Auto-merge without prompts (keep lower ID)")
    parser.add_argument("--threshold", type=int, default=3, help="Levenshtein distance threshold (default: 3)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be merged without making changes")
    parser.add_argument("--node-type", choices=["Person", "InvestigationTarget", "all"], default="all", help="Node type to check")
    args = parser.parse_args()
    
    print(f"[neo4j-merge] Connecting to {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: Could not connect to Neo4j: {e}")
        print("Make sure Neo4j is running: docker compose up -d")
        sys.exit(1)
    
    node_types = ["Person", "InvestigationTarget"] if args.node_type == "all" else [args.node_type]
    
    all_duplicates = []
    
    with driver.session() as session:
        for node_type in node_types:
            print(f"\n[neo4j-merge] Scanning {node_type} nodes (threshold: {args.threshold})...")
            duplicates = find_potential_duplicates(session, node_type, args.threshold)
            
            if duplicates:
                print(f"  Found {len(duplicates)} potential duplicate(s)")
                all_duplicates.extend(duplicates)
            else:
                print(f"  No duplicates found")
        
        if not all_duplicates:
            print("\n[neo4j-merge] No duplicates to merge. Done.")
            driver.close()
            return
        
        print(f"\n[neo4j-merge] Total: {len(all_duplicates)} potential duplicate(s)")
        
        if args.dry_run:
            print("[neo4j-merge] DRY RUN mode - no changes will be made")
        
        if args.auto:
            auto_merge(session, all_duplicates, args.dry_run)
        else:
            interactive_merge(session, all_duplicates, args.dry_run)
    
    driver.close()


if __name__ == "__main__":
    main()
