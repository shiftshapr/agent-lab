#!/usr/bin/env python3
"""
Build inscription/episode_NNN.json from drafts/episode_NNN.md without assign_ids.

Parses markdown with neo4j_ingest extractors (same fields neo4j_ingest uses for graph
ingest) and emits JSON-LD shaped like assign_ids + apply_ids_to_json output, preserving
live C-/A-/N-/M-* IDs already present in the drafts.

Does NOT rewrite drafts/, phase1_output/, or Neo4j.

Usage:
  cd ~/workspace/agent-lab
  python3 projects/monuments/bride_of_charlie/scripts/build_inscription_from_drafts.py
  python3 projects/monuments/bride_of_charlie/scripts/build_inscription_from_drafts.py --episode 8
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from neo4j_ingest import (  # noqa: E402
    MEME_NODE_HEADER,
    parse_episode_file,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_DIR / "drafts"
INSCRIPTION_DIR = PROJECT_DIR / "inscription"

_META_PATTERNS = {
    "episode": re.compile(r"- \*\*Episode\*\*:\s*(\d+)", re.I),
    "source": re.compile(r"- \*\*Source\*\*:\s*(.+)", re.I),
    "video_timestamp_range": re.compile(r"- \*\*Video Timestamp Range\*\*:\s*(.+)", re.I),
    "extraction_timestamp": re.compile(r"- \*\*Extraction Timestamp \(UTC\)\*\*:\s*(.+)", re.I),
    "model_version": re.compile(r"- \*\*Model Version\*\*:\s*(.+)", re.I),
    "transcript_sha256": re.compile(r"- \*\*Transcript SHA-256\*\*:\s*([0-9a-f]{64})", re.I),
    "analysis_date": re.compile(r"- \*\*Analysis Date\*\*:\s*(.+)", re.I),
    "transcript_completeness": re.compile(r"- \*\*Transcript Completeness\*\*:\s*(.+)", re.I),
}

_LABEL_TO_JSONLD: dict[str, tuple[str, str]] = {
    "Person": ("Person", "person"),
    "Organization": ("Organization", "organization"),
    "Place": ("Place", "place"),
    "Topic": ("Topic", "topic"),
    "InvestigationTarget": ("InvestigationTarget", "investigation_target"),
}

_OCC_FIELD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("video_timestamp", re.compile(r"^Video Timestamp:\s*(.+)$", re.I | re.MULTILINE)),
    ("speaker_node_ref", re.compile(r"^Speaker:\s*(\S+)\s*$", re.I | re.MULTILINE)),
    ("quote", re.compile(r"^Quote:\s*(.+)$", re.I | re.MULTILINE)),
    ("context", re.compile(r"^Context:\s*(.+)$", re.I | re.MULTILINE)),
    ("confidence", re.compile(r"^Confidence:\s*(high|medium|low)\s*$", re.I | re.MULTILINE)),
    ("uncertainty_note", re.compile(r"^Uncertainty:\s*(.+)$", re.I | re.MULTILINE)),
]
_TAGS_PATTERN = re.compile(r"^Tags:\s*(.+)$", re.I | re.MULTILINE)


def _split_related_ids(ids: list[str]) -> tuple[list[str], list[str], list[str]]:
    artifacts: list[str] = []
    claims: list[str] = []
    nodes: list[str] = []
    for raw in ids:
        token = raw
        if raw.lower().startswith("same_as:"):
            token = raw.split(":", 1)[1].strip()
        if token.startswith("A-"):
            artifacts.append(token)
        elif token.startswith("C-"):
            claims.append(token)
        elif token.startswith("N-"):
            nodes.append(token)
    return artifacts, claims, nodes


def _pressure(artifact_count: int, claim_count: int) -> str:
    score = artifact_count + claim_count * 2 + 1
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def _parse_meta(text: str, episode_num: int) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "episode": episode_num,
        "series": "Bride of Charlie",
        "channel": "Candace Owens",
        "source": "Video + Transcript",
        "transcript_completeness": "Full",
    }
    for key, pattern in _META_PATTERNS.items():
        m = pattern.search(text)
        if m:
            val = m.group(1).strip()
            if key == "episode":
                meta[key] = int(val)
            else:
                meta[key] = val
    if "analysis_date" not in meta and meta.get("extraction_timestamp"):
        meta["analysis_date"] = str(meta["extraction_timestamp"])[:10]
    return meta


def _parse_executive_summary(text: str) -> str:
    m = re.search(
        r"^## 2\. Executive Summary\s*\n(.*?)(?=^## 3\.)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def _parse_meme_register(text: str, episode_num: int) -> list[dict[str, Any]]:
    m = re.search(r"^## 6\. Meme Register\s*$", text, re.MULTILINE)
    if not m:
        return []
    section = text[m.end() :]
    nxt = re.search(r"^## \d+\.", section, re.MULTILINE)
    if nxt:
        section = section[: nxt.start()]

    memes: list[dict[str, Any]] = []
    headers = list(MEME_NODE_HEADER.finditer(section))
    for i, hdr in enumerate(headers):
        meme_id = hdr.group(1).strip()
        meme_type = hdr.group(2).strip()
        term = hdr.group(3).strip()
        start = hdr.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(section)
        block = section[start:end]

        occurrences: list[dict[str, Any]] = []
        parts = re.split(r"^### Occurrence \d+\s*$", block, flags=re.MULTILINE)
        for occ_block in parts[1:]:
            occ: dict[str, Any] = {"episode": episode_num}
            for key, pattern in _OCC_FIELD_PATTERNS:
                om = pattern.search(occ_block)
                if om:
                    val = om.group(1).strip()
                    if key == "confidence":
                        val = val.lower()
                    occ[key] = val
            tm = _TAGS_PATTERN.search(occ_block)
            if tm:
                occ["tags"] = [t.strip() for t in tm.group(1).split(",") if t.strip()]
            if occ.get("quote") or occ.get("video_timestamp"):
                occurrences.append(occ)

        if occurrences:
            memes.append(
                {
                    "@type": "MemeAnalysis",
                    "@id": meme_id,
                    "ref": meme_id,
                    "canonical_term": term,
                    "type": meme_type,
                    "occurrences": occurrences,
                }
            )
    return memes


def _build_artifacts(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    family_names = {f["id"]: f["name"] for f in parsed.get("artifact_families") or []}
    by_family: dict[str, list[dict[str, Any]]] = {}
    for art in parsed.get("artifacts") or []:
        fam = art.get("family_id") or art["id"].rsplit(".", 1)[0]
        rel_a, rel_c, rel_n = _split_related_ids(art.get("related_ids") or [])
        sub: dict[str, Any] = {
            "@type": "Artifact",
            "@id": art["id"],
            "ref": art["id"],
            "description": art.get("description") or "",
            "related_claims": rel_c,
            "related_nodes": rel_n,
            "tags": [],
        }
        if art.get("event_ts"):
            sub["event_timestamp"] = art["event_ts"]
        if art.get("source_ts"):
            sub["source_timestamp"] = art["source_ts"]
        if art.get("video_ts"):
            sub["video_timestamp"] = art["video_ts"]
        if art.get("discovery_ts"):
            sub["discovery_timestamp"] = art["discovery_ts"]
        if art.get("transcript_snippet"):
            sub["transcript_snippet"] = art["transcript_snippet"]
        if art.get("confidence"):
            sub["confidence"] = art["confidence"]
        if art.get("uncertainty_note"):
            sub["uncertainty_note"] = art["uncertainty_note"]
        if not rel_a and not rel_c and not rel_n:
            pass
        by_family.setdefault(fam, []).append(sub)

    out: list[dict[str, Any]] = []
    for fam_id in sorted(by_family.keys(), key=lambda x: int(x.split("-")[1])):
        out.append(
            {
                "@type": "ArtifactFamily",
                "@id": fam_id,
                "family_ref": fam_id,
                "bundle_name": family_names.get(fam_id, ""),
                "sub_items": by_family[fam_id],
            }
        )
    return out


def _collect_node_refs(data: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for claim in data.get("claims") or []:
        refs.update(claim.get("related_nodes") or [])
    for fam in data.get("artifacts") or []:
        for sub in fam.get("sub_items") or []:
            refs.update(sub.get("related_nodes") or [])
    for node in data.get("nodes") or []:
        refs.update(node.get("related_nodes") or [])
    return {r for r in refs if isinstance(r, str) and r.startswith("N-")}


def _load_global_node_registry(draft_paths: list[Path]) -> dict[str, dict[str, Any]]:
    """Index every N-* node block across drafts for cross-episode stub lookup."""
    registry: dict[str, dict[str, Any]] = {}
    for path in draft_paths:
        parsed = parse_episode_file(path)
        for node in _build_nodes(parsed):
            registry[str(node["ref"])] = node
    return registry


def _inject_cross_episode_stubs(
    data: dict[str, Any],
    registry: dict[str, dict[str, Any]],
) -> int:
    """Add nodes cited in claims/artifacts but absent from this episode's register."""
    present = {str(n.get("ref") or n.get("@id") or "") for n in data.get("nodes") or []}
    needed = _collect_node_refs(data) - present
    added = 0
    for nid in sorted(needed, key=lambda x: int(x.split("-")[1])):
        stub = registry.get(nid)
        if not stub:
            continue
        copy = dict(stub)
        copy["related_artifacts"] = []
        copy["related_claims"] = []
        copy["related_nodes"] = []
        copy["evidence_count"] = 0
        copy["claim_count"] = 0
        copy["episode_count"] = 1
        copy["investigative_pressure"] = "low"
        data.setdefault("nodes", []).append(copy)
        added += 1
    return added


def _build_nodes(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for n in parsed.get("nodes") or []:
        label = n.get("node_type") or "Person"
        jsonld_type, type_slug = _LABEL_TO_JSONLD.get(label, ("Person", "person"))
        rel_a, rel_c, rel_n = _split_related_ids(n.get("related_ids") or [])
        row: dict[str, Any] = {
            "@type": jsonld_type,
            "@id": n["id"],
            "ref": n["id"],
            "name": n.get("name") or "",
            "type": type_slug,
            "description": n.get("description") or "",
            "related_artifacts": rel_a,
            "related_claims": rel_c,
            "tags": [],
            "evidence_count": len(rel_a),
            "claim_count": len(rel_c),
            "episode_count": 1,
            "investigative_pressure": _pressure(len(rel_a), len(rel_c)),
        }
        if rel_n:
            row["related_nodes"] = rel_n
        if n.get("topic_kind"):
            row["topic_kind"] = n["topic_kind"]
        if n.get("organization_kind"):
            row["organization_kind"] = n["organization_kind"]
        if n.get("place_kind"):
            row["place_kind"] = n["place_kind"]
        if n.get("confidence"):
            row["confidence"] = n["confidence"]
        if n.get("uncertainty_note"):
            row["uncertainty_note"] = n["uncertainty_note"]
        nodes.append(row)
    return nodes


def _build_claims(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for c in parsed.get("claims") or []:
        row: dict[str, Any] = {
            "@type": "Claim",
            "@id": c["id"],
            "ref": c["id"],
            "label": c.get("label") or "",
            "claim": c.get("claim_text") or "",
            "anchored_artifacts": c.get("anchored_artifacts") or [],
            "related_nodes": c.get("related_nodes") or [],
            "tags": c.get("sensitive_topic_tags") or [],
        }
        if c.get("claim_ts"):
            row["claim_timestamp"] = c["claim_ts"]
        if c.get("investigative_direction"):
            row["investigative_direction"] = c["investigative_direction"]
        if c.get("transcript_snippet"):
            row["transcript_snippet"] = c["transcript_snippet"]
        if c.get("confidence"):
            row["confidence"] = c["confidence"]
        if c.get("uncertainty_note"):
            row["uncertainty_note"] = c["uncertainty_note"]
        if c.get("contradicts_claims"):
            row["contradicts_claim_refs"] = c["contradicts_claims"]
        if c.get("supports_claims"):
            row["supports_claim_refs"] = c["supports_claims"]
        if c.get("qualifies_claims"):
            row["qualifies_claim_refs"] = c["qualifies_claims"]
        claims.append(row)
    return claims


def build_episode_json(
    draft_path: Path,
    *,
    node_registry: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    text = draft_path.read_text(encoding="utf-8")
    parsed = parse_episode_file(draft_path)
    ep = int(parsed.get("episode_num") or 0)
    data = {
        "@context": "https://brc222.org/context/v1",
        "@type": "EpisodeAnalysis",
        "meta": _parse_meta(text, ep),
        "executive_summary": _parse_executive_summary(text),
        "artifacts": _build_artifacts(parsed),
        "nodes": _build_nodes(parsed),
        "claims": _build_claims(parsed),
        "memes": _parse_meme_register(text, ep),
    }
    if node_registry is not None:
        stubs = _inject_cross_episode_stubs(data, node_registry)
        if stubs:
            print(f"  + {stubs} cross-episode node stub(s)")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="Build inscription JSON from episode drafts")
    ap.add_argument("--drafts", type=Path, default=DRAFTS_DIR)
    ap.add_argument("--inscription", type=Path, default=INSCRIPTION_DIR)
    ap.add_argument("--episode", type=int, action="append", dest="episodes", metavar="N")
    args = ap.parse_args()

    drafts = sorted(args.drafts.glob("episode_*.md"))
    drafts = [p for p in drafts if re.match(r"episode_\d{3}\.md$", p.name)]
    if args.episodes:
        wanted = set(args.episodes)
        drafts = [p for p in drafts if int(re.search(r"episode_(\d+)", p.name).group(1)) in wanted]

    if not drafts:
        print("[build] No episode drafts found.", file=sys.stderr)
        return 1

    args.inscription.mkdir(parents=True, exist_ok=True)
    all_drafts = sorted(args.drafts.glob("episode_*.md"))
    all_drafts = [p for p in all_drafts if re.match(r"episode_\d{3}\.md$", p.name)]
    node_registry = _load_global_node_registry(all_drafts)

    for draft in drafts:
        ep = int(re.search(r"episode_(\d+)", draft.name).group(1))
        print(f"[build] episode_{ep:03d}.md")
        data = build_episode_json(draft, node_registry=node_registry)
        out = args.inscription / f"episode_{ep:03d}.json"
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        n_claims = len(data.get("claims") or [])
        n_nodes = len(data.get("nodes") or [])
        n_arts = sum(len(f.get("sub_items") or []) for f in data.get("artifacts") or [])
        print(f"[build] {out.name}: {n_arts} artifacts, {n_claims} claims, {n_nodes} nodes")

    print(f"[build] Wrote {len(drafts)} inscription JSON file(s) to {args.inscription}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
