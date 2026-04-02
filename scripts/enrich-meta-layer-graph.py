#!/usr/bin/env python3
"""
Enrich meta-layer graph: analysis layer (always) + meta-layer mapping (when --meta-layer).

Analysis layer (applied to everything): Dream, Opportunity, Insight, Idea, Theme, Milestone.
Meta-layer mapping (when --meta-layer): MLConcept, MLPrimitive, MLFramework, MLOrg, etc.
Use "add to graph" = analysis only. Use "add to meta-layer" = analysis + meta-layer mapping.

Usage:
  uv run python scripts/enrich-meta-layer-graph.py --file knowledge/urls/foo.md
  uv run python scripts/enrich-meta-layer-graph.py --file knowledge/docs/metaweb_book.md --meta-layer
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
LEDGER_PATH = AGENT_LAB_ROOT / "data" / "opportunities.json"

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


EXTRACTION_PROMPT = """You are analyzing content (article, report, book excerpt) for a user's meta-layer world model.

User interests (use for alignment): {user_context}

Extract structured data. Return ONLY valid JSON, no markdown or explanation.

{{
  "orgs": [{{"name": "...", "url": "...", "type": "..."}}],
  "reports": [{{"name": "...", "url": "...", "author_org": "...", "summary": "..."}}],
  "concepts": [{{"name": "...", "definition": "..."}}],
  "entities": [{{"name": "...", "type": "person|org|coalition|policymaker"}}],
  "relationships": [{{"from": "name", "to": "name", "type": "PUBLISHED|DISCUSSES|ADDRESSES|COLLABORATES_WITH|PART_OF|DERIVES_FROM"}}],
  "opportunities": {{
    "alignment": [{{"what": "...", "why": "...", "evidence": "..."}}],
    "collaboration": [{{"what": "...", "how": "...", "evidence": "..."}}],
    "promotion": [{{"angle": "...", "format": "substack|podcast|talk", "evidence": "..."}}]
  }}
}}

Rules:
- Only include what is clearly supported by the text.
- Names must match exactly in relationships (from/to).
- Be concise. Max 15 concepts, 10 orgs, 10 entities.
- For books: extract key themes, orgs, and opportunity signals.
"""

ANALYSIS_PROMPT = """Extract analysis-layer nodes. Return ONLY valid JSON.

{{
  "insights": [{{"name": "...", "summary": "...", "evidence": "..."}}],
  "ideas": [{{"name": "...", "idea_type": "project|experiment|article|workshop|other", "description": "...", "evidence": "..."}}],
  "themes": [{{"name": "...", "description": "...", "frequency": "recurring|occasional|single"}}],
  "opportunities": [{{"what": "...", "type": "alignment|collaboration|promotion", "evidence": "..."}}],
  "milestones": [{{"name": "...", "description": "...", "evidence": "..."}}]
}}

Be concise. Max 10 insights, 12 ideas, 8 themes, 6 opportunities, 6 milestones.
"""


def _extract_json_from_response(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks and <think> tags."""
    text = text.strip()
    # Strip <think>...</think> blocks (MiniMax and similar models emit reasoning)
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            data = json.loads(m.group(0))
        else:
            raise
    return _normalize_extraction(data)


def _normalize_extraction(data: dict) -> dict:
    """Map LLM response to expected schema (orgs, reports, concepts, entities, opportunities)."""
    out = {
        "orgs": data.get("orgs") or [],
        "reports": data.get("reports") or [],
        "concepts": data.get("concepts") or [],
        "entities": data.get("entities") or [],
        "relationships": data.get("relationships") or [],
        "opportunities": data.get("opportunities") or {},
    }
    # Map common alternative schemas
    org_name = data.get("organization") or data.get("author") or data.get("org") or data.get("source")
    if not out["orgs"] and org_name:
        out["orgs"] = [{"name": org_name, "url": data.get("url", "")}]
    if not out["reports"] and data.get("title"):
        out["reports"] = [{"name": data["title"], "url": data.get("url", ""), "summary": data.get("summary", ""), "author_org": org_name or ""}]
    if not out["concepts"] and data.get("topic"):
        out["concepts"] = [{"name": data["topic"], "definition": data.get("summary", "")}]
    if not out["concepts"] and data.get("main_topic"):
        out["concepts"] = [{"name": data["main_topic"], "definition": data.get("summary", "")}]
    if not out["concepts"] and data.get("topics"):
        out["concepts"] = [{"name": t} if isinstance(t, str) else t for t in data["topics"]]
    # key_actions -> collaboration opportunities
    if data.get("key_actions") and not out["opportunities"].get("collaboration"):
        out["opportunities"]["collaboration"] = [{"what": a, "evidence": a} for a in data["key_actions"][:5] if isinstance(a, str)]
    return out


def _ensure_enrichment_schema(driver) -> None:
    with driver.session() as session:
        for label, prop in [
            ("MLOrg", "name"),
            ("MLReport", "name"),
            ("Opportunity", "id"),
            ("Insight", "id"),
            ("Idea", "id"),
            ("Theme", "name"),
            ("Milestone", "id"),
        ]:
            try:
                session.run(
                    f"CREATE CONSTRAINT ml_{label}_{prop} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
                )
            except Exception:
                pass


def _write_to_neo4j(driver, data: dict, source_id: str, source_name: str) -> tuple[int, dict]:
    """Write extracted entities and relationships to Neo4j. Returns (count, summary of node names)."""
    count = 0
    summary = {"orgs": [], "reports": [], "concepts": [], "entities": [], "opportunities": []}
    orgs = data.get("orgs") or []
    reports = data.get("reports") or []
    concepts = data.get("concepts") or []
    entities = data.get("entities") or []
    relationships = data.get("relationships") or []
    opportunities = data.get("opportunities") or {}

    with driver.session() as session:
        for o in orgs:
            name = (o.get("name") or "").strip()
            if not name:
                continue
            session.run(
                "MERGE (n:MLOrg {name: $name}) ON CREATE SET n.url = $url, n.type = $type, n.created_at = datetime() ON MATCH SET n.updated_at = datetime()",
                name=name,
                url=(o.get("url") or "")[:500],
                type=(o.get("type") or "")[:100],
            )
            count += 1
            summary["orgs"].append(name)

        for r in reports:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            session.run(
                "MERGE (n:MLReport {name: $name}) ON CREATE SET n.url = $url, n.author_org = $author_org, n.summary = $summary, n.created_at = datetime() ON MATCH SET n.updated_at = datetime()",
                name=name,
                url=(r.get("url") or "")[:500],
                author_org=(r.get("author_org") or "")[:200],
                summary=(r.get("summary") or "")[:1000],
            )
            count += 1
            summary["reports"].append(name)

        for c in concepts:
            name = (c.get("name") or "").strip()
            if not name:
                continue
            session.run(
                "MERGE (n:MLConcept {name: $name}) ON CREATE SET n.definition = $definition, n.created_at = datetime() ON MATCH SET n.updated_at = datetime()",
                name=name,
                definition=(c.get("definition") or "")[:500],
            )
            count += 1
            summary["concepts"].append(name)

        for e in entities:
            name = (e.get("name") or "").strip()
            if not name:
                continue
            session.run(
                "MERGE (n:MLEntity {name: $name}) ON CREATE SET n.entity_type = $t, n.created_at = datetime() ON MATCH SET n.updated_at = datetime()",
                name=name,
                t=(e.get("type") or "other")[:50],
            )
            count += 1
            summary["entities"].append(name)

        # Relationships
        for rel in relationships:
            frm = (rel.get("from") or "").strip()
            to = (rel.get("to") or "").strip()
            typ = (rel.get("type") or "RELATES_TO").upper()
            if not frm or not to:
                continue
            try:
                session.run(
                    f"""
                    MATCH (a) WHERE (a:MLOrg OR a:MLReport OR a:MLConcept OR a:MLEntity) AND a.name = $from
                    MATCH (b) WHERE (b:MLOrg OR b:MLReport OR b:MLConcept OR b:MLEntity) AND b.name = $to
                    MERGE (a)-[r:{typ}]->(b)
                    """,
                    **{"from": frm, "to": to},
                )
            except Exception:
                pass

        # Link source to report if we have one
        if reports:
            rname = (reports[0].get("name") or "").strip()
            if rname:
                try:
                    session.run(
                        """
                        MATCH (s:MLSource {id: $sid})
                        MATCH (r:MLReport {name: $rname})
                        MERGE (s)-[:REFERENCES]->(r)
                        """,
                        sid=source_id,
                        rname=rname,
                    )
                except Exception:
                    pass

        # Opportunities
        opp_id_base = f"opp_{source_name[:30]}_{hash(source_id) % 10000}"
        for i, o in enumerate(opportunities.get("alignment") or []):
            oid = f"{opp_id_base}_align_{i}"
            desc = (o.get("what") or "")[:300]
            why = (o.get("why") or "")[:300]
            ev = (o.get("evidence") or "")[:500]
            session.run(
                """
                MERGE (n:Opportunity {id: $id})
                ON CREATE SET n.type = 'alignment', n.description = $desc, n.why = $why, n.evidence = $ev, n.source_id = $sid, n.status = 'open', n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime()
                """,
                id=oid,
                desc=desc,
                why=why,
                ev=ev,
                sid=source_id,
            )
            count += 1
            summary["opportunities"].append(f"alignment: {(o.get('what') or '')[:60]}")

        for i, o in enumerate(opportunities.get("collaboration") or []):
            oid = f"{opp_id_base}_collab_{i}"
            desc = (o.get("what") or "")[:300]
            how = (o.get("how") or "")[:300]
            ev = (o.get("evidence") or "")[:500]
            session.run(
                """
                MERGE (n:Opportunity {id: $id})
                ON CREATE SET n.type = 'collaboration', n.description = $desc, n.how = $how, n.evidence = $ev, n.source_id = $sid, n.status = 'open', n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime()
                """,
                id=oid,
                desc=desc,
                how=how,
                ev=ev,
                sid=source_id,
            )
            count += 1
            summary["opportunities"].append(f"collaboration: {(o.get('what') or '')[:60]}")

        for i, o in enumerate(opportunities.get("promotion") or []):
            oid = f"{opp_id_base}_promo_{i}"
            angle = (o.get("angle") or "")[:300]
            fmt = (o.get("format") or "substack")[:50]
            ev = (o.get("evidence") or "")[:500]
            session.run(
                """
                MERGE (n:Opportunity {id: $id})
                ON CREATE SET n.type = 'promotion', n.description = $angle, n.format = $fmt, n.evidence = $ev, n.source_id = $sid, n.status = 'open', n.created_at = datetime()
                ON MATCH SET n.updated_at = datetime()
                """,
                id=oid,
                angle=angle,
                fmt=fmt,
                ev=ev,
                sid=source_id,
            )
            count += 1
            summary["opportunities"].append(f"promotion: {(o.get('angle') or '')[:60]}")

    return count, summary


def _sync_opportunities_to_ledger(driver, source_id: str, source_url: str = "") -> None:
    """Sync Opportunity nodes to data/opportunities.json for /opportunities."""
    if not LEDGER_PATH.exists():
        data = {"schema_version": 1, "opportunities": []}
    else:
        data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    opps = data.get("opportunities", [])

    with driver.session() as session:
        result = session.run(
            "MATCH (o:Opportunity {source_id: $sid}) RETURN o.type AS type, o.description AS desc, o.why AS why, o.how AS how",
            sid=source_id,
        )
        for r in result:
            name = (r["desc"] or r["why"] or r["how"] or "Opportunity")[:80]
            notes = f"From graph. Type: {r['type']}. Source: {source_url}"
            if r["why"]:
                notes += f" Why: {r['why'][:200]}"
            if r["how"]:
                notes += f" How: {r['how'][:200]}"
            opps.append({
                "id": f"graph_{len(opps)}_{hash(source_id) % 1000}",
                "name": name,
                "type": r["type"] or "other",
                "deadline": "TBD",
                "source": "graph_enrich",
                "status": "open",
                "notes": notes[:500],
                "added_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            })

    data["opportunities"] = opps[-100:]
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def enrich_file(path: Path, driver, llm, verbose: bool = False) -> tuple[int, dict]:
    """Enrich a single file. Returns (total nodes, summary of node names)."""
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 0, {}

    content = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(content) < 200:
        print("Content too short to enrich.", file=sys.stderr)
        return 0, {}

    source_id = f"source:{path.relative_to(KNOWLEDGE_DIR)}"
    source_name = path.stem
    ctx = _load_user_context()
    user_ctx = f"meta_layer_lens: {ctx.get('meta_layer_lens', '')}. key_projects: {ctx.get('key_projects', [])}. priorities: {ctx.get('priorities', [])}"

    total = 0
    merged = {"orgs": [], "reports": [], "concepts": [], "entities": [], "opportunities": []}
    offset = 0
    batch = 0
    while offset < len(content):
        chunk = content[offset : offset + MAX_CHARS_PER_BATCH]
        if not chunk.strip():
            break
        batch += 1
        print(f"  Batch {batch}: {len(chunk)} chars...", file=sys.stderr)

        from langchain_core.messages import SystemMessage, HumanMessage
        prompt = EXTRACTION_PROMPT.format(user_context=user_ctx)
        messages = [
            SystemMessage(content="You extract structured data from content. Return only valid JSON."),
            HumanMessage(content=f"Content to analyze:\n\n{chunk}"),
        ]
        try:
            resp = llm.invoke(messages)
            text = resp.content if hasattr(resp, "content") else str(resp)
            if verbose:
                stripped = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
                print(f"[verbose] After think-strip ({len(stripped)} chars): {repr(stripped[:800])}", file=sys.stderr)
            data = _extract_json_from_response(text)
            if verbose:
                print(f"[verbose] Parsed: orgs={len(data.get('orgs') or [])}, concepts={len(data.get('concepts') or [])}", file=sys.stderr)
            n, summary = _write_to_neo4j(driver, data, source_id, source_name)
            total += n
            for k in merged:
                for v in summary.get(k, []):
                    if v not in merged[k]:
                        merged[k].append(v)
        except Exception as e:
            print(f"  Batch {batch} failed: {e}", file=sys.stderr)
            if verbose:
                import traceback
                traceback.print_exc(file=sys.stderr)

        offset += MAX_CHARS_PER_BATCH
        if offset >= len(content):
            break

    return total, merged


def main() -> int:
    _load_env()
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", type=Path, help="Path to knowledge file (e.g. knowledge/urls/foo.md)")
    parser.add_argument("--source-id", help="Neo4j source ID (e.g. source:urls/foo.md)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print LLM response for debugging")
    args = parser.parse_args()

    if not args.file and not args.source_id:
        parser.error("Provide --file or --source-id")

    if args.file:
        path = args.file if args.file.is_absolute() else AGENT_LAB_ROOT / args.file
    else:
        # Resolve source-id to file path
        sid = args.source_id
        if sid.startswith("source:"):
            sid = sid[7:]
        path = KNOWLEDGE_DIR / sid
        if not path.exists():
            print(f"Source not found: {path}", file=sys.stderr)
            return 1

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        print(f"Neo4j error: {e}", file=sys.stderr)
        return 1

    _ensure_enrichment_schema(driver)
    llm = _get_llm()

    print(f"Enriching: {path}", file=sys.stderr)
    total, summary = enrich_file(path, driver, llm, verbose=args.verbose)
    source_id = f"source:{path.relative_to(KNOWLEDGE_DIR)}"
    _sync_opportunities_to_ledger(driver, source_id, str(path))

    driver.close()
    print(f"[enrich] Done. {total} nodes created/updated.", file=sys.stderr)
    # Print node list for Telegram reply (parseable by shiftshapr)
    lines = []
    if summary.get("orgs"):
        lines.append("Orgs: " + ", ".join(summary["orgs"][:15]))
    if summary.get("reports"):
        lines.append("Reports: " + ", ".join(summary["reports"][:5]))
    if summary.get("concepts"):
        lines.append("Concepts: " + ", ".join(summary["concepts"][:15]))
    if summary.get("entities"):
        lines.append("Entities: " + ", ".join(summary["entities"][:10]))
    if summary.get("opportunities"):
        lines.extend(summary["opportunities"][:5])
    if lines:
        print("NODES:\n" + "\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
