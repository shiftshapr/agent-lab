#!/usr/bin/env python3
"""
Ingest knowledge base (metaweb_book, Substack, canvas, schema docs, work_log digest) into Neo4j meta-layer graph.

Creates MLSource, MLChunk, MLConcept, MLPrimitive nodes. Parses markdown structure:
- # Headers → MLConcept or section
- ## Subsections → MLChunk with context
- Inline **concepts** or primitive keywords → RELATES_TO

Usage:
  uv run --project framework/deer-flow/backend python scripts/ingest-meta-layer-knowledge.py [--force]
  # Or from agent-lab with neo4j in path:
  python scripts/ingest-meta-layer-knowledge.py [--force]

Environment: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD (from .env). Loads .env from agent-lab root.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
KNOWLEDGE_DIR = AGENT_LAB_ROOT / "knowledge"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")

# Meta-layer primitives (from voice)
ML_PRIMITIVES = [
    "infrastructure", "governance", "coordination", "inscription",
    "trust", "protocol", "layer", "signal", "alignment",
]


def _load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def ensure_schema(driver) -> None:
    """Create constraints and indexes for meta-layer nodes."""
    with driver.session() as session:
        for label, prop in [
            ("MLPrimitive", "name"),
            ("MLConcept", "name"),
            ("MLFramework", "name"),
            ("MLSource", "id"),
            ("MLChunk", "id"),
        ]:
            try:
                session.run(
                    f"CREATE CONSTRAINT ml_{label}_{prop} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
                )
            except Exception:
                pass
        try:
            session.run("CREATE INDEX ml_chunk_text IF NOT EXISTS FOR (n:MLChunk) ON (n.text)")
        except Exception:
            pass


def ensure_primitives(driver) -> None:
    """Ensure MLPrimitive nodes exist for core meta-layer primitives."""
    with driver.session() as session:
        for name in ML_PRIMITIVES:
            session.run(
                """
                MERGE (p:MLPrimitive {name: $name})
                ON CREATE SET p.definition = $name, p.created_at = datetime()
                """,
                name=name.lower(),
            )


def parse_markdown_chunks(path: Path, content: str) -> list[dict]:
    """Parse markdown into chunks with headers as context."""
    chunks = []
    lines = content.split("\n")
    current_header = ""
    current_subheader = ""
    current_text: list[str] = []
    source_name = path.stem

    def flush():
        if current_text:
            text = "\n".join(current_text).strip()
            if text and len(text) > 20:
                chunks.append({
                    "text": text[:8000],  # cap per chunk
                    "header": current_header,
                    "subheader": current_subheader,
                    "source": source_name,
                })
        current_text.clear()

    for line in lines:
        if line.startswith("# "):
            flush()
            current_header = line[2:].strip()
            current_subheader = ""
            current_text = []
        elif line.startswith("## "):
            flush()
            current_subheader = line[3:].strip()
            current_text = []
        elif line.startswith("### "):
            flush()
            current_subheader = line[4:].strip()
            current_text = []
        else:
            current_text.append(line)

    flush()
    return chunks


def source_type_from_path(path: Path) -> str:
    path_str = str(path).lower()
    name = path.stem.lower()
    if "metaweb" in name or "book" in name:
        return "book"
    if "substack" in name:
        return "substack"
    if "canvas" in name:
        return "canvas"
    if "pdf" in path_str or "docs" in path_str:
        return "document"
    if "url" in path_str or "urls" in path_str:
        return "url"
    return "knowledge"


def ingest_file(driver, path: Path, force: bool = False) -> int:
    """Ingest a single knowledge file. Returns count of chunks created."""
    if not path.exists():
        return 0
    content = path.read_text(encoding="utf-8").strip()
    if not content or content == "Add key concepts" or "placeholder" in content.lower():
        return 0  # Skip placeholders

    source_id = f"source:{path.relative_to(KNOWLEDGE_DIR)}"
    source_type = source_type_from_path(path)

    with driver.session() as session:
        session.run(
            """
            MERGE (s:MLSource {id: $id})
            ON CREATE SET s.name = $name, s.source_type = $type, s.path = $path, s.created_at = datetime()
            ON MATCH SET s.updated_at = datetime()
            """,
            id=source_id,
            name=path.stem,
            type=source_type,
            path=str(path.relative_to(AGENT_LAB_ROOT)),
        )

    chunks = parse_markdown_chunks(path, content)
    created = 0
    with driver.session() as session:
        for i, c in enumerate(chunks):
            chunk_id = f"{source_id}:chunk:{i}"
            result = session.run(
                """
                MERGE (chunk:MLChunk {id: $id})
                ON CREATE SET
                    chunk.text = $text,
                    chunk.header = $header,
                    chunk.subheader = $subheader,
                    chunk.chunk_type = 'excerpt',
                    chunk.source_name = $source_name,
                    chunk.created_at = datetime()
                ON MATCH SET
                    chunk.text = $text,
                    chunk.header = $header,
                    chunk.subheader = $subheader,
                    chunk.updated_at = datetime()
                WITH chunk
                MATCH (s:MLSource {id: $source_id})
                MERGE (s)-[:CONTAINS]->(chunk)
                RETURN chunk
                """,
                id=chunk_id,
                text=c["text"],
                header=c["header"] or "",
                subheader=c["subheader"] or "",
                source_name=c["source"],
                source_id=source_id,
            )
            if result.single():
                created += 1

    return created


def clear_meta_layer_graph(driver) -> None:
    """Remove all ML* nodes and relationships. Preserves Bride of Charlie data."""
    with driver.session() as session:
        session.run("""
            MATCH (n)
            WHERE n:MLSource OR n:MLChunk OR n:MLConcept OR n:MLFramework
               OR n:MLPrimitive OR n:MLProject OR n:MLEntity
            DETACH DELETE n
        """)


def main() -> int:
    _load_env()
    if not KNOWLEDGE_DIR.exists():
        print(f"[meta-layer-ingest] Knowledge dir not found: {KNOWLEDGE_DIR}")
        return 1

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: Could not connect to Neo4j: {e}")
        print("Run: docker compose up -d")
        return 1

    force = "--force" in sys.argv or "-f" in sys.argv
    single_file = None
    for i, a in enumerate(sys.argv):
        if a == "--file" and i + 1 < len(sys.argv):
            single_file = Path(sys.argv[i + 1])
            if not single_file.is_absolute():
                single_file = AGENT_LAB_ROOT / single_file
            break

    if force and not single_file:
        print("[meta-layer-ingest] Clearing meta-layer graph...")
        clear_meta_layer_graph(driver)

    ensure_schema(driver)
    ensure_primitives(driver)

    # Ingest knowledge files
    if single_file:
        files = [single_file] if single_file.exists() else []
    else:
        files = [
            KNOWLEDGE_DIR / "metaweb_book.md",
            KNOWLEDGE_DIR / "substack_highlights.md",
            KNOWLEDGE_DIR / "canvas_insights.md",
        ]
        for extra in (
            KNOWLEDGE_DIR / "meta_layer_schema.md",
            KNOWLEDGE_DIR / "pacha_schema.md",
            KNOWLEDGE_DIR / "work_log_digest.md",
        ):
            if extra.exists():
                files.append(extra)
        docs_dir = KNOWLEDGE_DIR / "docs"
        urls_dir = KNOWLEDGE_DIR / "urls"
        if docs_dir.exists():
            files.extend(docs_dir.glob("*.md"))
        if urls_dir.exists():
            files.extend(urls_dir.glob("*.md"))

    total = 0
    for path in files:
        if path.exists():
            n = ingest_file(driver, path)
            total += n
            if n > 0:
                print(f"  {path.name}: {n} chunk(s)")

    driver.close()
    print(f"[meta-layer-ingest] Done. {total} chunk(s) in graph.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
