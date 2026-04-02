#!/usr/bin/env python3
"""
List all person-like names for human review: Neo4j graph, NameCorrection dictionary,
and Node Register lines from episode drafts.

Usage (from agent-lab root or bride_of_charlie):
  uv run --project framework/deer-flow/backend python scripts/list_names_audit.py
  uv run --project framework/deer-flow/backend python scripts/list_names_audit.py --out names_audit.md

Requires Neo4j for sections 1–2; drafts section always runs if drafts/ exists.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
AGENT_LAB = PROJECT_DIR.parent.parent.parent

NODE_LINE = re.compile(r"^\*\*(N-\d+)\*\*\s+(.+)$", re.MULTILINE)

# Load .env
try:
    from dotenv import load_dotenv

    load_dotenv(AGENT_LAB / ".env", override=False)
except ImportError:
    pass

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")


def section_graph() -> str:
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return "## 1. Neo4j graph (Person / InvestigationTarget)\n\n*(neo4j driver not installed)*\n\n"

    lines = ["## 1. Neo4j graph (Person / InvestigationTarget)\n"]
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        return (
            "## 1. Neo4j graph (Person / InvestigationTarget)\n\n"
            f"*(could not connect: {e})*\n\n"
        )

    with driver.session() as session:
        q = """
        MATCH (n)
        WHERE n:Person OR n:InvestigationTarget
        RETURN labels(n) AS labels, n.id AS id, n.canonical_name AS canonical_name,
               n.name AS name, n.aliases AS aliases
        ORDER BY n.id
        """
        rows = list(session.run(q))
    driver.close()

    if not rows:
        lines.append("*(no Person / InvestigationTarget nodes)*\n\n")
        return "".join(lines)

    lines.append("| id | labels | canonical_name | name | aliases |\n")
    lines.append("|----|--------|----------------|------|--------|\n")
    for r in rows:
        lbl = ",".join(r["labels"] or [])
        cn = (r["canonical_name"] or "").replace("|", "\\|")
        nm = (r["name"] or "").replace("|", "\\|")
        als = r["aliases"]
        if isinstance(als, list):
            astr = "; ".join(str(a) for a in als if a)
        else:
            astr = str(als or "")
        astr = astr.replace("|", "\\|")
        lines.append(f"| {r['id']} | {lbl} | {cn} | {nm} | {astr} |\n")
    lines.append("\n")
    return "".join(lines)


def section_name_corrections() -> str:
    lines = ["## 2. Neo4j NameCorrection dictionary\n\n"]
    try:
        from neo4j import GraphDatabase
    except ImportError:
        lines.append("*(neo4j driver not installed)*\n\n")
        return "".join(lines)

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        lines.append(f"*(could not connect: {e})*\n\n")
        return "".join(lines)

    with driver.session() as session:
        recs = session.run(
            "MATCH (nc:NameCorrection) "
            "RETURN nc.incorrect AS incorrect, nc.correct AS correct, "
            "nc.confidence AS confidence, nc.source AS source "
            "ORDER BY nc.incorrect"
        )
        rows = [dict(x) for x in recs]
    driver.close()

    if not rows:
        lines.append("*(no NameCorrection nodes)*\n\n")
        return "".join(lines)

    lines.append("| incorrect → correct | confidence | source |\n")
    lines.append("|---------------------|------------|--------|\n")
    for r in rows:
        inc = (r.get("incorrect") or "").replace("|", "\\|")
        cor = (r.get("correct") or "").replace("|", "\\|")
        lines.append(f"| `{inc}` → `{cor}` | {r.get('confidence', '')} | {r.get('source', '')} |\n")
    lines.append("\n")
    return "".join(lines)


def section_drafts() -> str:
    drafts_dir = PROJECT_DIR / "drafts"
    lines = ["## 3. Drafts — Node Register (`**N-…**` lines)\n\n"]
    if not drafts_dir.is_dir():
        lines.append("*(no drafts/ directory)*\n\n")
        return "".join(lines)

    md_files = sorted(drafts_dir.glob("episode_*.md"))
    if not md_files:
        lines.append("*(no episode_*.md in drafts/)*\n\n")
        return "".join(lines)

    # nid -> set of (file, label)
    by_id: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for path in md_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in NODE_LINE.finditer(text):
            nid, label = m.group(1), m.group(2).strip()
            by_id[nid].add((path.name, label))

    lines.append(
        "Same `N-*` id may show **different label text** across episodes (regen / merge quirks).\n\n"
    )
    lines.append("| Node id | Appears in | Label text |\n")
    lines.append("|---------|------------|------------|\n")

    def sort_key(k: str) -> tuple[int, int]:
        m = re.match(r"N-(\d+)$", k)
        if not m:
            return (999, 999)
        n = int(m.group(1))
        return (0, n) if n < 1000 else (1, n)

    for nid in sorted(by_id.keys(), key=sort_key):
        entries = sorted(by_id[nid])
        files = ", ".join(e[0] for e in entries)
        labels = {e[1] for e in entries}
        lab_display = " **//** ".join(sorted(labels)) if len(labels) > 1 else (entries[0][1] if entries else "")
        lab_display = lab_display.replace("|", "\\|")
        lines.append(f"| {nid} | {files} | {lab_display} |\n")

    lines.append("\n")
    return "".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit names: Neo4j + NameCorrection + draft Node lines")
    ap.add_argument("--out", type=Path, help="Write report to this file (UTF-8)")
    args = ap.parse_args()

    title = "# Bride of Charlie — name audit\n\n"
    title += f"_Project: `{PROJECT_DIR}`_\n\n"
    body = title + section_graph() + section_name_corrections() + section_drafts()
    body += (
        "## 4. How to use this\n\n"
        "- Compare **§1** vs **§3**: graph should match your intended canonical names.\n"
        "- **§2**: every `incorrect → correct` substring-replaces in `transcripts_corrected/` "
        "on `apply-dir` (longer `incorrect` first).\n"
        "- Remove bad rows: `python scripts/neo4j_corrections.py remove \"…\"`\n"
    )

    if args.out:
        args.out.write_text(body, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
