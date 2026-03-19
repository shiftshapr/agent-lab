"""
Two-Phase Generation: Assign IDs from Central Ledger

Phase 2 of two-phase generation. Reads entity extraction output (JSON from Phase 1)
and assigns A-, C-, N- IDs from the ledger. Outputs final markdown.

Batch mode (Phase 1 done for all episodes, then Phase 2 across batch):
  assign_ids.py --batch phase1_output/ --drafts drafts/

Single-file mode:
  assign_ids.py phase1_output.json --drafts drafts/

  --batch DIR     Process all episode_*.json in DIR (episode order), single ledger
  --drafts DIR    Where to write output (default: project drafts/)
  --ledger DIR    Scan this dir for ledger state if Neo4j unavailable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_DIR / "drafts"

# Reuse protocol's ledger logic
AGENT_LAB = PROJECT_DIR.parent.parent.parent
sys.path.insert(0, str(AGENT_LAB))
try:
    from protocols.episode_analysis.episode_analysis_protocol import (
        scan_output_for_ids,
        format_ledger_context,
    )
    from protocols.episode_analysis.phase1_validation import validate_phase1
except ImportError:
    scan_output_for_ids = None
    format_ledger_context = None
    validate_phase1 = None  # type: ignore[misc, assignment]

ENTITY_SCHEMA = PROJECT_DIR / "templates" / "entity_schema.json"


def _phase1_validation_errors(data: dict) -> list[str]:
    if not validate_phase1:
        return []
    return validate_phase1(
        data,
        ENTITY_SCHEMA if ENTITY_SCHEMA.is_file() else None,
    )


def get_ledger_state(output_dir: Path) -> dict:
    """Get next available IDs from Neo4j or file scan."""
    if scan_output_for_ids and output_dir.exists():
        highest = scan_output_for_ids(output_dir)
    else:
        highest = {"artifact_bundle": 999, "claim": 1000, "node": 0, "node_investigation": 1000}
    return {
        "next_artifact": int(highest["artifact_bundle"]) + 1,
        "next_claim": int(highest["claim"]) + 1,
        "next_node": int(highest["node"]) + 1,
        "next_node_inv": int(highest["node_investigation"]) + 1,
    }


def assign_ids_to_entities(data: dict, ledger: dict) -> tuple[dict, dict]:
    """
    Build ref -> real ID mappings.
    Returns (ref_to_id, updated_ledger).
    """
    ref_to_id: dict[str, str] = {}
    next_art = ledger["next_artifact"]
    next_claim = ledger["next_claim"]
    next_node = ledger["next_node"]
    next_node_inv = ledger["next_node_inv"]

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
        ntype = node.get("type", "person")
        if "investigation" in str(ntype).lower() or (ref and re.match(r"NODE_1\d{3}", ref)):
            ref_to_id[ref] = f"N-{next_node_inv}"
            next_node_inv += 1
        else:
            ref_to_id[ref] = f"N-{next_node}"
            next_node += 1

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
    node_ids = sorted([ref_to_id.get(n["ref"], n["ref"]) for n in data.get("nodes", []) if n.get("ref") in ref_to_id], key=lambda x: int(x.split("-")[1]))

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
            if sub.get("confidence"):
                lines.append(f"Confidence: {sub['confidence']}")
            if sub.get("uncertainty_note"):
                lines.append(f"Uncertainty: {sub['uncertainty_note']}")
            lines.append("")
        lines.append("---\n")

    lines.append("## 4. Node Register\n")
    for node in data.get("nodes", []):
        nid = ref_to_id.get(node.get("ref", ""), node.get("ref", ""))
        lines.append(f"**{nid}** {node.get('name', '')}\n")
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
        if claim.get("confidence"):
            lines.append(f"Confidence: {claim['confidence']}")
        if claim.get("uncertainty_note"):
            lines.append(f"Uncertainty: {claim['uncertainty_note']}")
        lines.append(f"Investigative Direction: {claim.get('investigative_direction', '')}")
        lines.append("\n---\n")

    return "\n".join(lines)


def _episode_num_from_path(p: Path) -> int:
    m = re.search(r"episode_(\d+)", p.name, re.I)
    return int(m.group(1)) if m else 0


def run_batch(
    phase1_dir: Path,
    drafts_dir: Path,
    ledger_dir: Path | None,
    *,
    skip_validation: bool = False,
) -> int:
    """Phase 2 batch: process all phase1 JSONs in episode order, single central ledger."""
    json_files = sorted(
        phase1_dir.glob("episode_*.json"),
        key=_episode_num_from_path,
    )
    if not json_files:
        print(f"[assign_ids] No episode_*.json in {phase1_dir}")
        return 1

    if ledger_dir and ledger_dir.exists() and scan_output_for_ids:
        highest = scan_output_for_ids(ledger_dir)
        ledger = {
            "next_artifact": int(highest["artifact_bundle"]) + 1,
            "next_claim": int(highest["claim"]) + 1,
            "next_node": int(highest["node"]) + 1,
            "next_node_inv": int(highest["node_investigation"]) + 1,
        }
    else:
        ledger = {
            "next_artifact": 1000,
            "next_claim": 1000,
            "next_node": 1,
            "next_node_inv": 1000,
        }

    drafts_dir.mkdir(parents=True, exist_ok=True)
    inscription_dir = drafts_dir.parent / "inscription"
    inscription_dir.mkdir(parents=True, exist_ok=True)
    print(f"[assign_ids] Batch: {len(json_files)} episode(s), ledger A-{ledger['next_artifact']}, C-{ledger['next_claim']}")

    for jpath in json_files:
        data = json.loads(jpath.read_text(encoding="utf-8"))
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

        ref_to_id, ledger = assign_ids_to_entities(data, ledger)
        markdown = render_markdown(data, ref_to_id)
        json_with_ids = apply_ids_to_json(data, ref_to_id)

        out_name = f"{jpath.stem}.md"
        out_path = drafts_dir / out_name
        out_path.write_text(markdown, encoding="utf-8")
        print(f"  -> {out_name}")

        json_name = f"{jpath.stem}.json"
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
    ap.add_argument("--episode", type=int, help="Episode number (for single-file output filename)")
    ap.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip JSON Schema + reference integrity checks (not recommended)",
    )
    args = ap.parse_args()

    if args.batch:
        ledger_dir = args.ledger or args.drafts
        return run_batch(
            args.batch,
            args.drafts,
            ledger_dir,
            skip_validation=args.skip_validation,
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

    if not args.skip_validation:
        verrs = _phase1_validation_errors(data)
        if verrs:
            print("[assign_ids] Validation failed:")
            for line in verrs[:25]:
                print(f"  {line}")
            return 1

    ledger_dir = args.ledger or args.drafts
    if scan_output_for_ids and ledger_dir.exists():
        highest = scan_output_for_ids(ledger_dir)
        ledger = get_ledger_state(ledger_dir)
    else:
        ledger = get_ledger_state(Path("."))

    ref_to_id, _ = assign_ids_to_entities(data, ledger)
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
