"""
Two-Phase Generation: Assign IDs from Central Ledger

Phase 2 of two-phase generation. Reads entity extraction output (JSON from Phase 1)
and assigns A-, C-, N- IDs from the ledger. Outputs final markdown.

Batch mode (Phase 1 done for all episodes, then Phase 2 across batch):
  assign_ids.py --batch phase1_output/ --drafts drafts/

Regenerate from scratch (series order, people start at N-1, reuse IDs for same name):
  assign_ids.py --batch phase1_output/ --drafts drafts/ --fresh-ledger \\
    --dedupe-nodes --episode-output-names

Without --fresh-ledger, the ledger is taken from scanning --ledger / drafts (max existing
A-/C-/N- numbers). If drafts already contain high N-* ids, episode 001 can get N-32+ for the
first on-screen person even when phase1 lists them as NODE_1. Use --fresh-ledger to reset.

Single-file mode:
  assign_ids.py phase1_output.json --drafts drafts/

  --batch DIR     Process all episode_*.json in DIR (episode order), single ledger
  --drafts DIR    Where to write output (default: project drafts/)
  --ledger DIR    Scan this dir for ledger state if Neo4j unavailable
  --fresh-ledger  Do not scan --ledger / Neo4j; start A-/C-/N- counters from series defaults.
                  Also deletes legacy drafts matching episode_NNN_episode_NNN_<id>.md (stale ID space).
  --keep-legacy-draft-md  With --fresh-ledger, do not delete those legacy markdown files
  --dedupe-nodes  In batch, reuse N-* for same normalized node name across episodes (default on for --batch)
  --no-dedupe-nodes  Every NODE_* placeholder gets a new N-* (legacy behavior)
  --canonical-nodes FILE  Seed dedupe map from canonical/nodes.json (canonical_name + aliases)
  --episode-output-names   Write drafts/episode_NNN.md and inscription/episode_NNN.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Long-name episode drafts from an older naming scheme; same content as episode_NNN.md but wrong A-/C-/N- IDs.
_LEGACY_EPISODE_DRAFT_MD = re.compile(
    r"^episode_(\d{3})_episode_\1_[A-Za-z0-9_-]+\.md$"
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_DIR / "drafts"

# Reuse protocol's ledger logic
AGENT_LAB = PROJECT_DIR.parent.parent.parent
sys.path.insert(0, str(AGENT_LAB))
try:
    from protocols.episode_analysis.repo_venv_bootstrap import maybe_reexec_with_venv_if_jsonschema_missing

    maybe_reexec_with_venv_if_jsonschema_missing()
except ImportError:
    pass
try:
    from protocols.episode_analysis.episode_analysis_protocol import (
        scan_output_for_ids,
        format_ledger_context,
    )
except ImportError:
    scan_output_for_ids = None
    format_ledger_context = None

try:
    from protocols.episode_analysis.phase1_validation import validate_phase1
except ImportError:
    validate_phase1 = None  # type: ignore[misc, assignment]

try:
    from protocols.episode_analysis.node_claim_sync import (
        sanitize_node_claim_graph_phase1,
        sync_placeholder_refs_from_jsonld,
    )
except ImportError:
    sanitize_node_claim_graph_phase1 = None  # type: ignore[misc, assignment]
    sync_placeholder_refs_from_jsonld = None  # type: ignore[misc, assignment]


def _fallback_sync_placeholder_refs_from_jsonld(data: dict) -> None:
    """Used when ``node_claim_sync`` is not importable (same logic as protocols)."""
    for art in data.get("artifacts") or []:
        if not art.get("family_ref"):
            aid = art.get("@id")
            if aid:
                art["family_ref"] = aid
        for sub in art.get("sub_items") or []:
            if not sub.get("ref"):
                sid = sub.get("@id")
                if sid:
                    sub["ref"] = sid
    for node in data.get("nodes") or []:
        if not node.get("ref"):
            nid = node.get("@id")
            if nid:
                node["ref"] = nid
    for claim in data.get("claims") or []:
        if not claim.get("ref"):
            cid = claim.get("@id")
            if cid:
                claim["ref"] = cid
        if not claim.get("label"):
            if claim.get("title"):
                claim["label"] = str(claim["title"])
            elif claim.get("claim"):
                c = str(claim["claim"])
                claim["label"] = c if len(c) <= 240 else c[:237] + "…"

ENTITY_SCHEMA = PROJECT_DIR / "templates" / "entity_schema.json"
CANONICAL_NODES_DEFAULT = PROJECT_DIR / "canonical" / "nodes.json"


def _normalize_node_name(name: str) -> str:
    """Lowercase collapse whitespace for cross-episode person / investigation dedupe."""
    s = (name or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _neo4j_label_and_kinds(node: dict, ref: str = "") -> tuple[str, dict[str, str]]:
    """
    Map Phase 1 node to Neo4j label and optional kind fields for markdown / graph filters.
    Legacy InvestigationTarget + institution → Organization; other legacy themes → Topic.
    """
    at = str(node.get("@type") or "").strip()
    ntype = str(node.get("type") or "").lower()
    tags = {str(t).lower() for t in (node.get("tags") or [])}
    high_ref = bool(ref and re.match(r"NODE_1\d{3}", ref))

    if at == "Person" or (ntype == "person" and not high_ref):
        return "Person", {}

    if at == "Organization" or ntype == "organization":
        k = (node.get("organization_kind") or "").strip()
        return "Organization", {"organization_kind": k or "other"}
    if at == "Place" or ntype == "place":
        k = (node.get("place_kind") or "").strip()
        return "Place", {"place_kind": k or "other"}
    if at == "Topic" or ntype == "topic":
        k = (node.get("topic_kind") or "").strip()
        return "Topic", {"topic_kind": k or "other"}

    if ntype == "institution" or (at == "InvestigationTarget" and "institution" in tags):
        k = (node.get("organization_kind") or "").strip()
        return "Organization", {"organization_kind": k or "other"}

    if at == "InvestigationTarget" or ntype == "investigation_target" or high_ref:
        k = (node.get("topic_kind") or "").strip()
        return "Topic", {"topic_kind": k or "legacy_theme"}

    return "Person", {}


def _node_is_investigation(node: dict, ref: str) -> bool:
    """True when this node uses the N-1000+ id ledger (non-person)."""
    return _neo4j_label_and_kinds(node, ref)[0] != "Person"


def _node_dedupe_bucket(node: dict, ref: str) -> str:
    """Separate canonical name dedupe pools: person vs topic vs organization vs place."""
    label, _ = _neo4j_label_and_kinds(node, ref)
    if label == "Person":
        return "person"
    if label == "Organization":
        return "organization"
    if label == "Place":
        return "place"
    return "topic"


def _canonical_registry_bucket(n: dict, nid: str) -> str:
    t = str(n.get("type", "")).lower()
    if t == "person":
        return "person"
    if t in ("organization", "institution"):
        return "organization"
    if t == "place":
        return "place"
    if t in ("topic", "investigation_target"):
        return "topic"
    try:
        num = int(str(nid).split("-", 1)[-1])
    except ValueError:
        num = 0
    return "topic" if num >= 1000 else "person"


def load_node_registry_from_canonical(path: Path) -> dict[tuple[str, str], str]:
    """
    Build (bucket, normalized_name) -> N-* from canonical/nodes.json.
    bucket is person | topic | organization | place (keeps Topic vs org vs place dedupe separate).
    """
    reg: dict[tuple[str, str], str] = {}
    if not path.is_file():
        return reg
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return reg
    for nid, n in (doc.get("nodes") or {}).items():
        if not isinstance(n, dict):
            continue
        bucket = _canonical_registry_bucket(n, str(nid))
        cname = _normalize_node_name(str(n.get("canonical_name") or ""))
        if cname:
            reg[(bucket, cname)] = str(nid)
        for al in n.get("aliases") or []:
            an = _normalize_node_name(str(al))
            if an:
                reg[(bucket, an)] = str(nid)
    return reg


def _bump_ledger_next_nodes_from_registry(
    ledger: dict, reg: dict[tuple[str, str], str]
) -> None:
    """
    Canonical nodes.json can pin specific N-* for names. New people still consume
    next_node sequentially; without bumping, the counter can reuse an id already
    reserved in the registry (e.g. seed N-1 for Charlie but next unseeded person
    also gets N-1). Advance past the max numeric suffix seen among registry values.
    """
    max_person = 0
    max_inv = 999
    seen: set[str] = set()
    for nid in reg.values():
        if not isinstance(nid, str) or not nid.startswith("N-") or nid in seen:
            continue
        seen.add(nid)
        try:
            n = int(nid.split("-", 1)[1])
        except ValueError:
            continue
        if n >= 1000:
            max_inv = max(max_inv, n)
        elif n >= 1:
            max_person = max(max_person, n)
    if max_person > 0:
        ledger["next_node"] = max(int(ledger["next_node"]), max_person + 1)
    if max_inv >= 1000:
        ledger["next_node_inv"] = max(int(ledger["next_node_inv"]), max_inv + 1)


def _phase1_validation_errors(data: dict) -> list[str]:
    if not validate_phase1:
        return []
    return validate_phase1(
        data,
        ENTITY_SCHEMA if ENTITY_SCHEMA.is_file() else None,
    )


def _prepare_phase1_graph(data: dict) -> None:
    """Normalize refs and enforce node↔claim edge consistency before validation / ID assignment."""
    if sync_placeholder_refs_from_jsonld:
        sync_placeholder_refs_from_jsonld(data)
    else:
        _fallback_sync_placeholder_refs_from_jsonld(data)
    if sanitize_node_claim_graph_phase1:
        nlog = sanitize_node_claim_graph_phase1(data)
        if nlog:
            print(f"[assign_ids] node↔claim sync: {len(nlog)} change(s)")
            for line in nlog[:20]:
                print(f"  {line}")
            if len(nlog) > 20:
                print(f"  ... and {len(nlog) - 20} more")


def get_ledger_state(output_dir: Path) -> dict:
    """Get next available IDs from Neo4j or file scan."""
    if scan_output_for_ids and output_dir.exists():
        highest = scan_output_for_ids(output_dir)
    else:
        highest = {
            "artifact_bundle": 999,
            "claim": 1000,
            "node": 0,
            "node_investigation": 1000,
            "legal_matter": 999,
        }
    return {
        "next_artifact": int(highest["artifact_bundle"]) + 1,
        "next_claim": int(highest["claim"]) + 1,
        "next_node": int(highest["node"]) + 1,
        "next_node_inv": int(highest["node_investigation"]) + 1,
        "next_legal_matter": int(highest.get("legal_matter", 999)) + 1,
    }


def assign_ids_to_entities(
    data: dict,
    ledger: dict,
    *,
    dedupe_nodes: bool = False,
    node_name_registry: dict[tuple[str, str], str] | None = None,
) -> tuple[dict, dict]:
    """
    Build ref -> real ID mappings.
    If dedupe_nodes and node_name_registry is provided, reuse N-* when the same
    normalized name appears again (person vs topic vs organization vs place buckets).
    Registry is updated in place for new allocations.
    Returns (ref_to_id, updated_ledger).
    """
    ref_to_id: dict[str, str] = {}
    next_art = ledger["next_artifact"]
    next_claim = ledger["next_claim"]
    next_node = ledger["next_node"]
    next_node_inv = ledger["next_node_inv"]
    next_lm = int(ledger.get("next_legal_matter", 1000))
    reg = node_name_registry if dedupe_nodes and node_name_registry is not None else None

    # Artifacts: ART_1 -> A-1005, ART_1.1 -> A-1005.1
    for i, art in enumerate(data.get("artifacts", []), 1):
        fam_ref = art.get("family_ref") or f"ART_{i}"
        ref_to_id[fam_ref] = f"A-{next_art}"
        for j, sub in enumerate(art.get("sub_items", []), 1):
            sub_ref = sub.get("ref") or f"{fam_ref}.{j}"
            ref_to_id[sub_ref] = f"A-{next_art}.{j}"
        next_art += 1

    # Nodes: NODE_1 -> N-1 (people), NODE_1000 -> N-1000 (investigation)
    for node in data.get("nodes", []):
        ref = node.get("ref", "")
        inv = _node_is_investigation(node, ref)
        bucket = _node_dedupe_bucket(node, ref) if inv else "person"
        name_key = _normalize_node_name(str(node.get("name") or ""))

        if reg is not None and name_key:
            existing = reg.get((bucket, name_key))
            if existing:
                ref_to_id[ref] = existing
                continue

        if inv:
            new_id = f"N-{next_node_inv}"
            next_node_inv += 1
        else:
            new_id = f"N-{next_node}"
            next_node += 1
        ref_to_id[ref] = new_id
        if reg is not None and name_key:
            reg[(bucket, name_key)] = new_id

    # Legal matters: CASE_1 -> LM-1000 (global series IDs)
    for i, lm in enumerate(data.get("legal_matters") or [], 1):
        if not isinstance(lm, dict):
            continue
        ref = lm.get("ref") or f"CASE_{i}"
        ref_to_id[ref] = f"LM-{next_lm}"
        next_lm += 1

    # Claims: CLAIM_1 -> C-1009
    for i, claim in enumerate(data.get("claims", []), 1):
        ref = claim.get("ref") or f"CLAIM_{i}"
        ref_to_id[ref] = f"C-{next_claim}"
        next_claim += 1

    updated_ledger = {
        "next_artifact": next_art,
        "next_claim": next_claim,
        "next_node": next_node,
        "next_node_inv": next_node_inv,
        "next_legal_matter": next_lm,
    }
    return ref_to_id, updated_ledger


def replace_refs(text: str, ref_to_id: dict[str, str]) -> str:
    """Replace placeholder refs with real IDs. Longest first to avoid partial matches."""
    result = text
    for ref in sorted(ref_to_id.keys(), key=len, reverse=True):
        result = re.sub(rf"\b{re.escape(ref)}\b", ref_to_id[ref], result)
    return result


def apply_ids_to_json(data: dict, ref_to_id: dict[str, str]) -> dict:
    """Return a deep copy of data with placeholder refs replaced by real IDs. Inscription-ready JSON."""
    import copy
    out = copy.deepcopy(data)
    for art in out.get("artifacts", []):
        fid = ref_to_id.get(art.get("family_ref", ""), art.get("family_ref", ""))
        art["@id"] = fid
        art["family_ref"] = fid
        for sub in art.get("sub_items", []):
            sid = ref_to_id.get(sub.get("ref", ""), sub.get("ref", ""))
            sub["@id"] = sid
            sub["ref"] = sid
            sub["related_claims"] = [ref_to_id.get(r, r) for r in sub.get("related_claims", [])]
            sub["related_nodes"] = [ref_to_id.get(r, r) for r in sub.get("related_nodes", [])]
            if sub.get("same_as_artifact_refs"):
                sub["same_as_artifact_refs"] = [
                    ref_to_id.get(r, r) for r in sub.get("same_as_artifact_refs", [])
                ]
    for node in out.get("nodes", []):
        nid = ref_to_id.get(node.get("ref", ""), node.get("ref", ""))
        node["@id"] = nid
        node["ref"] = nid
        node["related_artifacts"] = [ref_to_id.get(r, r) for r in node.get("related_artifacts", [])]
        node["related_claims"] = [ref_to_id.get(r, r) for r in node.get("related_claims", [])]
        if node.get("related_nodes"):
            node["related_nodes"] = [ref_to_id.get(r, r) for r in node.get("related_nodes", [])]
    for claim in out.get("claims", []):
        cid = ref_to_id.get(claim.get("ref", ""), claim.get("ref", ""))
        claim["@id"] = cid
        claim["ref"] = cid
        claim["anchored_artifacts"] = [ref_to_id.get(r, r) for r in claim.get("anchored_artifacts", [])]
        claim["related_nodes"] = [ref_to_id.get(r, r) for r in claim.get("related_nodes", [])]
        if claim.get("contradicts_claim_refs"):
            claim["contradicts_claim_refs"] = [
                ref_to_id.get(r, r) for r in claim.get("contradicts_claim_refs", [])
            ]
        if claim.get("supports_claim_refs"):
            claim["supports_claim_refs"] = [
                ref_to_id.get(r, r) for r in claim.get("supports_claim_refs", [])
            ]
        if claim.get("qualifies_claim_refs"):
            claim["qualifies_claim_refs"] = [
                ref_to_id.get(r, r) for r in claim.get("qualifies_claim_refs", [])
            ]
    for lm in out.get("legal_matters") or []:
        if not isinstance(lm, dict):
            continue
        if lm.get("ref"):
            lid = ref_to_id.get(lm["ref"], lm["ref"])
            lm["ref"] = lid
            lm["@id"] = lid
        lm["artifact_refs"] = [ref_to_id.get(r, r) for r in lm.get("artifact_refs") or []]
        lm["party_node_refs"] = [ref_to_id.get(r, r) for r in lm.get("party_node_refs") or []]
        lm["place_node_refs"] = [ref_to_id.get(r, r) for r in lm.get("place_node_refs") or []]
    for row in out.get("organization_relationships") or []:
        if isinstance(row, dict):
            if row.get("from_org_ref"):
                row["from_org_ref"] = ref_to_id.get(row["from_org_ref"], row["from_org_ref"])
            if row.get("to_org_ref"):
                row["to_org_ref"] = ref_to_id.get(row["to_org_ref"], row["to_org_ref"])
            row["source_artifact_refs"] = [
                ref_to_id.get(r, r) for r in row.get("source_artifact_refs") or []
            ]
    for row in out.get("role_assertions") or []:
        if isinstance(row, dict):
            if row.get("person_node_ref"):
                row["person_node_ref"] = ref_to_id.get(
                    row["person_node_ref"], row["person_node_ref"]
                )
            if row.get("org_node_ref"):
                row["org_node_ref"] = ref_to_id.get(row["org_node_ref"], row["org_node_ref"])
    for row in out.get("node_equivalences") or []:
        if isinstance(row, dict):
            if row.get("node_ref_a"):
                row["node_ref_a"] = ref_to_id.get(row["node_ref_a"], row["node_ref_a"])
            if row.get("node_ref_b"):
                row["node_ref_b"] = ref_to_id.get(row["node_ref_b"], row["node_ref_b"])
    for row in out.get("provenance_links") or []:
        if isinstance(row, dict):
            if row.get("from_ref"):
                row["from_ref"] = ref_to_id.get(row["from_ref"], row["from_ref"])
            if row.get("to_ref"):
                row["to_ref"] = ref_to_id.get(row["to_ref"], row["to_ref"])
    for row in out.get("topic_mentions") or []:
        if isinstance(row, dict):
            if row.get("claim_ref"):
                row["claim_ref"] = ref_to_id.get(row["claim_ref"], row["claim_ref"])
            if row.get("topic_node_ref"):
                row["topic_node_ref"] = ref_to_id.get(
                    row["topic_node_ref"], row["topic_node_ref"]
                )
    for row in out.get("meme_links") or []:
        if isinstance(row, dict):
            if row.get("claim_ref"):
                row["claim_ref"] = ref_to_id.get(row["claim_ref"], row["claim_ref"])
            if row.get("speaker_node_ref"):
                row["speaker_node_ref"] = ref_to_id.get(
                    row["speaker_node_ref"], row["speaker_node_ref"]
                )
            if row.get("target_node_ref"):
                row["target_node_ref"] = ref_to_id.get(
                    row["target_node_ref"], row["target_node_ref"]
                )
    for meme_block in out.get("memes", []):
        for occ in meme_block.get("occurrences", []):
            ref = occ.get("speaker_node_ref")
            if ref:
                occ["speaker_node_ref"] = ref_to_id.get(ref, ref)
    return out


def render_markdown(data: dict, ref_to_id: dict[str, str]) -> str:
    """Render entity JSON to protocol markdown with real IDs."""
    lines = []
    meta = data.get("meta", {})
    ep = meta.get("episode", "?")

    lines.append("# Episode Analysis Output Template\n")
    lines.append("## 1. Meta-Data\n")
    lines.append(f"- **Episode**: {meta.get('episode', '?')}")
    lines.append(f"- **Source**: {meta.get('source', 'Unknown')}")
    lines.append(f"- **Video Timestamp Range**: {meta.get('video_timestamp_range', 'Unknown')}")
    if meta.get("extraction_timestamp"):
        lines.append(f"- **Extraction Timestamp (UTC)**: {meta['extraction_timestamp']}")
    if meta.get("model_version"):
        lines.append(f"- **Model Version**: {meta['model_version']}")
    if meta.get("transcript_sha256"):
        lines.append(f"- **Transcript SHA-256**: {meta['transcript_sha256']}")
    lines.append("")

    art_ids = sorted({ref_to_id.get(a["family_ref"], a["family_ref"]) for a in data.get("artifacts", []) if a.get("family_ref") in ref_to_id})
    claim_refs = [c.get("ref") for c in data.get("claims", []) if c.get("ref") in ref_to_id]
    claim_ids = sorted([ref_to_id[r] for r in claim_refs], key=lambda x: int(x.split("-")[1]))
    node_ids = sorted(
        {ref_to_id.get(n["ref"], n["ref"]) for n in data.get("nodes", []) if n.get("ref") in ref_to_id},
        key=lambda x: int(x.split("-")[1]),
    )

    lines.append("- **Episode Ledger Summary**:")
    lines.append(f"  - Artifact Families Introduced: {', '.join(art_ids) if art_ids else 'None'}")
    lines.append(f"  - Claim Range: {claim_ids[0]}-{claim_ids[-1]}" if len(claim_ids) >= 2 else f"  - Claim Range: {claim_ids[0]}" if claim_ids else "  - Claim Range: None")
    lines.append(f"  - New Nodes Introduced: {', '.join(node_ids) if node_ids else 'None'}")
    lines.append("")

    lines.append("## 2. Executive Summary\n")
    lines.append(data.get("executive_summary", ""))
    lines.append("")

    lines.append("## 3. Artifact Register\n")
    for art in data.get("artifacts", []):
        fam_ref = art.get("family_ref", "")
        fam_id = ref_to_id.get(fam_ref, fam_ref)
        lines.append(f"**{fam_id}** {art.get('bundle_name', '')}\n")
        for sub in art.get("sub_items", []):
            sub_id = ref_to_id.get(sub.get("ref", ""), sub.get("ref", ""))
            lines.append(f"**{sub_id}** {sub.get('description', '')}")
            if sub.get("event_timestamp"):
                lines.append(f"Event Timestamp: {sub['event_timestamp']}")
            if sub.get("video_timestamp"):
                lines.append(f"Video Timestamp: {sub['video_timestamp']}")
            rel_c = [ref_to_id.get(r, r) for r in sub.get("related_claims", [])]
            rel_n = [ref_to_id.get(r, r) for r in sub.get("related_nodes", [])]
            same_as = [ref_to_id.get(r, r) for r in sub.get("same_as_artifact_refs", [])]
            rel_bits = rel_c + rel_n
            if same_as:
                rel_bits.append(f"same_as: {', '.join(same_as)}")
            lines.append(f"*Related: {', '.join(rel_bits)}*")
            if sub.get("transcript_snippet"):
                lines.append(f"Transcript Snippet: {sub['transcript_snippet']}")
            if sub.get("confidence"):
                lines.append(f"Confidence: {sub['confidence']}")
            if sub.get("uncertainty_note"):
                lines.append(f"Uncertainty: {sub['uncertainty_note']}")
            lines.append("")
        lines.append("---\n")

    lines.append("## 4. Node Register\n")
    for node in data.get("nodes", []):
        nid = ref_to_id.get(node.get("ref", ""), node.get("ref", ""))
        ref = str(node.get("ref") or "")
        lines.append(f"**{nid}** {node.get('name', '')}\n")
        label, kinds = _neo4j_label_and_kinds(node, ref)
        lines.append(f"Node Type: {label}")
        if label == "Topic":
            tk = (kinds.get("topic_kind") or "").strip()
            if tk:
                lines.append(f"Topic Kind: {tk}")
        elif label == "Organization":
            ok = (kinds.get("organization_kind") or "").strip()
            if ok:
                lines.append(f"Organization Kind: {ok}")
        elif label == "Place":
            pk = (kinds.get("place_kind") or "").strip()
            if pk:
                lines.append(f"Place Kind: {pk}")
        lines.append(node.get("description", ""))
        rel_a = [ref_to_id.get(r, r) for r in node.get("related_artifacts", [])]
        rel_c = [ref_to_id.get(r, r) for r in node.get("related_claims", [])]
        lines.append(f"\n*Related: {', '.join(rel_a + rel_c)}*")
        if node.get("confidence"):
            lines.append(f"\nConfidence: {node['confidence']}")
        if node.get("uncertainty_note"):
            lines.append(f"Uncertainty: {node['uncertainty_note']}")
        lines.append("\n---\n")

    lines.append("## 5. Claim Register\n")
    for claim in data.get("claims", []):
        cid = ref_to_id.get(claim.get("ref", ""), claim.get("ref", ""))
        lines.append(f"**{cid}** {claim.get('label', '')}\n")
        lines.append(f"Claim Timestamp: {claim.get('claim_timestamp', '')}")
        lines.append(f"Claim: {claim.get('claim', '')}")
        if claim.get("transcript_snippet"):
            lines.append(f"Transcript Snippet: {claim['transcript_snippet']}")
        arts = [ref_to_id.get(r, r) for r in claim.get("anchored_artifacts", [])]
        nodes = [ref_to_id.get(r, r) for r in claim.get("related_nodes", [])]
        lines.append(f"Anchored Artifacts: {', '.join(arts)}")
        lines.append(f"Related Nodes: {', '.join(nodes)}")
        if claim.get("contradicts_claim_refs"):
            cc = [ref_to_id.get(r, r) for r in claim["contradicts_claim_refs"]]
            lines.append(f"Contradicts: {', '.join(cc)}")
        if claim.get("supports_claim_refs"):
            sc = [ref_to_id.get(r, r) for r in claim["supports_claim_refs"]]
            lines.append(f"Supports: {', '.join(sc)}")
        if claim.get("qualifies_claim_refs"):
            qq = [ref_to_id.get(r, r) for r in claim["qualifies_claim_refs"]]
            lines.append(f"Qualifies: {', '.join(qq)}")
        stags = claim.get("sensitive_topic_tags") or []
        if stags:
            lines.append(f"Sensitive Tags: {', '.join(str(t) for t in stags)}")
        if claim.get("confidence"):
            lines.append(f"Confidence: {claim['confidence']}")
        if claim.get("uncertainty_note"):
            lines.append(f"Uncertainty: {claim['uncertainty_note']}")
        lines.append(f"Investigative Direction: {claim.get('investigative_direction', '')}")
        lines.append("\n---\n")

    memes = [m for m in data.get("memes", []) if isinstance(m, dict)]
    if memes:
        lines.append("## 6. Meme Register\n")
        for m in memes:
            mid = (
                ref_to_id.get(m.get("ref", ""), m.get("ref", ""))
                or str(m.get("@id") or "").strip()
                or "?"
            )
            mtype = str(m.get("type") or "meme")
            term = str(m.get("canonical_term") or "")
            lines.append(f"**{mid}** ({mtype}) {term}\n")
            for i, occ in enumerate(m.get("occurrences") or [], 1):
                if not isinstance(occ, dict):
                    continue
                lines.append(f"### Occurrence {i}\n")
                if occ.get("video_timestamp"):
                    lines.append(f"Video Timestamp: {occ['video_timestamp']}")
                sp = occ.get("speaker_node_ref")
                if sp:
                    lines.append(
                        f"Speaker: {ref_to_id.get(str(sp).strip(), str(sp).strip())}"
                    )
                if occ.get("quote"):
                    lines.append(f"Quote: {occ['quote']}")
                if occ.get("context"):
                    lines.append(f"Context: {occ['context']}")
                tags = occ.get("tags")
                if tags:
                    lines.append(f"Tags: {', '.join(str(t) for t in tags)}")
                if occ.get("confidence"):
                    lines.append(f"Confidence: {occ['confidence']}")
                if occ.get("uncertainty_note"):
                    lines.append(f"Uncertainty: {occ['uncertainty_note']}")
                lines.append("")
            if m.get("context") and not any(
                isinstance(o, dict) and o.get("context") for o in (m.get("occurrences") or [])
            ):
                lines.append(f"Summary: {m['context']}\n")
            lines.append("---\n")

    legal = [x for x in (data.get("legal_matters") or []) if isinstance(x, dict)]
    if legal:
        lines.append("## 7. Legal Matter Register\n")
        for lm in legal:
            lid = ref_to_id.get(lm.get("ref", ""), lm.get("ref", ""))
            lines.append(f"**{lid}** {lm.get('name', '')}\n")
            pn = [ref_to_id.get(r, r) for r in lm.get("party_node_refs") or []]
            pl = [ref_to_id.get(r, r) for r in lm.get("place_node_refs") or []]
            ar = [ref_to_id.get(r, r) for r in lm.get("artifact_refs") or []]
            if pn:
                lines.append(f"Party Nodes: {', '.join(pn)}")
            if pl:
                lines.append(f"Place Nodes: {', '.join(pl)}")
            if ar:
                lines.append(f"Artifact Anchors: {', '.join(ar)}")
            if lm.get("description"):
                lines.append(f"Description: {lm['description']}")
            if lm.get("confidence"):
                lines.append(f"Confidence: {lm['confidence']}")
            if lm.get("uncertainty_note"):
                lines.append(f"Uncertainty: {lm['uncertainty_note']}")
            lines.append("---\n")

    org_rels = [x for x in (data.get("organization_relationships") or []) if isinstance(x, dict)]
    if org_rels:
        lines.append("## 8. Organization Network\n")
        for row in org_rels:
            a = ref_to_id.get(row.get("from_org_ref", ""), row.get("from_org_ref", ""))
            b = ref_to_id.get(row.get("to_org_ref", ""), row.get("to_org_ref", ""))
            rel = row.get("relation", "")
            lines.append(f"OrgLink: {a} {rel} {b}")
        lines.append("")

    roles = [x for x in (data.get("role_assertions") or []) if isinstance(x, dict)]
    if roles:
        lines.append("## 9. Role Assertions\n")
        for row in roles:
            p = ref_to_id.get(row.get("person_node_ref", ""), row.get("person_node_ref", ""))
            o = ref_to_id.get(row.get("org_node_ref", ""), row.get("org_node_ref", ""))
            edge = row.get("role_edge", "")
            title = (row.get("role_title") or "").strip()
            tail = f" title:{title}" if title else ""
            lines.append(f"RoleLink: {p} {edge} {o}{tail}")
        lines.append("")

    equiv = [x for x in (data.get("node_equivalences") or []) if isinstance(x, dict)]
    if equiv:
        lines.append("## 10. Node Equivalence (SAME_AS)\n")
        for row in equiv:
            a = ref_to_id.get(row.get("node_ref_a", ""), row.get("node_ref_a", ""))
            b = ref_to_id.get(row.get("node_ref_b", ""), row.get("node_ref_b", ""))
            lines.append(f"SameAs: {a} {b}")
        lines.append("")

    prov = [x for x in (data.get("provenance_links") or []) if isinstance(x, dict)]
    if prov:
        lines.append("## 11. Provenance Links\n")
        for row in prov:
            fr = ref_to_id.get(row.get("from_ref", ""), row.get("from_ref", ""))
            to = ref_to_id.get(row.get("to_ref", ""), row.get("to_ref", ""))
            rel = row.get("relation", "")
            lines.append(f"Prov: {fr} {rel} {to}")
        lines.append("")

    tmen = [x for x in (data.get("topic_mentions") or []) if isinstance(x, dict)]
    if tmen:
        lines.append("## 12. Topic Threading\n")
        for row in tmen:
            c = ref_to_id.get(row.get("claim_ref", ""), row.get("claim_ref", ""))
            t = ref_to_id.get(row.get("topic_node_ref", ""), row.get("topic_node_ref", ""))
            lines.append(f"TopicMention: {c} {t}")
        lines.append("")

    mlinks = [x for x in (data.get("meme_links") or []) if isinstance(x, dict)]
    if mlinks:
        lines.append("## 13. Meme Graph Links\n")
        for row in mlinks:
            mid = str(row.get("meme_ref") or "").strip()
            lt = row.get("link_type", "")
            if lt == "invoked_by_claim":
                cr = ref_to_id.get(row.get("claim_ref", ""), row.get("claim_ref", ""))
                lines.append(f"MemeLink: {mid} invoked_by_claim {cr}")
            elif lt == "invoked_by_speaker":
                sp = ref_to_id.get(row.get("speaker_node_ref", ""), row.get("speaker_node_ref", ""))
                lines.append(f"MemeLink: {mid} invoked_by_speaker {sp}")
            elif lt == "targets_node":
                tg = ref_to_id.get(row.get("target_node_ref", ""), row.get("target_node_ref", ""))
                lines.append(f"MemeLink: {mid} targets_node {tg}")
        lines.append("")

    return "\n".join(lines)


def _episode_num_from_path(p: Path) -> int:
    m = re.search(r"episode_(\d+)", p.name, re.I)
    return int(m.group(1)) if m else 0


def _remove_legacy_episode_markdown(drafts_dir: Path) -> list[Path]:
    """Remove episode_NNN_episode_NNN_*youtubeId*.md so Neo4j ingest / humans only see canonical names."""
    removed: list[Path] = []
    if not drafts_dir.is_dir():
        return removed
    for p in drafts_dir.glob("episode_*.md"):
        if p.is_file() and _LEGACY_EPISODE_DRAFT_MD.match(p.name):
            p.unlink()
            removed.append(p)
    return sorted(removed)


def run_batch(
    phase1_dir: Path,
    drafts_dir: Path,
    ledger_dir: Path | None,
    *,
    skip_validation: bool = False,
    fresh_ledger: bool = False,
    dedupe_nodes: bool = True,
    canonical_nodes: Path | None = None,
    episode_output_names: bool = False,
    inscription_dir_override: Path | None = None,
    keep_legacy_draft_md: bool = False,
) -> int:
    """Phase 2 batch: process all phase1 JSONs in episode order, single central ledger."""
    json_files = sorted(
        (p for p in phase1_dir.glob("episode_*.json") if "readme" not in p.name.lower()),
        key=_episode_num_from_path,
    )
    if not json_files:
        print(f"[assign_ids] No episode_*.json in {phase1_dir}")
        return 1

    if fresh_ledger and not keep_legacy_draft_md:
        pruned = _remove_legacy_episode_markdown(drafts_dir)
        if pruned:
            print(
                f"[assign_ids] --fresh-ledger: removed {len(pruned)} legacy draft(s) "
                f"(episode_NNN_episode_NNN_*.md — stale ID space). "
                f"Use --keep-legacy-draft-md to retain."
            )
            for p in pruned:
                print(f"  removed {p.name}")

    if fresh_ledger:
        ledger = {
            "next_artifact": 1000,
            "next_claim": 1000,
            "next_node": 1,
            "next_node_inv": 1000,
            "next_legal_matter": 1000,
        }
    elif ledger_dir and ledger_dir.exists() and scan_output_for_ids:
        highest = scan_output_for_ids(ledger_dir)
        ledger = {
            "next_artifact": int(highest["artifact_bundle"]) + 1,
            "next_claim": int(highest["claim"]) + 1,
            "next_node": int(highest["node"]) + 1,
            "next_node_inv": int(highest["node_investigation"]) + 1,
            "next_legal_matter": int(highest.get("legal_matter", 999)) + 1,
        }
    else:
        ledger = {
            "next_artifact": 1000,
            "next_claim": 1000,
            "next_node": 1,
            "next_node_inv": 1000,
            "next_legal_matter": 1000,
        }

    canon_path = canonical_nodes if canonical_nodes is not None else CANONICAL_NODES_DEFAULT
    node_name_registry: dict[tuple[str, str], str] = {}
    if dedupe_nodes:
        node_name_registry = load_node_registry_from_canonical(canon_path)
        if node_name_registry:
            print(f"[assign_ids] Seeded {len(node_name_registry)} name key(s) from {canon_path}")
            _bump_ledger_next_nodes_from_registry(ledger, node_name_registry)

    drafts_dir.mkdir(parents=True, exist_ok=True)
    # Always default inscription to project dir (not drafts_dir.parent) so --drafts /tmp/... still writes to project.
    inscription_dir = inscription_dir_override if inscription_dir_override is not None else (PROJECT_DIR / "inscription")
    inscription_dir.mkdir(parents=True, exist_ok=True)
    dinfo = "dedupe on" if dedupe_nodes else "dedupe off"
    print(
        f"[assign_ids] Batch: {len(json_files)} episode(s), "
        f"ledger A-{ledger['next_artifact']}, C-{ledger['next_claim']}, N-{ledger['next_node']} ({dinfo})"
    )

    for jpath in json_files:
        data = json.loads(jpath.read_text(encoding="utf-8"))
        _prepare_phase1_graph(data)
        ep = data.get("meta", {}).get("episode") or _episode_num_from_path(jpath)
        data.setdefault("meta", {})["episode"] = ep

        if not skip_validation:
            verrs = _phase1_validation_errors(data)
            if verrs:
                print(f"[assign_ids] Validation failed for {jpath.name}:")
                for line in verrs[:20]:
                    print(f"  {line}")
                if len(verrs) > 20:
                    print(f"  ... and {len(verrs) - 20} more")
                return 1

        ref_to_id, ledger = assign_ids_to_entities(
            data,
            ledger,
            dedupe_nodes=dedupe_nodes,
            node_name_registry=node_name_registry if dedupe_nodes else None,
        )
        markdown = render_markdown(data, ref_to_id)
        json_with_ids = apply_ids_to_json(data, ref_to_id)

        if episode_output_names:
            out_name = f"episode_{int(ep):03d}.md"
            json_name = f"episode_{int(ep):03d}.json"
        else:
            out_name = f"{jpath.stem}.md"
            json_name = f"{jpath.stem}.json"
        out_path = drafts_dir / out_name
        out_path.write_text(markdown, encoding="utf-8")
        print(f"  -> {out_name}")

        json_path = inscription_dir / json_name
        json_path.write_text(json.dumps(json_with_ids, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> inscription/{json_name}")

    print(f"[assign_ids] Done. Wrote {len(json_files)} draft(s) + JSON to drafts/ and inscription/")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Assign IDs from ledger to phase-1 entity extraction")
    ap.add_argument("input", type=Path, nargs="?", help="Phase 1 JSON file (or use --batch)")
    ap.add_argument("--batch", type=Path, metavar="DIR", help="Process all episode_*.json in DIR (Phase 2 batch)")
    ap.add_argument("--drafts", type=Path, default=DRAFTS_DIR, help="Output directory")
    ap.add_argument("--ledger", type=Path, help="Directory to scan for ledger state")
    ap.add_argument(
        "--fresh-ledger",
        action="store_true",
        help="Ignore scanned max IDs; start from series defaults; remove legacy episode_NNN_episode_NNN_*.md drafts",
    )
    ap.add_argument(
        "--keep-legacy-draft-md",
        action="store_true",
        help="With --fresh-ledger, do not delete legacy long-name episode markdown (not recommended)",
    )
    ap.add_argument(
        "--no-dedupe-nodes",
        action="store_true",
        help="Batch: assign a new N-* for every NODE_* (no cross-episode name reuse)",
    )
    ap.add_argument(
        "--dedupe-nodes",
        action="store_true",
        help="Single-file: reuse N-* when name matches registry (from --canonical-nodes or prior batch)",
    )
    ap.add_argument(
        "--canonical-nodes",
        type=Path,
        metavar="FILE",
        help=f"Seed dedupe registry from this JSON (default: {CANONICAL_NODES_DEFAULT})",
    )
    ap.add_argument(
        "--episode-output-names",
        action="store_true",
        help="Batch: write episode_NNN.md and inscription/episode_NNN.json",
    )
    ap.add_argument(
        "--inscription",
        type=Path,
        metavar="DIR",
        help=f"Batch: write inscription JSON here (default: {PROJECT_DIR / 'inscription'})",
    )
    ap.add_argument("--episode", type=int, help="Episode number (for single-file output filename)")
    ap.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip JSON Schema + reference integrity checks (not recommended)",
    )
    args = ap.parse_args()

    if args.batch:
        ledger_dir = None if args.fresh_ledger else (args.ledger or args.drafts)
        return run_batch(
            args.batch,
            args.drafts,
            ledger_dir,
            skip_validation=args.skip_validation,
            fresh_ledger=args.fresh_ledger,
            dedupe_nodes=not args.no_dedupe_nodes,
            canonical_nodes=args.canonical_nodes,
            episode_output_names=args.episode_output_names,
            inscription_dir_override=args.inscription,
            keep_legacy_draft_md=args.keep_legacy_draft_md,
        )

    # Single-file mode
    if not args.input or args.input == Path("-"):
        if args.input != Path("-"):
            print("[assign_ids] Need input file or --batch DIR")
            return 1
        data = json.load(sys.stdin)
    else:
        if not args.input.exists():
            print(f"[assign_ids] File not found: {args.input}")
            return 1
        data = json.loads(args.input.read_text(encoding="utf-8"))

    _prepare_phase1_graph(data)

    if not args.skip_validation:
        verrs = _phase1_validation_errors(data)
        if verrs:
            print("[assign_ids] Validation failed:")
            for line in verrs[:25]:
                print(f"  {line}")
            return 1

    if args.fresh_ledger:
        ledger = {
            "next_artifact": 1000,
            "next_claim": 1000,
            "next_node": 1,
            "next_node_inv": 1000,
            "next_legal_matter": 1000,
        }
    else:
        ledger_dir = args.ledger or args.drafts
        if scan_output_for_ids and ledger_dir.exists():
            ledger = get_ledger_state(ledger_dir)
        else:
            ledger = get_ledger_state(Path("."))

    canon_path = args.canonical_nodes if args.canonical_nodes is not None else CANONICAL_NODES_DEFAULT
    reg: dict[tuple[str, str], str] | None = None
    if args.dedupe_nodes:
        reg = load_node_registry_from_canonical(canon_path)
        if reg:
            print(f"[assign_ids] Dedupe: seeded {len(reg)} name key(s) from {canon_path}")
            _bump_ledger_next_nodes_from_registry(ledger, reg)

    ref_to_id, _ = assign_ids_to_entities(
        data,
        ledger,
        dedupe_nodes=bool(args.dedupe_nodes),
        node_name_registry=reg,
    )
    markdown = render_markdown(data, ref_to_id)

    ep = data.get("meta", {}).get("episode") or args.episode or 1
    out_name = f"episode_{ep:03d}_assigned.md"
    out_path = args.drafts / out_name
    args.drafts.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"[assign_ids] Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
