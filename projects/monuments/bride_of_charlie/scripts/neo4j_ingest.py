"""
Neo4j Ingest Script for Bride of Charlie Episode Drafts
Parses markdown episode files and loads the investigative graph into Neo4j.

Usage:
    python scripts/neo4j_ingest.py [--drafts-dir drafts/] [--force]

Environment:
    NEO4J_URI (default: bolt://127.0.0.1:17687 — agent-lab docker-compose host port)
    NEO4J_USER (default: neo4j)
    NEO4J_PASSWORD (default: openclaw)
    NEO4J_INGEST_STRICT_CLAIMS (default: 1) — skip placeholder / unanchored / nodeless claims
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
DRAFTS_DIR = PROJECT_ROOT / "drafts"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")

# ---------------------------------------------------------------------------
# Regex patterns for parsing markdown
# ---------------------------------------------------------------------------

EPISODE_NUM_PATTERN = re.compile(r"episode[_\s]+(\d+)", re.IGNORECASE)
ARTIFACT_FAMILY_PATTERN = re.compile(r"^\*\*A-(\d+)\*\*\s+(.+)$", re.MULTILINE)
ARTIFACT_ITEM_PATTERN = re.compile(r"^\*\*A-(\d+)\.(\d+)\*\*\s+(.+)$", re.MULTILINE)
CLAIM_PATTERN = re.compile(r"^\*\*C-(\d+)\*\*\s+(.+)$", re.MULTILINE)
NODE_PATTERN = re.compile(r"^\*\*N-(\d+)\*\*\s+(.+)$", re.MULTILINE)
RELATED_PATTERN = re.compile(r"\*Related:\s*([^*]+)\*", re.IGNORECASE)

TIMESTAMP_PATTERNS = {
    "event": re.compile(r"Event Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE),
    "source": re.compile(r"Source Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE),
    "video": re.compile(r"Video Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE),
    "discovery": re.compile(r"Discovery Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE),
    "extraction": re.compile(r"Extraction Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE),
    "claim": re.compile(r"Claim Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE),
}

CONFIDENCE_PATTERN = re.compile(
    r"(?:Confidence Level:|Confidence:)\s*(high|medium|low)\b",
    re.IGNORECASE,
)
UNCERTAINTY_PATTERN = re.compile(r"^Uncertainty:\s*(.+)$", re.MULTILINE)
TRANSCRIPT_SNIPPET_PATTERN = re.compile(r"^Transcript Snippet:\s*(.+)$", re.MULTILINE)
CONTRADICTS_PATTERN = re.compile(r"^Contradicts:\s*(.+)$", re.MULTILINE)
SUPPORTS_PATTERN = re.compile(r"^Supports:\s*(.+)$", re.MULTILINE)
CLAIM_TEXT_PATTERN = re.compile(r"^Claim:\s*(.+)$", re.MULTILINE)
ANCHORED_ARTIFACTS_PATTERN = re.compile(r"Anchored Artifacts:\s*(.+)$", re.MULTILINE)
RELATED_NODES_PATTERN = re.compile(r"Related Nodes:\s*(.+)$", re.MULTILINE)
INVESTIGATIVE_DIRECTION_PATTERN = re.compile(r"Investigative Direction:\s*(.+)$", re.MULTILINE)

# Same Person node, other names (maiden/married/caption). Italic line after **N-* ** title.
ALSO_KNOWN_AS_PATTERN = re.compile(
    r"^\*Also known as:\s*(.+?)\*\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def parse_declared_aliases(section: str) -> list[str]:
    """Split *Also known as: …* into trimmed name strings (semicolon-separated)."""
    m = ALSO_KNOWN_AS_PATTERN.search(section)
    if not m:
        return []
    raw = m.group(1).strip()
    parts = [p.strip() for p in raw.split(";")]
    return [p for p in parts if p]


def is_also_known_as_line(line: str) -> bool:
    s = line.strip()
    return bool(ALSO_KNOWN_AS_PATTERN.match(s))

def extract_episode_num(text: str, filename: str) -> int:
    """Extract episode number from filename or content."""
    match = EPISODE_NUM_PATTERN.search(filename)
    if match:
        return int(match.group(1))
    match = EPISODE_NUM_PATTERN.search(text)
    if match:
        return int(match.group(1))
    return 0


_ID_TOKEN = re.compile(r"^(A-\d+(?:\.\d+)?|C-\d+|N-\d+)$")

# Skip LLM placeholder / slot claims (never ingest as real Claim nodes)
PLACEHOLDER_LABEL_PATTERNS = (
    re.compile(r"\[reserved", re.I),
    re.compile(r"\[not used", re.I),
    re.compile(r"\bfuture claims\b", re.I),
    re.compile(r"^\s*tbd\b", re.I),
    re.compile(r"\bplaceholder\b", re.I),
)


def is_placeholder_claim_label(label: str | None) -> bool:
    if not label or not str(label).strip():
        return True
    s = str(label).strip()
    return any(p.search(s) for p in PLACEHOLDER_LABEL_PATTERNS)


def parse_id_list(text: str) -> list[str]:
    """Parse comma-separated IDs: A-1000.1, C-1009, N-2 (handles dotted artifact refs)."""
    out: list[str] = []
    for part in re.split(r",", text):
        id = part.strip()
        if id.lower().startswith("same_as:"):
            id = id.split(":", 1)[1].strip()
        if id and _ID_TOKEN.match(id):
            out.append(id)
    return out


def extract_artifact_families(text: str, episode_num: int) -> list[dict[str, Any]]:
    """Extract artifact families (A-XXXX) from markdown."""
    families = []
    for match in ARTIFACT_FAMILY_PATTERN.finditer(text):
        family_id = f"A-{match.group(1)}"
        name = match.group(2).strip()
        families.append({"id": family_id, "name": name, "episode_num": episode_num})
    return families


def extract_artifacts(text: str, episode_num: int) -> list[dict[str, Any]]:
    """Extract individual artifacts (A-XXXX.Y) with timestamps and related IDs."""
    artifacts = []
    for match in ARTIFACT_ITEM_PATTERN.finditer(text):
        artifact_id = f"A-{match.group(1)}.{match.group(2)}"
        family_id = f"A-{match.group(1)}"
        description = match.group(3).strip()
        
        # Find the section for this artifact (from this match to next artifact or claim)
        start_pos = match.end()
        next_match = ARTIFACT_ITEM_PATTERN.search(text, start_pos)
        next_claim = CLAIM_PATTERN.search(text, start_pos)
        next_node = NODE_PATTERN.search(text, start_pos)
        
        end_pos = len(text)
        for m in [next_match, next_claim, next_node]:
            if m and m.start() < end_pos:
                end_pos = m.start()
        
        section = text[start_pos:end_pos]
        
        # Extract timestamps
        timestamps = {}
        for key, pattern in TIMESTAMP_PATTERNS.items():
            ts_match = pattern.search(section)
            if ts_match:
                timestamps[f"{key}_ts"] = ts_match.group(1).strip()
        
        # Extract confidence (high|medium|low)
        confidence = None
        conf_match = CONFIDENCE_PATTERN.search(section)
        if conf_match:
            confidence = conf_match.group(1).lower()

        uncertainty_note = None
        um = UNCERTAINTY_PATTERN.search(section)
        if um:
            uncertainty_note = um.group(1).strip()

        transcript_snippet = None
        ts = TRANSCRIPT_SNIPPET_PATTERN.search(section)
        if ts:
            transcript_snippet = ts.group(1).strip()
        
        # Extract related IDs
        related_ids = []
        rel_match = RELATED_PATTERN.search(section)
        if rel_match:
            related_ids = parse_id_list(rel_match.group(1))
        
        artifacts.append({
            "id": artifact_id,
            "family_id": family_id,
            "description": description,
            "episode_num": episode_num,
            "confidence": confidence,
            "uncertainty_note": uncertainty_note,
            "transcript_snippet": transcript_snippet,
            "related_ids": related_ids,
            **timestamps,
        })
    
    return artifacts


def extract_claims(text: str, episode_num: int) -> list[dict[str, Any]]:
    """Extract claims (C-XXXX) with anchored artifacts and related nodes."""
    claims = []
    for match in CLAIM_PATTERN.finditer(text):
        claim_id = f"C-{match.group(1)}"
        label = match.group(2).strip()
        
        # Find claim section
        start_pos = match.end()
        next_match = CLAIM_PATTERN.search(text, start_pos)
        next_node = NODE_PATTERN.search(text, start_pos)
        
        end_pos = len(text)
        for m in [next_match, next_node]:
            if m and m.start() < end_pos:
                end_pos = m.start()
        
        section = text[start_pos:end_pos]
        
        # Extract claim text
        claim_text = None
        claim_match = CLAIM_TEXT_PATTERN.search(section)
        if claim_match:
            claim_text = claim_match.group(1).strip()
        
        # Extract claim timestamp
        claim_ts = None
        ts_match = TIMESTAMP_PATTERNS["claim"].search(section)
        if ts_match:
            claim_ts = ts_match.group(1).strip()
        
        # Extract anchored artifacts
        anchored_artifacts = []
        anchor_match = ANCHORED_ARTIFACTS_PATTERN.search(section)
        if anchor_match:
            anchored_artifacts = parse_id_list(anchor_match.group(1))
        
        # Extract related nodes
        related_nodes = []
        nodes_match = RELATED_NODES_PATTERN.search(section)
        if nodes_match:
            related_nodes = parse_id_list(nodes_match.group(1))
        
        # Extract investigative direction
        investigative_direction = None
        inv_match = INVESTIGATIVE_DIRECTION_PATTERN.search(section)
        if inv_match:
            investigative_direction = inv_match.group(1).strip()

        contradicts_claims: list[str] = []
        cm = CONTRADICTS_PATTERN.search(section)
        if cm:
            contradicts_claims = [x for x in parse_id_list(cm.group(1)) if x.startswith("C-")]

        supports_claims: list[str] = []
        sm = SUPPORTS_PATTERN.search(section)
        if sm:
            supports_claims = [x for x in parse_id_list(sm.group(1)) if x.startswith("C-")]

        confidence = None
        cf = CONFIDENCE_PATTERN.search(section)
        if cf:
            confidence = cf.group(1).lower()

        uncertainty_note = None
        um = UNCERTAINTY_PATTERN.search(section)
        if um:
            uncertainty_note = um.group(1).strip()

        transcript_snippet = None
        tsp = TRANSCRIPT_SNIPPET_PATTERN.search(section)
        if tsp:
            transcript_snippet = tsp.group(1).strip()
        
        claims.append({
            "id": claim_id,
            "label": label,
            "claim_text": claim_text,
            "claim_ts": claim_ts,
            "episode_num": episode_num,
            "anchored_artifacts": anchored_artifacts,
            "related_nodes": related_nodes,
            "investigative_direction": investigative_direction,
            "contradicts_claims": contradicts_claims,
            "supports_claims": supports_claims,
            "confidence": confidence,
            "uncertainty_note": uncertainty_note,
            "transcript_snippet": transcript_snippet,
        })
    
    return claims


def extract_nodes(text: str, episode_num: int) -> list[dict[str, Any]]:
    """Extract nodes (N-X for people, N-1000+ for investigation targets)."""
    nodes = []
    for match in NODE_PATTERN.finditer(text):
        node_id = f"N-{match.group(1)}"
        name = match.group(2).strip()
        node_num = int(match.group(1))
        
        # Determine node type
        node_type = "InvestigationTarget" if node_num >= 1000 else "Person"
        
        # Find node section
        start_pos = match.end()
        next_match = NODE_PATTERN.search(text, start_pos)
        next_claim = CLAIM_PATTERN.search(text, start_pos)
        
        end_pos = len(text)
        for m in [next_match, next_claim]:
            if m and m.start() < end_pos:
                end_pos = m.start()
        
        section = text[start_pos:end_pos]

        declared_aliases = parse_declared_aliases(section)

        # Extract description (first non-empty line after node header)
        lines = section.split("\n")
        description = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith("Evidence Count:") or line.startswith("*Related:"):
                continue
            if is_also_known_as_line(line):
                continue
            description = line
            break

        # Extract related IDs
        related_ids = []
        rel_match = RELATED_PATTERN.search(section)
        if rel_match:
            related_ids = parse_id_list(rel_match.group(1))

        confidence = None
        cf = CONFIDENCE_PATTERN.search(section)
        if cf:
            confidence = cf.group(1).lower()

        uncertainty_note = None
        um = UNCERTAINTY_PATTERN.search(section)
        if um:
            uncertainty_note = um.group(1).strip()
        
        nodes.append({
            "id": node_id,
            "name": name,
            "node_type": node_type,
            "description": description,
            "episode_num": episode_num,
            "related_ids": related_ids,
            "confidence": confidence,
            "uncertainty_note": uncertainty_note,
            "declared_aliases": declared_aliases,
        })
    
    return nodes


def parse_episode_file(filepath: Path) -> dict[str, Any]:
    """Parse a single episode markdown file."""
    text = filepath.read_text(encoding="utf-8")
    episode_num = extract_episode_num(text, filepath.name)
    
    return {
        "episode_num": episode_num,
        "filename": filepath.name,
        "artifact_families": extract_artifact_families(text, episode_num),
        "artifacts": extract_artifacts(text, episode_num),
        "claims": extract_claims(text, episode_num),
        "nodes": extract_nodes(text, episode_num),
    }


# ---------------------------------------------------------------------------
# Name standardization helpers
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
    """Normalize name for comparison (lowercase, remove extra spaces)."""
    return " ".join(name.lower().split())


def find_similar_node(session, name: str, node_type: str, threshold: int = 3) -> dict | None:
    """
    Find existing node with similar name using fuzzy matching.
    Returns dict with id, canonical_name if found, None otherwise.
    """
    normalized_search = normalize_name(name)
    
    # Get all nodes of this type
    result = session.run(
        f"MATCH (n:{node_type}) "
        "RETURN n.id AS id, n.canonical_name AS canonical_name, n.aliases AS aliases"
    )
    
    for record in result:
        canonical = record["canonical_name"]
        aliases = record["aliases"] or []
        
        # Check exact match on canonical or aliases
        if normalize_name(canonical) == normalized_search:
            return {"id": record["id"], "canonical_name": canonical, "match_type": "exact"}
        
        for alias in aliases:
            if normalize_name(alias) == normalized_search:
                return {"id": record["id"], "canonical_name": canonical, "match_type": "alias"}
        
        # Check fuzzy match on canonical name
        distance = levenshtein_distance(normalize_name(canonical), normalized_search)
        if distance <= threshold:
            return {"id": record["id"], "canonical_name": canonical, "match_type": "fuzzy", "distance": distance}
    
    return None


def add_alias_to_node(session, node_id: str, node_type: str, alias: str):
    """Add an alias to an existing node."""
    session.run(
        f"MATCH (n:{node_type} {{id: $id}}) "
        "SET n.aliases = coalesce(n.aliases, []) + "
        "CASE WHEN $alias IN coalesce(n.aliases, []) THEN [] ELSE [$alias] END",
        id=node_id,
        alias=alias
    )


# ---------------------------------------------------------------------------
# Neo4j ingestion
# ---------------------------------------------------------------------------

def create_constraints(tx):
    """Create uniqueness constraints for all node types."""
    constraints = [
        "CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (a:Artifact) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT artifact_family_id IF NOT EXISTS FOR (af:ArtifactFamily) REQUIRE af.id IS UNIQUE",
        "CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE",
        "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT investigation_target_id IF NOT EXISTS FOR (it:InvestigationTarget) REQUIRE it.id IS UNIQUE",
        "CREATE CONSTRAINT episode_num IF NOT EXISTS FOR (e:Episode) REQUIRE e.episode_num IS UNIQUE",
    ]
    for constraint in constraints:
        try:
            tx.run(constraint)
        except Exception as e:
            # Constraint may already exist
            pass


def ingest_episode(driver, episode_data: dict[str, Any], force: bool = False, fuzzy_match: bool = True):
    """Ingest a single episode into Neo4j."""
    episode_num = episode_data["episode_num"]
    merge_log = []
    
    with driver.session() as session:
        # Create constraints first
        session.execute_write(create_constraints)
        
        # Create Episode node
        session.run(
            "MERGE (e:Episode {episode_num: $episode_num}) "
            "SET e.filename = $filename",
            episode_num=episode_num,
            filename=episode_data["filename"],
        )
        
        # Ingest artifact families
        for family in episode_data["artifact_families"]:
            session.run(
                "MERGE (af:ArtifactFamily {id: $id}) "
                "SET af.name = $name, af.episode_num = $episode_num "
                "WITH af "
                "MATCH (e:Episode {episode_num: $episode_num}) "
                "MERGE (e)-[:CONTAINS_FAMILY]->(af)",
                **family,
            )
        
        # Ingest artifacts
        for artifact in episode_data["artifacts"]:
            related_ids = artifact.get("related_ids", [])
            family_id = artifact["family_id"]
            
            # Props for Neo4j (no nulls; omit structural keys)
            props = {
                k: v
                for k, v in artifact.items()
                if k not in ("related_ids", "family_id") and v is not None
            }
            
            session.run(
                "MERGE (a:Artifact {id: $id}) "
                "SET a += $props "
                "WITH a "
                "MATCH (af:ArtifactFamily {id: $family_id}) "
                "MERGE (af)-[:HAS_ARTIFACT]->(a)",
                id=artifact["id"],
                props=props,
                family_id=family_id,
            )
        
        # Ingest nodes (Person and InvestigationTarget) with fuzzy matching
        for node in episode_data["nodes"]:
            related_ids = node.get("related_ids", [])
            node_type = node["node_type"]
            episode_num_node = node["episode_num"]
            node_id = node["id"]
            node_name = node["name"]
            
            # Check for similar existing node
            actual_node_id = node_id
            if fuzzy_match:
                similar = find_similar_node(session, node_name, node_type, threshold=3)
                if similar:
                    # Found similar node - merge into existing
                    actual_node_id = similar["id"]
                    if similar["match_type"] == "fuzzy":
                        merge_log.append(
                            f"  → Merged '{node_name}' ({node_id}) into '{similar['canonical_name']}' "
                            f"({actual_node_id}) [distance: {similar.get('distance', 0)}]"
                        )
                    elif similar["match_type"] == "alias":
                        merge_log.append(
                            f"  → Matched '{node_name}' to existing alias of '{similar['canonical_name']}' ({actual_node_id})"
                        )
                    
                    # Add original name as alias if different
                    if normalize_name(node_name) != normalize_name(similar["canonical_name"]):
                        add_alias_to_node(session, actual_node_id, node_type, node_name)
                    for alias in node.get("declared_aliases") or []:
                        a = (alias or "").strip()
                        if a and normalize_name(a) != normalize_name(similar["canonical_name"]):
                            add_alias_to_node(session, actual_node_id, node_type, a)

                    # Don't create new node - use existing
                    # Still create APPEARS_IN relationship
                    session.run(
                        f"MATCH (n:{node_type} {{id: $id}}) "
                        "MATCH (e:Episode {episode_num: $episode_num}) "
                        "MERGE (n)-[:APPEARS_IN]->(e)",
                        id=actual_node_id,
                        episode_num=episode_num_node,
                    )
                    continue
            
            # No similar node found - create new with canonical_name and declared aliases
            props = {
                k: v
                for k, v in node.items()
                if k
                not in (
                    "related_ids",
                    "node_type",
                    "episode_num",
                    "declared_aliases",
                    "name",
                )
                and v is not None
            }
            props["canonical_name"] = node_name
            props["aliases"] = [
                a.strip()
                for a in (node.get("declared_aliases") or [])
                if (a or "").strip()
                and normalize_name(a.strip()) != normalize_name(node_name)
            ]
            
            session.run(
                f"MERGE (n:{node_type} {{id: $id}}) "
                "SET n += $props "
                "WITH n "
                "MATCH (e:Episode {episode_num: $episode_num}) "
                "MERGE (n)-[:APPEARS_IN]->(e)",
                id=node_id,
                props=props,
                episode_num=episode_num_node,
            )
        
        strict_claims = os.getenv("NEO4J_INGEST_STRICT_CLAIMS", "1").lower() in (
            "1",
            "true",
            "yes",
        )
        artifact_id_set = {
            r["id"] for r in session.run("MATCH (a:Artifact) RETURN a.id AS id")
        }
        person_node_id_set = {
            r["id"]
            for r in session.run(
                "MATCH (n) WHERE n:Person OR n:InvestigationTarget RETURN n.id AS id"
            )
        }

        # Ingest claims
        for claim in episode_data["claims"]:
            label = claim.get("label")
            anchored_raw = list(claim.get("anchored_artifacts") or [])
            related_raw = list(claim.get("related_nodes") or [])
            resolved_artifacts = [a for a in anchored_raw if a in artifact_id_set]
            resolved_nodes = [n for n in related_raw if n in person_node_id_set]

            if strict_claims:
                if is_placeholder_claim_label(label):
                    merge_log.append(
                        f"  SKIP placeholder claim {claim['id']}: {(label or '')[:70]!r}"
                    )
                    continue
                if not resolved_artifacts:
                    merge_log.append(
                        f"  SKIP unanchored claim {claim['id']} (no Artifact in DB for {anchored_raw!r})"
                    )
                    continue
                if not resolved_nodes:
                    merge_log.append(
                        f"  SKIP claim {claim['id']} (no Person/InvestigationTarget in DB for {related_raw!r})"
                    )
                    continue
                use_artifacts = resolved_artifacts
                use_nodes = resolved_nodes
            else:
                use_artifacts = anchored_raw
                use_nodes = related_raw

            contradicts = claim.get("contradicts_claims") or []
            supports = claim.get("supports_claims") or []

            # Strip relationship keys and list fields not stored as Neo4j props
            props = {
                k: v
                for k, v in claim.items()
                if k
                not in (
                    "anchored_artifacts",
                    "related_nodes",
                    "contradicts_claims",
                    "supports_claims",
                )
                and v is not None
            }
            props["anchored_artifact_ids"] = ",".join(resolved_artifacts)
            props["related_node_ids"] = ",".join(resolved_nodes)

            session.run(
                "MERGE (c:Claim {id: $id}) "
                "SET c += $props "
                "WITH c "
                "MATCH (e:Episode {episode_num: $episode_num}) "
                "MERGE (c)-[:FROM_EPISODE]->(e)",
                id=claim["id"],
                props=props,
                episode_num=claim["episode_num"],
            )

            # Create ANCHORS relationships
            for artifact_id in use_artifacts:
                session.run(
                    "MATCH (a:Artifact {id: $artifact_id}) "
                    "MATCH (c:Claim {id: $claim_id}) "
                    "MERGE (a)-[:ANCHORS]->(c)",
                    artifact_id=artifact_id,
                    claim_id=claim["id"],
                )

            # Create INVOLVES relationships from claims to nodes
            for node_id in use_nodes:
                session.run(
                    "MATCH (c:Claim {id: $claim_id}) "
                    "MATCH (n) WHERE n.id = $node_id AND (n:Person OR n:InvestigationTarget) "
                    "MERGE (c)-[:INVOLVES]->(n)",
                    claim_id=claim["id"],
                    node_id=node_id,
                )

            for other_id in contradicts:
                session.run(
                    "MATCH (c1:Claim {id: $from_id}), (c2:Claim {id: $to_id}) "
                    "MERGE (c1)-[:CONTRADICTS]->(c2)",
                    from_id=claim["id"],
                    to_id=other_id,
                )
            for other_id in supports:
                session.run(
                    "MATCH (c1:Claim {id: $from_id}), (c2:Claim {id: $to_id}) "
                    "MERGE (c1)-[:SUPPORTS]->(c2)",
                    from_id=claim["id"],
                    to_id=other_id,
                )
        
        # Create INVOLVES relationships from artifacts to nodes (from related_ids)
        for artifact in episode_data["artifacts"]:
            artifact_id = artifact["id"]
            # Re-parse to get related_ids
            for node_id in artifact.get("related_ids", []):
                if node_id.startswith("N-"):
                    session.run(
                        "MATCH (a:Artifact {id: $artifact_id}) "
                        "MATCH (n) WHERE n.id = $node_id AND (n:Person OR n:InvestigationTarget) "
                        "MERGE (a)-[:INVOLVES]->(n)",
                        artifact_id=artifact_id,
                        node_id=node_id,
                    )
    
    return merge_log


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest Bride of Charlie episode drafts into Neo4j")
    parser.add_argument("--drafts-dir", type=Path, default=DRAFTS_DIR, help="Directory containing episode draft markdown files")
    parser.add_argument("--force", action="store_true", help="Clear existing graph before ingesting")
    parser.add_argument("--no-fuzzy-match", action="store_true", help="Disable fuzzy name matching (exact matches only)")
    args = parser.parse_args()
    
    fuzzy_match = not args.no_fuzzy_match
    
    drafts_dir = args.drafts_dir
    if not drafts_dir.exists():
        print(f"ERROR: Drafts directory not found: {drafts_dir}")
        sys.exit(1)
    
    # Find episode files (exclude cross_episode_analysis)
    episode_files = sorted([f for f in drafts_dir.glob("episode_*.md")])
    if not episode_files:
        print(f"ERROR: No episode_*.md files found in {drafts_dir}")
        sys.exit(1)
    
    print(f"[neo4j-ingest] Connecting to {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: Could not connect to Neo4j: {e}")
        print("Make sure Neo4j is running: docker compose up -d")
        sys.exit(1)
    
    if args.force:
        print("[neo4j-ingest] FORCE mode: clearing graph (preserving NameCorrection nodes)...")
        with driver.session() as session:
            session.run("""
                MATCH (n)
                WHERE NOT n:NameCorrection
                DETACH DELETE n
            """)
    
    if fuzzy_match:
        print(f"[neo4j-ingest] Fuzzy name matching: ENABLED (use --no-fuzzy-match to disable)")
    else:
        print(f"[neo4j-ingest] Fuzzy name matching: DISABLED")
    
    print(f"[neo4j-ingest] Ingesting {len(episode_files)} episode(s)...")
    
    for i, filepath in enumerate(episode_files, 1):
        print(f"  [{i}/{len(episode_files)}] {filepath.name}")
        try:
            episode_data = parse_episode_file(filepath)
            merge_log = ingest_episode(driver, episode_data, args.force, fuzzy_match)
            print(f"       OK (Episode {episode_data['episode_num']})")
            if merge_log:
                for log_line in merge_log:
                    print(log_line)
        except Exception as e:
            print(f"       ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    driver.close()
    print(f"\n[neo4j-ingest] Done. View graph at http://localhost:7474")
    print(f"[neo4j-ingest] Login: neo4j / openclaw")


if __name__ == "__main__":
    main()
