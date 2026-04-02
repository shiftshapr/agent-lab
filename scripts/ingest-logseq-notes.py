#!/usr/bin/env python3
"""
Ingest Logseq notes into meta-layer graph: parse, clean, categorize, extract insights/ideas/dreams/themes.

Logseq format: pages/*.md (frontmatter + bullet blocks), journals/YYYY_MM_DD.md.

Usage:
  uv run --project framework/deer-flow/backend python scripts/ingest-logseq-notes.py
  uv run --project framework/deer-flow/backend python scripts/ingest-logseq-notes.py --logseq-dir ~/path/to/logseq
  uv run --project framework/deer-flow/backend python scripts/ingest-logseq-notes.py --ingest-only   # Skip LLM enrichment

Environment: NEO4J_*, MINIMAX_API_KEY or Ollama (from .env).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent
KNOWLEDGE_DIR = AGENT_LAB_ROOT / "knowledge"
CONTEXT_PATH = AGENT_LAB_ROOT / "data" / "shiftshapr_context.json"

# Default: user's Logseq graph in iCloud
DEFAULT_LOGSEQ = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Documents/daveed"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")
MAX_CHARS_PER_BATCH = int(os.getenv("ENRICH_MAX_CHARS", "50000"))


def _load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def _load_user_context() -> dict:
    if not CONTEXT_PATH.exists():
        return {}
    try:
        return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---- Logseq parser ----

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter, return (props, body)."""
    if not content.strip().startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    front = parts[1].strip()
    body = parts[2].strip()
    props = {}
    for line in front.split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            props[k.strip().lower()] = v.strip().strip('"\'')
    return props, body


def _parse_blocks(text: str) -> list[dict]:
    """Parse Logseq bullet blocks. Returns list of {text, depth, markers}."""
    blocks = []
    for line in text.split("\n"):
        stripped = line.lstrip("\t")
        depth = len(line) - len(stripped)
        content = stripped.lstrip("- ").strip()
        if not content:
            continue
        markers = []
        if content.startswith("DONE "):
            markers.append("DONE")
            content = content[5:].strip()
        elif content.startswith("TODO "):
            markers.append("TODO")
            content = content[5:].strip()
        elif content.startswith("LATER "):
            markers.append("LATER")
            content = content[6:].strip()
        elif content.startswith("DOING "):
            markers.append("DOING")
            content = content[6:].strip()
        blocks.append({"text": content, "depth": depth, "markers": markers})
    return blocks


def _clean_block_text(text: str) -> str:
    """Normalize block text: fix [[links]], #tags, trim."""
    # Normalize [[page name]] to readable
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # Normalize #[[tag]] to #tag
    text = re.sub(r"#\[\[([^\]]+)\]\]", r"#\1", text)
    return text.strip()


def _extract_tags(text: str) -> list[str]:
    """Extract #tag and #[[tag]] from text."""
    tags = set()
    for m in re.finditer(r"#(?:\[\[)?([^\s\]\]#]+)\]?\]?", text):
        tags.add(m.group(1).strip())
    return list(tags)


def _extract_page_refs(text: str) -> list[str]:
    """Extract [[page]] references."""
    return [m.group(1).strip() for m in re.finditer(r"\[\[([^\]]+)\]\]", text)]


def _parse_date_from_item(path: Path, name: str, source_type: str, props: dict) -> str | None:
    """Extract ISO date (YYYY-MM-DD) from journal name, page frontmatter, or file mtime."""
    if source_type == "journal":
        # Journal: name is 2020-11-13 (from stem) or path stem 2020_11_13
        stem = path.stem
        m = re.match(r"(\d{4})[-_](\d{2})[-_](\d{2})", stem)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    for key in ("created_at", "created", "date", "updated_at", "updated"):
        val = props.get(key)
        if val:
            # Parse common formats: 2020-11-13, 2020-11-13T12:00:00
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(val))
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    try:
        mtime = path.stat().st_mtime
        from datetime import datetime, timezone
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def collect_logseq_content(logseq_dir: Path, limit: int | None = None, pages_only: bool = False) -> list[dict]:
    """
    Collect all pages and journals. Returns list of {
        path, name, source_type (page|journal), content, blocks, props, date
    }.
    """
    results = []
    pages_dir = logseq_dir / "pages"
    journals_dir = logseq_dir / "journals"

    def add_file(path: Path, source_type: str, name: str) -> None:
        if limit is not None and len(results) >= limit:
            return
        if not path.exists():
            return
        try:
            raw = path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            return
        if len(raw) < 10:
            return
        props, body = _parse_frontmatter(raw)
        title = props.get("title") or name
        blocks = _parse_blocks(body)
        cleaned_blocks = []
        for b in blocks:
            ct = _clean_block_text(b["text"])
            if len(ct) >= 3:
                cleaned_blocks.append({
                    **b,
                    "text": ct,
                    "tags": _extract_tags(b["text"]),
                    "refs": _extract_page_refs(b["text"]),
                })
        content = "\n".join(b["text"] for b in cleaned_blocks)
        if len(content) < 20:
            return
        date_str = _parse_date_from_item(path, name, source_type, props)
        results.append({
            "path": path,
            "name": name,
            "title": title,
            "source_type": source_type,
            "content": content,
            "blocks": cleaned_blocks,
            "props": props,
            "date": date_str,
        })

    if pages_dir.exists():
        for f in pages_dir.glob("*.md"):
            add_file(f, "page", f.stem)
            if limit is not None and len(results) >= limit:
                break
    if journals_dir.exists() and not pages_only:
        for f in sorted(journals_dir.glob("*.md")):
            # 2020_11_13 -> 2020-11-13
            name = f.stem.replace("_", "-")
            add_file(f, "journal", name)
            if limit is not None and len(results) >= limit:
                break

    return results


def chunk_for_enrichment(items: list[dict], max_chars: int = 12000) -> list[dict]:
    """Group items into batches for LLM enrichment. Preserve context (title, date)."""
    batches = []
    current = []
    current_len = 0
    for item in items:
        header = f"[{item['source_type'].upper()}] {item['title']} ({item['name']})\n\n"
        block_texts = [b["text"] for b in item["blocks"]]
        text = header + "\n".join(block_texts)
        if current_len + len(text) > max_chars and current:
            batches.append({"items": current, "text": "\n\n---\n\n".join(i.get("_chunk_text", "") for i in current)})
            current = []
            current_len = 0
        item["_chunk_text"] = text
        current.append(item)
        current_len += len(text)
    if current:
        batches.append({"items": current, "text": "\n\n---\n\n".join(i.get("_chunk_text", "") for i in current)})
    return batches


# ---- Neo4j ingest ----

def clear_logseq_from_graph(driver) -> None:
    """Remove logseq sources, their chunks, and nodes that only emerge from them (insights, ideas, dreams)."""
    with driver.session() as session:
        # Delete EMERGES_FROM from themes/tags to logseq sources (keep the node)
        session.run("""
            MATCH (t)-[r:EMERGES_FROM]->(s:MLSource)
            WHERE s.id STARTS WITH 'source:logseq/'
            DELETE r
        """)
        # Delete analysis-layer nodes that emerge from logseq (current labels + legacy ML* from pre-migration)
        session.run("""
            MATCH (x)-[r:EMERGES_FROM]->(s:MLSource)
            WHERE s.id STARTS WITH 'source:logseq/' AND (
                x:Insight OR x:Idea OR x:Dream OR x:Opportunity OR x:Milestone
                OR x:MLInsight OR x:MLIdea OR x:MLDream OR x:MLOpportunity OR x:MLMilestone
            )
            DELETE r, x
        """)
        # Delete chunks and their TAGGED_WITH; then delete sources
        session.run("""
            MATCH (s:MLSource)-[:CONTAINS]->(c:MLChunk)
            WHERE s.id STARTS WITH 'source:logseq/'
            DETACH DELETE c
        """)
        session.run("""
            MATCH (s:MLSource) WHERE s.id STARTS WITH 'source:logseq/'
            DETACH DELETE s
        """)


def ensure_schema(driver) -> None:
    with driver.session() as session:
        for label, prop in [
            ("MLSource", "id"),
            ("MLChunk", "id"),
            ("Insight", "id"),
            ("Idea", "id"),
            ("Dream", "id"),
            ("Theme", "name"),
            ("Opportunity", "id"),
            ("Milestone", "id"),
            ("MLTag", "name"),
        ]:
            try:
                session.run(
                    f"CREATE CONSTRAINT ml_{label}_{prop} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
                )
            except Exception:
                pass


def ingest_to_neo4j(driver, items: list[dict], base_path: Path) -> int:
    """Create MLSource + MLChunk + MLTag (from Logseq tags/refs) + Dream (from [[Dream]] blocks) per item. Returns total node/rel creations."""
    created = 0
    for item in items:
        rel = item["path"].relative_to(base_path)
        source_id = f"source:logseq/{rel}"
        date_str = item.get("date")
        all_tags_refs = set()
        dream_blocks = []

        blocks = item["blocks"]
        for bi, b in enumerate(blocks):
            for t in b.get("tags") or []:
                all_tags_refs.add((t, "hashtag"))
            for r in b.get("refs") or []:
                all_tags_refs.add((r, "ref"))
                if r.lower() == "dream":
                    # Include child blocks (Logseq outline: dream content often in children)
                    depth0 = b.get("depth", 0)
                    parts = [b["text"]]
                    for bj in range(bi + 1, len(blocks)):
                        if blocks[bj].get("depth", 0) <= depth0:
                            break
                        parts.append(blocks[bj]["text"])
                    dream_blocks.append("\n".join(parts))

        with driver.session() as session:
            session.run(
                """
                MERGE (s:MLSource {id: $id})
                ON CREATE SET s.name = $name, s.source_type = $type, s.path = $path, s.source_date = $date, s.created_at = datetime()
                ON MATCH SET s.updated_at = datetime(), s.source_date = COALESCE($date, s.source_date)
                """,
                id=source_id,
                name=item["title"],
                type=f"logseq_{item['source_type']}",
                path=str(rel),
                date=date_str or "",
            )
            # Include all blocks (parent + children) so we retain full outline content
            full_text = "\n".join(b["text"] for b in item["blocks"])
            # Neo4j RANGE index on MLChunk.text has ~8KB limit; split long content into multiple chunks
            MAX_CHUNK_CHARS = 7000  # stay under 8KB index limit
            chunk_texts = []
            if len(full_text) <= MAX_CHUNK_CHARS:
                chunk_texts = [full_text]
            else:
                remainder = full_text
                while remainder:
                    if len(remainder) <= MAX_CHUNK_CHARS:
                        chunk_texts.append(remainder)
                        break
                    split_at = remainder.rfind("\n", 0, MAX_CHUNK_CHARS + 1)
                    if split_at <= 0:
                        split_at = MAX_CHUNK_CHARS
                    chunk_texts.append(remainder[:split_at].rstrip())
                    remainder = remainder[split_at:].lstrip("\n")

            chunk_ids = []
            for ci, chunk_text in enumerate(chunk_texts):
                chunk_id = f"{source_id}:chunk:{ci}"
                chunk_ids.append(chunk_id)
                session.run(
                    """
                    MERGE (c:MLChunk {id: $id})
                    ON CREATE SET c.text = $text, c.chunk_type = 'logseq_note', c.source_name = $name, c.source_date = $date, c.created_at = datetime()
                    ON MATCH SET c.text = $text, c.source_date = COALESCE($date, c.source_date), c.updated_at = datetime()
                    WITH c
                    MATCH (s:MLSource {id: $sid})
                    MERGE (s)-[:CONTAINS]->(c)
                    """,
                    id=chunk_id,
                    text=chunk_text,
                    name=item["title"],
                    date=date_str or "",
                    sid=source_id,
                )
                created += 1

            # Persist Logseq tags/refs as MLTag, link TAGGED_WITH to all chunks from this source
            for tag_name, tag_src in all_tags_refs:
                if not tag_name or len(tag_name) > 200:
                    continue
                for chunk_id in chunk_ids:
                    session.run(
                        """
                        MERGE (t:MLTag {name: $name})
                        ON CREATE SET t.tag_type = $ttype, t.source_date = $date, t.created_at = datetime()
                        ON MATCH SET t.updated_at = datetime(), t.source_date = COALESCE($date, t.source_date)
                        WITH t
                        MATCH (c:MLChunk {id: $chunk_id})
                        MERGE (c)-[:TAGGED_WITH]->(t)
                        """,
                        name=tag_name,
                        ttype=tag_src,
                        date=date_str or "",
                        chunk_id=chunk_id,
                    )
                    created += 1

            # [[Dream]]-tagged blocks → Dream (literal overnight dreams only)
            for i, dream_text in enumerate(dream_blocks):
                if len(dream_text.strip()) < 10:
                    continue
                dream_id = f"dream:logseq/{rel}:{i}"
                name = (dream_text[:150] + "…") if len(dream_text) > 150 else dream_text
                session.run(
                    """
                    MERGE (d:Dream {id: $id})
                    ON CREATE SET d.name = $name, d.summary = $summary, d.source_date = $date, d.dream_type = 'literal', d.created_at = datetime()
                    ON MATCH SET d.updated_at = datetime(), d.source_date = COALESCE($date, d.source_date), d.name = $name, d.summary = $summary
                    WITH d
                    MATCH (s:MLSource {id: $sid})
                    MERGE (d)-[:EMERGES_FROM]->(s)
                    """,
                    id=dream_id,
                    name=name[:200],
                    summary=dream_text[:2000],
                    date=date_str or "",
                    sid=source_id,
                )
                created += 1

    return created


# ---- LLM extraction for notes ----

NOTES_EXTRACTION_PROMPT = """You are analyzing personal notes (Logseq pages and journals) for a user's meta-layer world model.

User context: {user_context}

Extract structured data. Return ONLY valid JSON, no markdown or explanation.

{{
  "insights": [{{"name": "...", "summary": "...", "evidence": "..."}}],
  "ideas": [
    {{"name": "...", "idea_type": "project|experiment|thought_experiment|inscription|article|workshop|other", "description": "...", "evidence": "..."}}
  ],
  "themes": [{{"name": "...", "description": "...", "frequency": "recurring|occasional|single"}}],
  "opportunities": [{{"what": "...", "type": "alignment|collaboration|promotion", "evidence": "..."}}],
  "milestones": [{{"name": "...", "description": "...", "evidence": "..."}}],
  "smart_tags": [{{"name": "...", "tag_type": "topic|project|person|place|concept", "description": "..."}}]
}}

Rules:
- insights: Non-obvious realizations, learnings, "aha" moments
- ideas: Actionable or explorable—projects, experiments, articles, workshops, inscriptions, thought experiments
- themes: Recurring topics across notes (e.g. "digital sovereignty", "collective intelligence")
- opportunities: Alignment, collaboration, or promotion signals
- milestones: Progress markers, goals reached, key events
- smart_tags: Semantic categories to complement the user's own # and [[ ]] tags
- Do NOT extract "dreams"—the user tags those explicitly with [[Dream]] for literal overnight dreams
- Be concise. Max 12 insights, 15 ideas, 10 themes, 8 opportunities, 8 milestones, 15 smart_tags.
"""


def _get_llm():
    from langchain_openai import ChatOpenAI

    if os.getenv("MINIMAX_API_KEY"):
        return ChatOpenAI(
            model=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"),
            base_url="https://api.minimax.io/v1",
            api_key=os.getenv("MINIMAX_API_KEY"),
            temperature=0.2,
            max_tokens=8192,
        )
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "qwen2.5:7b"),
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "fake"),
        temperature=0.2,
        max_tokens=8192,
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
        raise


def _write_notes_extractions(driver, data: dict, source_ids: list[str], source_dates: list[str] | None = None) -> tuple[int, dict]:
    """Write Insight, Idea, Dream, Theme, Opportunity, Milestone, MLTag and link to sources. source_dates: optional list of dates (YYYY-MM-DD) per source."""
    count = 0
    summary = {"insights": [], "ideas": [], "dreams": [], "themes": [], "opportunities": [], "milestones": [], "tags": []}
    base_id = hash(",".join(source_ids)) % 100000
    dates = [d for d in (source_dates or []) if d]
    earliest_date = min(dates) if dates else None

    with driver.session() as session:
        for i, x in enumerate(data.get("insights") or []):
            oid = f"insight_{base_id}_{i}"
            name = (x.get("name") or x.get("summary") or "Insight")[:200]
            session.run(
                """
                MERGE (n:Insight {id: $id})
                ON CREATE SET n.name = $name, n.summary = $summary, n.evidence = $ev, n.source_date = $date, n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime(), n.source_date = COALESCE($date, n.source_date)
                """,
                id=oid,
                name=name,
                summary=(x.get("summary") or "")[:500],
                ev=(x.get("evidence") or "")[:500],
                date=earliest_date or "",
            )
            for sid in source_ids:
                try:
                    session.run(
                        "MATCH (i:Insight {id: $iid}), (s:MLSource {id: $sid}) MERGE (i)-[:EMERGES_FROM]->(s)",
                        iid=oid,
                        sid=sid,
                    )
                except Exception:
                    pass
            count += 1
            summary["insights"].append(name[:60])

        for i, x in enumerate(data.get("ideas") or []):
            oid = f"idea_{base_id}_{i}"
            name = (x.get("name") or x.get("description") or "Idea")[:200]
            itype = x.get("idea_type") or "other"
            if itype not in ("project", "experiment", "thought_experiment", "inscription", "article", "workshop", "other"):
                itype = "other"
            session.run(
                """
                MERGE (n:Idea {id: $id})
                ON CREATE SET n.name = $name, n.idea_type = $itype, n.description = $desc, n.evidence = $ev, n.status = 'open', n.source_date = $date, n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime(), n.source_date = COALESCE($date, n.source_date)
                """,
                id=oid,
                name=name,
                itype=itype,
                desc=(x.get("description") or "")[:500],
                ev=(x.get("evidence") or "")[:500],
                date=earliest_date or "",
            )
            for sid in source_ids:
                try:
                    session.run(
                        "MATCH (i:Idea {id: $iid}), (s:MLSource {id: $sid}) MERGE (i)-[:EMERGES_FROM]->(s)",
                        iid=oid,
                        sid=sid,
                    )
                except Exception:
                    pass
            count += 1
            summary["ideas"].append(f"{itype}: {name[:50]}")

        # Dreams: only from user's [[Dream]] tag (handled in ingest_to_neo4j), not LLM

        for i, x in enumerate(data.get("themes") or []):
            name = (x.get("name") or "Theme")[:200]
            session.run(
                """
                MERGE (n:Theme {name: $name})
                ON CREATE SET n.description = $desc, n.frequency = $freq, n.source_date = $date, n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime(), n.source_date = COALESCE($date, n.source_date)
                """,
                name=name,
                desc=(x.get("description") or "")[:500],
                freq=(x.get("frequency") or "occasional")[:20],
                date=earliest_date or "",
            )
            for sid in source_ids:
                try:
                    session.run(
                        "MATCH (t:Theme {name: $name}), (s:MLSource {id: $sid}) MERGE (t)-[:EMERGES_FROM]->(s)",
                        name=name,
                        sid=sid,
                    )
                except Exception:
                    pass
            count += 1
            summary["themes"].append(name[:60])

        for i, x in enumerate(data.get("opportunities") or []):
            oid = f"opp_{base_id}_{i}"
            what = (x.get("what") or "Opportunity")[:200]
            otype = (x.get("type") or "collaboration")[:30]
            if otype not in ("alignment", "collaboration", "promotion"):
                otype = "collaboration"
            session.run(
                """
                MERGE (n:Opportunity {id: $id})
                ON CREATE SET n.type = $otype, n.description = $desc, n.evidence = $ev, n.source_date = $date, n.source_id = $sid, n.status = 'open', n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime(), n.source_date = COALESCE($date, n.source_date)
                """,
                id=oid,
                otype=otype,
                desc=what,
                ev=(x.get("evidence") or "")[:500],
                date=earliest_date or "",
                sid=source_ids[0] if source_ids else "",
            )
            for sid in source_ids:
                try:
                    session.run(
                        "MATCH (o:Opportunity {id: $oid}), (s:MLSource {id: $sid}) MERGE (o)-[:EMERGES_FROM]->(s)",
                        oid=oid,
                        sid=sid,
                    )
                except Exception:
                    pass
            count += 1
            summary["opportunities"].append(f"{otype}: {what[:50]}")

        for i, x in enumerate(data.get("milestones") or []):
            mid = f"milestone_{base_id}_{i}"
            name = (x.get("name") or x.get("description") or "Milestone")[:200]
            session.run(
                """
                MERGE (n:Milestone {id: $id})
                ON CREATE SET n.name = $name, n.description = $desc, n.evidence = $ev, n.source_date = $date, n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime(), n.source_date = COALESCE($date, n.source_date)
                """,
                id=mid,
                name=name,
                desc=(x.get("description") or "")[:500],
                ev=(x.get("evidence") or "")[:500],
                date=earliest_date or "",
            )
            for sid in source_ids:
                try:
                    session.run(
                        "MATCH (m:Milestone {id: $mid}), (s:MLSource {id: $sid}) MERGE (m)-[:EMERGES_FROM]->(s)",
                        mid=mid,
                        sid=sid,
                    )
                except Exception:
                    pass
            count += 1
            summary["milestones"].append(name[:60])

        for i, x in enumerate(data.get("smart_tags") or []):
            name = (x.get("name") or "Tag")[:200]
            ttype = (x.get("tag_type") or "topic")[:20]
            session.run(
                """
                MERGE (n:MLTag {name: $name})
                ON CREATE SET n.tag_type = $ttype, n.description = $desc, n.source_date = $date, n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime(), n.source_date = COALESCE($date, n.source_date)
                """,
                name=name,
                ttype=ttype,
                desc=(x.get("description") or "")[:300],
                date=earliest_date or "",
            )
            count += 1
            summary["tags"].append(name[:60])

    return count, summary


# ---- Main ----

def main() -> int:
    _load_env()
    logseq_dir = DEFAULT_LOGSEQ
    ingest_only = False
    limit = None
    pages_only = False
    clear_logseq = False
    for i, a in enumerate(sys.argv):
        if a == "--logseq-dir" and i + 1 < len(sys.argv):
            logseq_dir = Path(sys.argv[i + 1]).expanduser().resolve()
        elif a == "--ingest-only":
            ingest_only = True
        elif a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
        elif a == "--pages-only":
            pages_only = True
        elif a == "--clear-logseq":
            clear_logseq = True

    if not logseq_dir.exists():
        print(f"Logseq dir not found: {logseq_dir}", file=sys.stderr)
        print("Usage: python scripts/ingest-logseq-notes.py [--logseq-dir PATH] [--ingest-only]", file=sys.stderr)
        return 1

    items = collect_logseq_content(logseq_dir, limit=limit, pages_only=pages_only)
    print(f"Collected {len(items)} note files from {logseq_dir}", file=sys.stderr)

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        print(f"Neo4j connection failed: {e}", file=sys.stderr)
        return 1

    ensure_schema(driver)
    if clear_logseq:
        print("Clearing existing logseq nodes from graph...", file=sys.stderr)
        clear_logseq_from_graph(driver)
    n_nodes = ingest_to_neo4j(driver, items, logseq_dir)
    print(f"Ingested {len(items)} sources ({n_nodes} nodes: chunks, tags, dreams)", file=sys.stderr)

    if ingest_only:
        driver.close()
        print("NODES: (ingest only, no enrichment)", file=sys.stderr)
        return 0

    # Enrich with LLM
    ctx = _load_user_context()
    user_ctx = f"meta_layer_lens: {ctx.get('meta_layer_lens', '')}. key_projects: {ctx.get('key_projects', [])}"
    batches = chunk_for_enrichment(items)
    llm = _get_llm()
    total_enriched = 0
    all_summary = {"insights": [], "ideas": [], "dreams": [], "themes": [], "tags": []}

    from langchain_core.messages import SystemMessage, HumanMessage

    for bi, batch in enumerate(batches):
        if len(batch["text"]) < 100:
            continue
        print(f"  Enriching batch {bi + 1}/{len(batches)} ({len(batch['text'])} chars)...", file=sys.stderr)
        prompt = NOTES_EXTRACTION_PROMPT.format(user_context=user_ctx)
        messages = [
            SystemMessage(content="You extract structured data from personal notes. Return only valid JSON."),
            HumanMessage(content=f"{prompt}\n\n---\n\nContent:\n\n{batch['text'][:60000]}"),
        ]
        try:
            resp = llm.invoke(messages)
            text = resp.content if hasattr(resp, "content") else str(resp)
            data = _extract_json(text)
            source_ids = [f"source:logseq/{item['path'].relative_to(logseq_dir)}" for item in batch["items"]]
            source_dates = [item.get("date") or "" for item in batch["items"]]
            n, summary = _write_notes_extractions(driver, data, source_ids, source_dates)
            total_enriched += n
            for k in all_summary:
                all_summary[k].extend(summary.get(k, []))
        except Exception as e:
            print(f"  Enrich batch {bi + 1} failed: {e}", file=sys.stderr)

    driver.close()

    print(f"\n[ingest-logseq] Done. {len(items)} sources, {n_nodes} ingest nodes, {total_enriched} LLM-enriched nodes.", file=sys.stderr)
    print("NODES:", file=sys.stderr)
    for k in ("insights", "ideas", "dreams", "themes", "opportunities", "milestones", "tags"):
        v = all_summary.get(k, [])
        if v:
            uniq = list(dict.fromkeys(v))[:10]
            print(f"  {k}: {', '.join(uniq)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
