"""
Meta-layer graph retrieval — query Neo4j for relevant chunks, concepts, primitives.

Used by Shiftshapr to inject context when the user's prompt relates to meta-layer
content. Falls back to file-based knowledge if Neo4j unavailable.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_DIR = AGENT_LAB_ROOT / "knowledge"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")
META_LAYER_RETRIEVAL_MAX_CHARS = int(os.getenv("META_LAYER_RETRIEVAL_MAX_CHARS", "12000"))


def _get_driver():
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        return driver
    except Exception:
        return None


def extract_keywords(text: str, max_words: int = 10) -> list[str]:
    """Extract likely search terms (skip stopwords)."""
    stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during"}
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return [w for w in words if w not in stop][:max_words]


def retrieve(query: str | None, max_chars: int | None = None) -> str:
    """
    Retrieve relevant meta-layer content from Neo4j.

    If query is provided, uses keyword matching on chunk text and header.
    Also returns MLPrimitive and MLConcept nodes for grounding.
    Falls back to empty string if Neo4j unavailable.
    """
    max_chars = max_chars or META_LAYER_RETRIEVAL_MAX_CHARS
    driver = _get_driver()
    if not driver:
        return ""

    keywords = extract_keywords(query or "") if query else []
    chunks = []

    try:
        with driver.session() as session:
            # Always include primitives (short, grounding)
            prim_result = session.run(
                "MATCH (p:MLPrimitive) RETURN p.name AS name, p.definition AS def LIMIT 20"
            )
            prims = [f"- {r['name']}" for r in prim_result if r["name"]]
            if prims:
                chunks.append("**Meta-layer primitives:**\n" + "\n".join(prims))

            # If we have keywords, search chunks (any keyword match)
            if keywords:
                conditions = " OR ".join(
                    f"toLower(c.text) CONTAINS $k{i}" for i in range(len(keywords))
                )
                params = {f"k{i}": kw for i, kw in enumerate(keywords)}
                params["limit"] = 15
                result = session.run(
                    f"""
                    MATCH (s:MLSource)-[:CONTAINS]->(c:MLChunk)
                    WHERE {conditions}
                    RETURN c.text AS text, c.header AS header, c.subheader AS subheader, s.name AS source
                    LIMIT $limit
                    """,
                    params,
                )
                for r in result:
                    header = f"### {r['header']}" if r["header"] else ""
                    if r["subheader"]:
                        header += f" / {r['subheader']}"
                    block = f"{header}\n\n{r['text'][:2000]}" if header else r["text"][:2000]
                    chunks.append(block)
            else:
                # No query: return a sample of chunks (recent or diverse)
                result = session.run(
                    """
                    MATCH (s:MLSource)-[:CONTAINS]->(c:MLChunk)
                    RETURN c.text AS text, c.header AS header, c.subheader AS subheader, s.name AS source
                    ORDER BY c.created_at DESC
                    LIMIT 8
                    """
                )
                for r in result:
                    header = f"### {r['header']}" if r["header"] else ""
                    if r["subheader"]:
                        header += f" / {r['subheader']}"
                    block = f"{header}\n\n{r['text'][:1500]}" if header else r["text"][:1500]
                    chunks.append(block)

        driver.close()
    except Exception:
        return ""

    if not chunks:
        return ""

    combined = "\n\n---\n\n".join(chunks)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "\n\n[... truncated]"
    return "**Meta-layer world model** (from graph):\n\n" + combined
