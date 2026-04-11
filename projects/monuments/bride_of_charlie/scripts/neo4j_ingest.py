"""
Neo4j Ingest Script for Bride of Charlie Episode Drafts
Parses markdown episode files and loads the investigative graph into Neo4j.

Node labels: Person, Topic, Organization, Place, InvestigationTarget (legacy),
LegalMatter, Meme.

Claim graph: CONTRADICTS, SUPPORTS, QUALIFIES; SUPPORTED_BY from claims with
Sensitive Tags to each anchored artifact. Legal matters, org–org links, roles,
SAME_AS, provenance (CITES_SOURCE, DERIVED_FROM, RECORDING_OF), MENTIONS_TOPIC,
meme links (INVOKES_MEME, TARGETS_NODE).

Usage:
    python scripts/neo4j_ingest.py [--drafts-dir drafts/] [--force]

Environment:
    NEO4J_URI (default: bolt://127.0.0.1:17687 — agent-lab docker-compose host port)
    NEO4J_USER (default: neo4j)
    NEO4J_PASSWORD (default: openclaw)
    NEO4J_INGEST_STRICT_CLAIMS (default: 1) — skip placeholder / malformed claims
    NEO4J_INGEST_UNSUBSTANTIATED_CLAIMS (default: 1) — with strict on, ingest claims with no A-* anchor
        when they have ≥1 resolved Related Node (INVOLVES) and/or a TopicMention line to a
        resolved Topic/InvestigationTarget; set Claim.substantiated = false

Multi-episode ingest keeps a cumulative draft N-* → graph id map so fuzzy-merged nodes
still resolve in claims and structural edges (OrgLink, RoleLink, artifact *Related*, etc.).
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
QUALIFIES_PATTERN = re.compile(r"^Qualifies:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
SENSITIVE_TAGS_PATTERN = re.compile(r"^Sensitive Tags:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
CLAIM_TEXT_PATTERN = re.compile(r"^Claim:\s*(.+)$", re.MULTILINE)
# Use horizontal whitespace only after the colon: \s* would swallow newlines and
# merge the next field line into this capture (e.g. empty Anchored + Related Nodes).
ANCHORED_ARTIFACTS_PATTERN = re.compile(
    r"^Anchored Artifacts:[ \t]*([^\n]*?)\s*$", re.MULTILINE
)
RELATED_NODES_PATTERN = re.compile(
    r"^Related Nodes:[ \t]*([^\n]*?)\s*$", re.MULTILINE
)
INVESTIGATIVE_DIRECTION_PATTERN = re.compile(r"Investigative Direction:\s*(.+)$", re.MULTILINE)

# After **N-* ** title — emitted by assign_ids for clean graph filters.
NODE_TYPE_PATTERN = re.compile(r"^Node Type:\s*(.+)\s*$", re.MULTILINE | re.IGNORECASE)
TOPIC_KIND_PATTERN = re.compile(r"^Topic Kind:\s*(.+)\s*$", re.MULTILINE | re.IGNORECASE)
ORG_KIND_PATTERN = re.compile(r"^Organization Kind:\s*(.+)\s*$", re.MULTILINE | re.IGNORECASE)
PLACE_KIND_PATTERN = re.compile(r"^Place Kind:\s*(.+)\s*$", re.MULTILINE | re.IGNORECASE)

LEGAL_MATTER_HEADER = re.compile(r"^\*\*(LM-\d+)\*\*\s+(.+)$", re.MULTILINE)
LM_PARTY_PATTERN = re.compile(r"^Party Nodes:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
LM_PLACE_PATTERN = re.compile(r"^Place Nodes:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
LM_ARTIFACT_PATTERN = re.compile(r"^Artifact Anchors:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
LM_DESC_PATTERN = re.compile(r"^Description:\s*(.+)$", re.MULTILINE | re.IGNORECASE)

ORG_LINK_PATTERN = re.compile(r"^OrgLink:\s+(\S+)\s+([a-z_]+)\s+(\S+)\s*$", re.MULTILINE)
ROLE_LINK_PATTERN = re.compile(
    r"^RoleLink:\s+(\S+)\s+(holds_role|member_of|chair_of)\s+(\S+)(?:\s+title:(.*))?$",
    re.MULTILINE,
)
SAME_AS_LINE_PATTERN = re.compile(r"^SameAs:\s+(\S+)\s+(\S+)\s*$", re.MULTILINE)
PROV_LINE_PATTERN = re.compile(
    r"^Prov:\s+(\S+)\s+(cites_source|derived_from|recording_of)\s+(\S+)\s*$",
    re.MULTILINE,
)
TOPIC_MENTION_PATTERN = re.compile(r"^TopicMention:\s+(\S+)\s+(\S+)\s*$", re.MULTILINE)
MEME_LINK_PATTERN = re.compile(
    r"^MemeLink:\s+(M-\d+)\s+(invoked_by_claim|invoked_by_speaker|targets_node)\s+(\S+)\s*$",
    re.MULTILINE,
)
MEME_NODE_HEADER = re.compile(r"^\*\*(M-\d+)\*\*\s+\((\w+)\)\s+(.+)$", re.MULTILINE)

# Map JSON relation -> Neo4j relationship type (org–org)
ORG_REL_TYPES = {
    "subsidiary_of": "SUBSIDIARY_OF",
    "affiliated_with": "AFFILIATED_WITH",
    "contractor_for": "CONTRACTOR_FOR",
    "funded_by": "FUNDED_BY",
    "donated_to": "DONATED_TO",
    "parent_of": "PARENT_OF",
    "same_enterprise_as": "SAME_ENTERPRISE_AS",
}

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


def _is_node_metadata_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s.startswith("Evidence Count:") or s.startswith("*Related:"):
        return True
    if is_also_known_as_line(s):
        return True
    if NODE_TYPE_PATTERN.match(s) or TOPIC_KIND_PATTERN.match(s):
        return True
    if ORG_KIND_PATTERN.match(s) or PLACE_KIND_PATTERN.match(s):
        return True
    return False


def _parse_node_type_label(raw: str | None, node_num: int) -> str:
    """Normalize markdown 'Node Type:' value to a Neo4j label."""
    if not raw or not str(raw).strip():
        return "InvestigationTarget" if node_num >= 1000 else "Person"
    t = str(raw).strip().lower().replace(" ", "")
    aliases = {
        "person": "Person",
        "topic": "Topic",
        "organization": "Organization",
        "place": "Place",
        "investigationtarget": "InvestigationTarget",
        "investigation_target": "InvestigationTarget",
    }
    if t in aliases:
        return aliases[t]
    return "InvestigationTarget" if node_num >= 1000 else "Person"


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

        qualifies_claims: list[str] = []
        qm = QUALIFIES_PATTERN.search(section)
        if qm:
            qualifies_claims = [x for x in parse_id_list(qm.group(1)) if x.startswith("C-")]

        sensitive_topic_tags: list[str] = []
        st = SENSITIVE_TAGS_PATTERN.search(section)
        if st:
            sensitive_topic_tags = [
                t.strip()
                for t in re.split(r",\s*", st.group(1).strip())
                if t.strip()
            ]

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
            "qualifies_claims": qualifies_claims,
            "sensitive_topic_tags": sensitive_topic_tags,
            "confidence": confidence,
            "uncertainty_note": uncertainty_note,
            "transcript_snippet": transcript_snippet,
        })
    
    return claims


def extract_nodes(text: str, episode_num: int) -> list[dict[str, Any]]:
    """Extract nodes (N-*); label from Node Type line or legacy N-1000+ → InvestigationTarget."""
    nodes = []
    for match in NODE_PATTERN.finditer(text):
        node_id = f"N-{match.group(1)}"
        name = match.group(2).strip()
        node_num = int(match.group(1))
        
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

        nt_m = NODE_TYPE_PATTERN.search(section)
        node_type = _parse_node_type_label(
            nt_m.group(1).strip() if nt_m else None,
            node_num,
        )

        topic_kind = None
        tk = TOPIC_KIND_PATTERN.search(section)
        if tk:
            topic_kind = tk.group(1).strip()
        organization_kind = None
        ok = ORG_KIND_PATTERN.search(section)
        if ok:
            organization_kind = ok.group(1).strip()
        place_kind = None
        pk = PLACE_KIND_PATTERN.search(section)
        if pk:
            place_kind = pk.group(1).strip()

        # Extract description (first substantive line after header / type / kinds)
        lines = section.split("\n")
        description = None
        for line in lines:
            line_stripped = line.strip()
            if _is_node_metadata_line(line_stripped):
                continue
            description = line_stripped
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

        row: dict[str, Any] = {
            "id": node_id,
            "name": name,
            "node_type": node_type,
            "description": description,
            "episode_num": episode_num,
            "related_ids": related_ids,
            "confidence": confidence,
            "uncertainty_note": uncertainty_note,
            "declared_aliases": declared_aliases,
        }
        if topic_kind:
            row["topic_kind"] = topic_kind
        if organization_kind:
            row["organization_kind"] = organization_kind
        if place_kind:
            row["place_kind"] = place_kind
        
        nodes.append(row)
    
    return nodes


def extract_legal_matters(text: str, episode_num: int) -> list[dict[str, Any]]:
    matters: list[dict[str, Any]] = []
    for m in LEGAL_MATTER_HEADER.finditer(text):
        lm_id = m.group(1).strip()
        name = m.group(2).strip()
        start = m.end()
        nxt = LEGAL_MATTER_HEADER.search(text, start)
        end = nxt.start() if nxt else len(text)
        section = text[start:end]
        party_nodes: list[str] = []
        pm = LM_PARTY_PATTERN.search(section)
        if pm:
            party_nodes = parse_id_list(pm.group(1))
            party_nodes = [x for x in party_nodes if x.startswith("N-")]
        place_nodes: list[str] = []
        plm = LM_PLACE_PATTERN.search(section)
        if plm:
            place_nodes = parse_id_list(plm.group(1))
            place_nodes = [x for x in place_nodes if x.startswith("N-")]
        arts: list[str] = []
        am = LM_ARTIFACT_PATTERN.search(section)
        if am:
            arts = parse_id_list(am.group(1))
            arts = [x for x in arts if _ID_TOKEN.match(x) and x.startswith("A-")]
        desc = None
        dm = LM_DESC_PATTERN.search(section)
        if dm:
            desc = dm.group(1).strip()
        matters.append(
            {
                "id": lm_id,
                "name": name,
                "description": desc,
                "episode_num": episode_num,
                "party_nodes": party_nodes,
                "place_nodes": place_nodes,
                "artifact_ids": arts,
            }
        )
    return matters


def extract_org_relationship_lines(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in ORG_LINK_PATTERN.finditer(text):
        rel = m.group(2).strip()
        if rel in ORG_REL_TYPES:
            out.append({"from_id": m.group(1), "relation": rel, "to_id": m.group(3)})
    return out


def extract_role_assertion_lines(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in ROLE_LINK_PATTERN.finditer(text):
        title = (m.group(4) or "").strip()
        out.append(
            {
                "person_id": m.group(1).strip(),
                "role_edge": m.group(2).strip(),
                "org_id": m.group(3).strip(),
                "role_title": title,
            }
        )
    return out


def extract_same_as_lines(text: str) -> list[dict[str, str]]:
    return [
        {"a": m.group(1), "b": m.group(2)}
        for m in SAME_AS_LINE_PATTERN.finditer(text)
    ]


def extract_provenance_lines(text: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in PROV_LINE_PATTERN.finditer(text):
        out.append({"from_id": m.group(1), "relation": m.group(2), "to_id": m.group(3)})
    return out


def extract_topic_mention_lines(text: str) -> list[dict[str, str]]:
    return [
        {"claim_id": m.group(1), "topic_id": m.group(2)}
        for m in TOPIC_MENTION_PATTERN.finditer(text)
    ]


def extract_meme_link_lines(text: str) -> list[dict[str, str]]:
    return [
        {"meme_id": m.group(1), "link_type": m.group(2), "target_id": m.group(3)}
        for m in MEME_LINK_PATTERN.finditer(text)
    ]


def extract_meme_nodes(text: str) -> list[dict[str, Any]]:
    """Parse **M-1** (type) term lines in the Meme Register."""
    nodes: list[dict[str, Any]] = []
    for m in MEME_NODE_HEADER.finditer(text):
        nodes.append(
            {
                "id": m.group(1).strip(),
                "meme_type": m.group(2).strip(),
                "canonical_term": m.group(3).strip(),
            }
        )
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
        "legal_matters": extract_legal_matters(text, episode_num),
        "organization_relationships": extract_org_relationship_lines(text),
        "role_assertions": extract_role_assertion_lines(text),
        "node_equivalences": extract_same_as_lines(text),
        "provenance_links": extract_provenance_lines(text),
        "topic_mentions": extract_topic_mention_lines(text),
        "meme_links": extract_meme_link_lines(text),
        "meme_nodes": extract_meme_nodes(text),
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


def resolve_draft_graph_node_id(node_id: str, draft_to_graph: dict[str, str]) -> str:
    """
    Map a §4 ledger N-* id to the Neo4j node id after fuzzy merge.

    `draft_to_graph` is cumulative across episodes in a single ingest run: each
    processed node registers ``draft_to_graph[declared_id] = actual_id`` (equal
    when no merge). Claims and edges still citing the draft id then resolve.
    """
    if not node_id or not isinstance(node_id, str) or not node_id.startswith("N-"):
        return node_id
    return draft_to_graph.get(node_id, node_id)


def resolve_related_graph_node_ids(
    raw_ids: list[str],
    draft_to_graph: dict[str, str],
    graph_node_id_set: set[str],
) -> list[str]:
    """Resolve draft N-* to graph ids, keep only ids present in DB, dedupe order."""
    seen: set[str] = set()
    out: list[str] = []
    for nid in raw_ids:
        g = resolve_draft_graph_node_id(nid, draft_to_graph)
        if g in graph_node_id_set and g not in seen:
            seen.add(g)
            out.append(g)
    return out


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
        "CREATE CONSTRAINT topic_id IF NOT EXISTS FOR (t:Topic) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
        "CREATE CONSTRAINT place_id IF NOT EXISTS FOR (pl:Place) REQUIRE pl.id IS UNIQUE",
        "CREATE CONSTRAINT investigation_target_id IF NOT EXISTS FOR (it:InvestigationTarget) REQUIRE it.id IS UNIQUE",
        "CREATE CONSTRAINT legal_matter_id IF NOT EXISTS FOR (lm:LegalMatter) REQUIRE lm.id IS UNIQUE",
        "CREATE CONSTRAINT meme_id IF NOT EXISTS FOR (m:Meme) REQUIRE m.id IS UNIQUE",
        "CREATE CONSTRAINT episode_num IF NOT EXISTS FOR (e:Episode) REQUIRE e.episode_num IS UNIQUE",
    ]
    for constraint in constraints:
        try:
            tx.run(constraint)
        except Exception as e:
            # Constraint may already exist
            pass


def ingest_episode(
    driver,
    episode_data: dict[str, Any],
    force: bool = False,
    fuzzy_match: bool = True,
    draft_node_id_to_graph_id: dict[str, str] | None = None,
):
    """Ingest a single episode into Neo4j.

    Pass a shared ``draft_node_id_to_graph_id`` dict from ``main()`` so draft
    ledger N-* ids from every episode map to merged graph ids for claims and edges.
    """
    episode_num = episode_data["episode_num"]
    merge_log = []
    if draft_node_id_to_graph_id is None:
        draft_node_id_to_graph_id = {}

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
        
        # Ingest nodes (Person, Topic, Organization, Place, legacy InvestigationTarget)
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
                    draft_node_id_to_graph_id[node_id] = actual_node_id
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
            draft_node_id_to_graph_id[node_id] = node_id

        # Legal matter clusters (artifacts + parties + places)
        for lm in episode_data.get("legal_matters") or []:
            session.run(
                "MERGE (lm:LegalMatter {id: $id}) "
                "SET lm.name = $name, lm.episode_num = $ep, lm.description = $desc",
                id=lm["id"],
                name=lm.get("name") or "",
                ep=lm.get("episode_num", episode_num),
                desc=lm.get("description"),
            )
            session.run(
                "MATCH (lm:LegalMatter {id: $lid}), (e:Episode {episode_num: $ep}) "
                "MERGE (lm)-[:APPEARS_IN]->(e)",
                lid=lm["id"],
                ep=episode_num,
            )
            for aid in lm.get("artifact_ids") or []:
                session.run(
                    "MATCH (a:Artifact {id: $aid}), (lm:LegalMatter {id: $lid}) "
                    "MERGE (a)-[:IN_LEGAL_MATTER]->(lm)",
                    aid=aid,
                    lid=lm["id"],
                )
            for nid in lm.get("party_nodes") or []:
                gnid = resolve_draft_graph_node_id(nid, draft_node_id_to_graph_id)
                session.run(
                    "MATCH (lm:LegalMatter {id: $lid}), (n {id: $nid}) "
                    "WHERE n:Person OR n:Organization OR n:Topic OR n:Place OR n:InvestigationTarget "
                    "MERGE (n)-[:PARTY_IN_MATTER]->(lm)",
                    lid=lm["id"],
                    nid=gnid,
                )
            for nid in lm.get("place_nodes") or []:
                gnid = resolve_draft_graph_node_id(nid, draft_node_id_to_graph_id)
                session.run(
                    "MATCH (lm:LegalMatter {id: $lid}), (n {id: $nid}) "
                    "WHERE n:Place OR n:Topic OR n:Organization OR n:InvestigationTarget "
                    "MERGE (lm)-[:LOCUS_AT]->(n)",
                    lid=lm["id"],
                    nid=gnid,
                )
        
        strict_claims = os.getenv("NEO4J_INGEST_STRICT_CLAIMS", "1").lower() in (
            "1",
            "true",
            "yes",
        )
        artifact_id_set = {
            r["id"] for r in session.run("MATCH (a:Artifact) RETURN a.id AS id")
        }
        graph_node_id_set = {
            r["id"]
            for r in session.run(
                "MATCH (n) WHERE n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget "
                "RETURN n.id AS id"
            )
        }

        ingest_unsubstantiated = os.getenv(
            "NEO4J_INGEST_UNSUBSTANTIATED_CLAIMS", "1"
        ).lower() in ("1", "true", "yes")

        topic_mentions_by_claim: dict[str, list[str]] = {}
        for tm in episode_data.get("topic_mentions") or []:
            cid, tid = tm.get("claim_id"), tm.get("topic_id")
            if cid and tid:
                topic_mentions_by_claim.setdefault(str(cid), []).append(str(tid))

        def topic_mention_targets_resolved(claim_id: str) -> list[str]:
            seen: set[str] = set()
            out: list[str] = []
            for tid in topic_mentions_by_claim.get(claim_id, []):
                gtid = resolve_draft_graph_node_id(tid, draft_node_id_to_graph_id)
                if gtid in graph_node_id_set and gtid not in seen:
                    seen.add(gtid)
                    out.append(gtid)
            return out

        # Ingest claims
        for claim in episode_data["claims"]:
            label = claim.get("label")
            anchored_raw = list(claim.get("anchored_artifacts") or [])
            related_raw = list(claim.get("related_nodes") or [])
            resolved_artifacts = [a for a in anchored_raw if a in artifact_id_set]
            resolved_nodes = resolve_related_graph_node_ids(
                related_raw, draft_node_id_to_graph_id, graph_node_id_set
            )
            resolved_topic_targets = topic_mention_targets_resolved(claim["id"])
            has_entity_connectivity = bool(resolved_nodes) or bool(resolved_topic_targets)

            substantiated: bool
            use_artifacts: list[str]
            use_nodes: list[str]

            if strict_claims:
                if is_placeholder_claim_label(label):
                    merge_log.append(
                        f"  SKIP placeholder claim {claim['id']}: {(label or '')[:70]!r}"
                    )
                    continue
                if resolved_artifacts:
                    if not resolved_nodes:
                        merge_log.append(
                            f"  SKIP claim {claim['id']} (no graph entity node in DB for {related_raw!r})"
                        )
                        continue
                    substantiated = True
                    use_artifacts = resolved_artifacts
                    use_nodes = resolved_nodes
                elif ingest_unsubstantiated and has_entity_connectivity:
                    substantiated = False
                    use_artifacts = []
                    use_nodes = resolved_nodes
                    merge_log.append(
                        f"  INGEST unsubstantiated claim {claim['id']} "
                        f"(no artifact; INVOLVES={len(resolved_nodes)}, "
                        f"TopicMention→resolved={len(resolved_topic_targets)})"
                    )
                else:
                    if not ingest_unsubstantiated and has_entity_connectivity:
                        merge_log.append(
                            f"  SKIP unanchored claim {claim['id']} "
                            f"(NEO4J_INGEST_UNSUBSTANTIATED_CLAIMS=0; "
                            f"would ingest as verbal with INVOLVES/TopicMention only)"
                        )
                    elif not anchored_raw:
                        merge_log.append(
                            f"  SKIP unanchored claim {claim['id']} "
                            f"(no artifact and no INVOLVES/TopicMention connectivity; "
                            f"related={related_raw!r})"
                        )
                    else:
                        merge_log.append(
                            f"  SKIP unanchored claim {claim['id']} "
                            f"(no Artifact in DB for {anchored_raw!r}; "
                            f"no INVOLVES/TopicMention connectivity)"
                        )
                    continue
            else:
                use_artifacts = anchored_raw
                use_nodes = []
                seen_u: set[str] = set()
                for n in related_raw:
                    if isinstance(n, str) and n.startswith("N-"):
                        g = resolve_draft_graph_node_id(n, draft_node_id_to_graph_id)
                        if g not in seen_u:
                            seen_u.add(g)
                            use_nodes.append(g)
                substantiated = bool(
                    [a for a in anchored_raw if a in artifact_id_set]
                )

            contradicts = claim.get("contradicts_claims") or []
            supports = claim.get("supports_claims") or []
            qualifies = claim.get("qualifies_claims") or []
            sens_tags = claim.get("sensitive_topic_tags") or []

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
                    "qualifies_claims",
                    "sensitive_topic_tags",
                )
                and v is not None
            }
            props["anchored_artifact_ids"] = ",".join(resolved_artifacts)
            props["related_node_ids"] = ",".join(use_nodes)
            props["substantiated"] = substantiated
            if sens_tags:
                props["sensitive_topic_tags"] = ",".join(sens_tags)

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
                    "MATCH (n) WHERE n.id = $node_id AND (n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget) "
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
            for other_id in qualifies:
                session.run(
                    "MATCH (c1:Claim {id: $from_id}), (c2:Claim {id: $to_id}) "
                    "MERGE (c1)-[:QUALIFIES]->(c2)",
                    from_id=claim["id"],
                    to_id=other_id,
                )
            if sens_tags:
                for artifact_id in use_artifacts:
                    session.run(
                        "MATCH (c:Claim {id: $cid}), (a:Artifact {id: $aid}) "
                        "MERGE (c)-[:SUPPORTED_BY]->(a)",
                        cid=claim["id"],
                        aid=artifact_id,
                    )

        # Meme nodes (from Meme Register headers)
        for mn in episode_data.get("meme_nodes") or []:
            session.run(
                "MERGE (m:Meme {id: $id}) "
                "SET m.canonical_term = $term, m.meme_type = $mtype, m.episode_num = $ep",
                id=mn["id"],
                term=mn.get("canonical_term") or "",
                mtype=mn.get("meme_type") or "meme",
                ep=episode_num,
            )
            session.run(
                "MATCH (m:Meme {id: $mid}), (e:Episode {episode_num: $ep}) "
                "MERGE (m)-[:APPEARS_IN]->(e)",
                mid=mn["id"],
                ep=episode_num,
            )

        # Organization ↔ organization network (whitelist relation types)
        for row in episode_data.get("organization_relationships") or []:
            rel_key = row.get("relation") or ""
            rt = ORG_REL_TYPES.get(rel_key)
            if not rt:
                continue
            fid = resolve_draft_graph_node_id(row["from_id"], draft_node_id_to_graph_id)
            tid = resolve_draft_graph_node_id(row["to_id"], draft_node_id_to_graph_id)
            session.run(
                f"MATCH (a {{id: $fid}}), (b {{id: $tid}}) "
                f"WHERE (a:Organization OR a:InvestigationTarget) "
                f"AND (b:Organization OR b:InvestigationTarget) "
                f"MERGE (a)-[:{rt}]->(b)",
                fid=fid,
                tid=tid,
            )

        role_map = {"holds_role": "HOLDS_ROLE", "member_of": "MEMBER_OF", "chair_of": "CHAIR_OF"}
        for row in episode_data.get("role_assertions") or []:
            edge = row.get("role_edge") or ""
            rt = role_map.get(edge)
            if not rt:
                continue
            title = row.get("role_title") or ""
            pid = resolve_draft_graph_node_id(row["person_id"], draft_node_id_to_graph_id)
            oid = resolve_draft_graph_node_id(row["org_id"], draft_node_id_to_graph_id)
            session.run(
                f"MATCH (p:Person {{id: $pid}}), (o {{id: $oid}}) "
                f"WHERE o:Organization OR o:InvestigationTarget "
                f"MERGE (p)-[r:{rt}]->(o) SET r.role_title = $title",
                pid=pid,
                oid=oid,
                title=title,
            )

        for row in episode_data.get("node_equivalences") or []:
            a, b = row.get("a"), row.get("b")
            if not a or not b or a == b:
                continue
            ga = resolve_draft_graph_node_id(a, draft_node_id_to_graph_id)
            gb = resolve_draft_graph_node_id(b, draft_node_id_to_graph_id)
            lo, hi = (ga, gb) if ga < gb else (gb, ga)
            session.run(
                "MATCH (x {id: $lo}), (y {id: $hi}) "
                "WHERE x:Person OR x:Topic OR x:Organization OR x:Place OR x:InvestigationTarget "
                "  AND (y:Person OR y:Topic OR y:Organization OR y:Place OR y:InvestigationTarget) "
                "MERGE (x)-[:SAME_AS]->(y)",
                lo=lo,
                hi=hi,
            )

        for pl in episode_data.get("provenance_links") or []:
            fr, to, rel = pl.get("from_id"), pl.get("to_id"), pl.get("relation")
            if not fr or not to or not rel:
                continue
            if rel == "cites_source" and str(fr).startswith("C-"):
                session.run(
                    "MATCH (c:Claim {id: $f}), (a:Artifact {id: $t}) "
                    "MERGE (c)-[:CITES_SOURCE]->(a)",
                    f=fr,
                    t=to,
                )
            elif str(fr).startswith("A-") and str(to).startswith("A-"):
                if rel == "derived_from":
                    rtype = "DERIVED_FROM"
                elif rel == "recording_of":
                    rtype = "RECORDING_OF"
                else:
                    continue
                session.run(
                    f"MATCH (a1:Artifact {{id: $f}}), (a2:Artifact {{id: $t}}) "
                    f"MERGE (a1)-[:{rtype}]->(a2)",
                    f=fr,
                    t=to,
                )

        for tm in episode_data.get("topic_mentions") or []:
            cid, tid = tm.get("claim_id"), tm.get("topic_id")
            if not cid or not tid:
                continue
            gtid = resolve_draft_graph_node_id(tid, draft_node_id_to_graph_id)
            session.run(
                "MATCH (c:Claim {id: $cid}), (t {id: $tid}) "
                "WHERE t:Topic OR t:InvestigationTarget "
                "MERGE (c)-[:MENTIONS_TOPIC]->(t)",
                cid=cid,
                tid=gtid,
            )

        for ml in episode_data.get("meme_links") or []:
            mid, ltype, tid = ml.get("meme_id"), ml.get("link_type"), ml.get("target_id")
            if not mid or not ltype or not tid:
                continue
            if ltype == "invoked_by_claim" and tid.startswith("C-"):
                session.run(
                    "MATCH (c:Claim {id: $tid}), (m:Meme {id: $mid}) "
                    "MERGE (c)-[:INVOKES_MEME]->(m)",
                    tid=tid,
                    mid=mid,
                )
            elif ltype == "invoked_by_speaker" and tid.startswith("N-"):
                gtid = resolve_draft_graph_node_id(tid, draft_node_id_to_graph_id)
                session.run(
                    "MATCH (p:Person {id: $tid}), (m:Meme {id: $mid}) "
                    "MERGE (p)-[:INVOKES_MEME]->(m)",
                    tid=gtid,
                    mid=mid,
                )
            elif ltype == "targets_node" and tid.startswith("N-"):
                gtid = resolve_draft_graph_node_id(tid, draft_node_id_to_graph_id)
                session.run(
                    "MATCH (m:Meme {id: $mid}), (n {id: $tid}) "
                    "WHERE n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget "
                    "MERGE (m)-[:TARGETS_NODE]->(n)",
                    mid=mid,
                    tid=gtid,
                )
        
        # Create INVOLVES relationships from artifacts to nodes (from related_ids)
        for artifact in episode_data["artifacts"]:
            artifact_id = artifact["id"]
            # Re-parse to get related_ids
            for node_id in artifact.get("related_ids", []):
                if node_id.startswith("N-"):
                    gnid = resolve_draft_graph_node_id(node_id, draft_node_id_to_graph_id)
                    session.run(
                        "MATCH (a:Artifact {id: $artifact_id}) "
                        "MATCH (n) WHERE n.id = $node_id AND (n:Person OR n:Topic OR n:Organization OR n:Place OR n:InvestigationTarget) "
                        "MERGE (a)-[:INVOLVES]->(n)",
                        artifact_id=artifact_id,
                        node_id=gnid,
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

    _us = os.getenv("NEO4J_INGEST_UNSUBSTANTIATED_CLAIMS", "1").lower() in (
        "1",
        "true",
        "yes",
    )
    if _us:
        print(
            "[neo4j-ingest] Unsubstantiated claims: ENABLED "
            "(verbal claims with INVOLVES and/or TopicMention; set NEO4J_INGEST_UNSUBSTANTIATED_CLAIMS=0 to skip)"
        )
    else:
        print("[neo4j-ingest] Unsubstantiated claims: DISABLED")

    print(f"[neo4j-ingest] Ingesting {len(episode_files)} episode(s)...")
    draft_node_id_to_graph_id: dict[str, str] = {}

    for i, filepath in enumerate(episode_files, 1):
        print(f"  [{i}/{len(episode_files)}] {filepath.name}")
        try:
            episode_data = parse_episode_file(filepath)
            merge_log = ingest_episode(
                driver,
                episode_data,
                args.force,
                fuzzy_match,
                draft_node_id_to_graph_id,
            )
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
