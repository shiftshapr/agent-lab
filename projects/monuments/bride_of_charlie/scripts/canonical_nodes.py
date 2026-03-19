"""
Canonical Node Dictionary & Learning System

Single source of truth for node names. Logs edge cases for human review
and all adjustments for learning.

Usage:
  # Ingest nodes from Phase 1 output (de-dup, log edge cases)
  python scripts/canonical_nodes.py ingest phase1_output/

  # List pending edge cases for review
  python scripts/canonical_nodes.py review --list

  # Resolve edge case (approve / edit / deny)
  python scripts/canonical_nodes.py review --resolve ec-20260318-001 approve
  python scripts/canonical_nodes.py review --resolve ec-20260318-001 edit "Erica Kirk"
  python scripts/canonical_nodes.py review --resolve ec-20260318-001 deny

  # Show adjustments log (learning)
  python scripts/canonical_nodes.py adjustments --tail 20

  # Export for transcript correction
  python scripts/canonical_nodes.py export-corrections
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CANONICAL_DIR = PROJECT_DIR / "canonical"
NODES_FILE = CANONICAL_DIR / "nodes.json"
EDGE_CASES_FILE = CANONICAL_DIR / "edge_cases.jsonl"
ADJUSTMENTS_FILE = CANONICAL_DIR / "adjustments.jsonl"
REVIEWED_FILE = CANONICAL_DIR / "reviewed.jsonl"


def _ensure_dir():
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)


def _load_nodes() -> dict:
    if not NODES_FILE.exists():
        return {
            "version": 1,
            "updated": datetime.now(timezone.utc).isoformat(),
            "next_person_id": 1,
            "next_investigation_id": 1000,
            "nodes": {},
        }
    return json.loads(NODES_FILE.read_text(encoding="utf-8"))


def _save_nodes(data: dict):
    _ensure_dir()
    data["updated"] = datetime.now(timezone.utc).isoformat()
    NODES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _next_edge_case_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = 0
    if EDGE_CASES_FILE.exists():
        for line in EDGE_CASES_FILE.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                count += 1
    return f"ec-{now}-{count + 1:03d}"


def _next_adj_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d")
    count = 0
    if ADJUSTMENTS_FILE.exists():
        for line in ADJUSTMENTS_FILE.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                count += 1
    return f"adj-{now}-{count + 1:03d}"


def collect_phase1_extraction_review_items(doc: dict) -> list[dict]:
    """
    Collect entities worth human review: confidence medium/low or any uncertainty_note.
    Used after successful Phase 1 save.
    """
    items: list[dict] = []

    def add(entity: str, ref: str, path: str, conf: str | None, note: str | None):
        if conf not in ("low", "medium") and not (note and str(note).strip()):
            return
        items.append(
            {
                "entity": entity,
                "ref": ref,
                "path": path,
                "confidence": conf,
                "uncertainty_note": (note or "").strip() or None,
            }
        )

    for i, c in enumerate(doc.get("claims", [])):
        add("claim", str(c.get("ref", f"#{i}")), f"claims[{i}]", c.get("confidence"), c.get("uncertainty_note"))
    for i, n in enumerate(doc.get("nodes", [])):
        add("node", str(n.get("ref", f"#{i}")), f"nodes[{i}]", n.get("confidence"), n.get("uncertainty_note"))
    for fi, fam in enumerate(doc.get("artifacts", [])):
        for si, sub in enumerate(fam.get("sub_items", [])):
            add(
                "artifact",
                str(sub.get("ref", f"{fi}.{si}")),
                f"artifacts[{fi}].sub_items[{si}]",
                sub.get("confidence"),
                sub.get("uncertainty_note"),
            )
    for mi, meme in enumerate(doc.get("memes", [])):
        mref = str(meme.get("ref", f"M#{mi}"))
        for oi, occ in enumerate(meme.get("occurrences", []) or []):
            add(
                "meme_occurrence",
                mref,
                f"memes[{mi}].occurrences[{oi}]",
                occ.get("confidence"),
                occ.get("uncertainty_note"),
            )
    return items


def log_phase1_validation_errors(episode: int, transcript_stem: str, errors: list[str]) -> str | None:
    """Queue schema/reference validation failures for human review. Returns edge_case id."""
    if not errors:
        return None
    candidates = [{"error": e[:500]} for e in errors[:50]]
    return log_edge_case(
        "phase1_validation",
        episode,
        f"Phase 1 validation failed for {transcript_stem} ({len(errors)} issue(s))",
        candidates,
        "fix_json_or_prompt_then_regenerate",
        "low",
    )


def log_extraction_review_batch(episode: int, transcript_stem: str, items: list[dict]) -> str | None:
    """Queue low/medium confidence or uncertainty_note extractions. Returns edge_case id."""
    if not items:
        return None
    return log_edge_case(
        "extraction_review",
        episode,
        f"Extraction confidence / uncertainty: {transcript_stem}",
        items,
        "human_verify_fields",
        "medium",
    )


def log_edge_case(
    case_type: str,
    episode: int,
    context: str,
    candidates: list[dict],
    suggested_action: str,
    auto_confidence: str = "low",
) -> str:
    """Log an edge case for human review. Returns edge_case_id."""
    _ensure_dir()
    ec_id = _next_edge_case_id()
    entry = {
        "id": ec_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": case_type,
        "episode": episode,
        "context": context,
        "candidates": candidates,
        "suggested_action": suggested_action,
        "status": "pending",
        "auto_confidence": auto_confidence,
    }
    with open(EDGE_CASES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return ec_id


def log_adjustment(
    edge_case_id: str,
    action: str,
    before: dict,
    after: dict,
    human_decision: str = "",
) -> str:
    """Log an adjustment for learning. Returns adjustment_id."""
    _ensure_dir()
    adj_id = _next_adj_id()
    entry = {
        "id": adj_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "edge_case_id": edge_case_id,
        "action": action,
        "before": before,
        "after": after,
        "human_decision": human_decision,
        "source": "human_review",
    }
    with open(ADJUSTMENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return adj_id


def _load_learning_denials() -> set[tuple[str, ...]]:
    """Load denied patterns from adjustments for learning."""
    denials = set()
    if not ADJUSTMENTS_FILE.exists():
        return denials
    for line in ADJUSTMENTS_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            adj = json.loads(line)
            if adj.get("action") == "denied":
                cands = adj.get("before", {}).get("candidates", [])
                if len(cands) >= 2:
                    names = tuple(sorted(c.get("name", "") for c in cands))
                    denials.add(names)
        except json.JSONDecodeError:
            pass
    return denials


def _load_learning_aliases() -> dict[str, str]:
    """Load approved alias mappings from adjustments (incorrect -> canonical)."""
    aliases = {}
    if not ADJUSTMENTS_FILE.exists():
        return aliases
    for line in ADJUSTMENTS_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            adj = json.loads(line)
            if adj.get("action") in ("approved", "edited"):
                after = adj.get("after", {})
                alias = after.get("alias_added") or after.get("before_name")
                canonical = after.get("canonical_name") or after.get("node_id")
                if alias and canonical:
                    aliases[alias] = canonical
        except json.JSONDecodeError:
            pass
    return aliases


def list_pending_edge_cases() -> list[dict]:
    """Return edge cases with status=pending."""
    if not EDGE_CASES_FILE.exists():
        return []
    pending = []
    for line in EDGE_CASES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            ec = json.loads(line)
            if ec.get("status") == "pending":
                pending.append(ec)
        except json.JSONDecodeError:
            pass
    return pending


def _update_edge_case_status(ec_id: str, status: str):
    """Update edge case status in file (rewrite)."""
    if not EDGE_CASES_FILE.exists():
        return
    lines = []
    for line in EDGE_CASES_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            ec = json.loads(line)
            if ec.get("id") == ec_id:
                ec["status"] = status
                ec["resolved_at"] = datetime.now(timezone.utc).isoformat()
            lines.append(json.dumps(ec, ensure_ascii=False))
        except json.JSONDecodeError:
            lines.append(line)
    EDGE_CASES_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_reviewed(ec_id: str, action: str, human_decision: str = ""):
    with open(REVIEWED_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "edge_case_id": ec_id,
            "action": action,
            "human_decision": human_decision,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False) + "\n")


def resolve_edge_case(ec_id: str, action: str, edit_value: str | None = None) -> bool:
    """Resolve an edge case: approve, edit, or deny. Returns True if found."""
    pending = list_pending_edge_cases()
    ec = next((e for e in pending if e["id"] == ec_id), None)
    if not ec:
        return False

    candidates = ec.get("candidates", [])
    before = {"candidates": [{"name": c.get("name"), "node_id": c.get("node_id")} for c in candidates], "type": ec.get("type")}
    data = _load_nodes()
    nodes = data["nodes"]

    if action == "deny":
        _update_edge_case_status(ec_id, "denied")
        log_adjustment(ec_id, "denied", before, {"action": "denied"}, "Human denied")
        _append_reviewed(ec_id, "denied")
        print(f"  Denied {ec_id}")
        return True

    if action == "approve":
        existing = next((c for c in candidates if c.get("node_id")), None)
        new_name = next((c.get("name") for c in candidates if not c.get("node_id")), None)
        if existing and new_name and existing.get("node_id"):
            nid = existing["node_id"]
            if nid in nodes and new_name not in nodes[nid].get("aliases", []):
                nodes[nid]["aliases"] = list(set(nodes[nid].get("aliases", []) + [new_name]))
                nodes[nid]["corrections"] = nodes[nid].get("corrections", []) + [
                    {"from": new_name, "to": existing.get("name"), "source": "human_review", "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
                ]
            after = {"canonical_name": existing.get("name"), "node_id": nid, "alias_added": new_name}
        else:
            after = {"canonical_name": edit_value or (candidates[0].get("name") if candidates else ""), "action": "approved"}
        _update_edge_case_status(ec_id, "approved")
        log_adjustment(ec_id, "approved", before, after, "Human approved")
        _append_reviewed(ec_id, "approved")
        _save_nodes(data)
        print(f"  Approved {ec_id}")
        return True

    if action == "edit" and edit_value:
        existing = next((c for c in candidates if c.get("node_id")), None)
        new_name = next((c.get("name") for c in candidates if not c.get("node_id")), None)
        if existing and existing.get("node_id") in nodes and new_name:
            nid = existing["node_id"]
            nodes[nid]["aliases"] = list(set(nodes[nid].get("aliases", []) + [new_name]))
            nodes[nid]["canonical_name"] = edit_value
            nodes[nid]["corrections"] = nodes[nid].get("corrections", []) + [
                {"from": new_name, "to": edit_value, "source": "human_review", "date": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
            ]
        after = {"canonical_name": edit_value, "action": "edited", "human_override": edit_value}
        _update_edge_case_status(ec_id, "edited")
        log_adjustment(ec_id, "edited", before, after, f"Human set to: {edit_value}")
        _append_reviewed(ec_id, "edited", edit_value)
        _save_nodes(data)
        print(f"  Edited {ec_id} -> {edit_value}")
        return True

    return False


def ingest_phase1_dir(phase1_dir: Path) -> int:
    """Ingest nodes from Phase 1 JSON files. De-dup, log edge cases. Returns count of edge cases logged."""
    data = _load_nodes()
    nodes = data["nodes"]
    next_person = data["next_person_id"]
    next_inv = data["next_investigation_id"]
    learning_denials = _load_learning_denials()
    learning_aliases = _load_learning_aliases()
    edge_count = 0

    json_files = sorted(phase1_dir.glob("episode_*.json"), key=lambda p: _ep_num(p))

    for jpath in json_files:
        ep = _ep_num(jpath)
        try:
            doc = json.loads(jpath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        for node in doc.get("nodes", []):
            ref = node.get("ref", "")
            name = (node.get("name") or "").strip()
            ntype = node.get("type", "person")
            if not name:
                continue

            # Check learning: is this a known alias?
            if name in learning_aliases:
                name = learning_aliases[name]

            # De-dup: exact match
            existing = next((nid for nid, n in nodes.items() if n.get("canonical_name") == name), None)
            if existing:
                nodes[existing]["episodes"] = sorted(set(nodes[existing].get("episodes", []) + [ep]))
                continue

            # De-dup: check aliases
            existing = next(
                (nid for nid, n in nodes.items() if name in n.get("aliases", [])),
                None,
            )
            if existing:
                nodes[existing]["episodes"] = sorted(set(nodes[existing].get("episodes", []) + [ep]))
                continue

            # Potential merge: similar name (simple check)
            similar = [
                (nid, n) for nid, n in nodes.items()
                if _names_similar(name, n.get("canonical_name", ""))
                or name in n.get("aliases", [])
            ]
            if similar:
                # Edge case: might be same person
                pair = tuple(sorted([name, similar[0][1].get("canonical_name", "")]))
                if pair not in learning_denials:
                    ec_id = log_edge_case(
                        "de_dup_candidate",
                        ep,
                        f"Phase 1 episode_{ep}",
                        [
                            {"name": name, "node_id": None, "source": f"episode_{ep}"},
                            {"name": similar[0][1]["canonical_name"], "node_id": similar[0][0], "source": "canonical"},
                        ],
                        "merge",
                        "low",
                    )
                    edge_count += 1
                    continue  # Don't add until human resolves

            # New node
            if "investigation" in str(ntype).lower() or (ref and re.match(r"NODE_1\d{3}", ref)):
                nid = f"N-{next_inv}"
                next_inv += 1
            else:
                nid = f"N-{next_person}"
                next_person += 1

            conf = "low" if _is_low_confidence(name, ep, nodes) else "medium"
            nodes[nid] = {
                "canonical_name": name,
                "type": "person" if "investigation" not in str(ntype).lower() else "investigation_target",
                "aliases": [],
                "confidence": conf,
                "first_seen_episode": ep,
                "episodes": [ep],
                "corrections": [],
            }
            if conf == "low":
                log_edge_case(
                    "low_confidence",
                    ep,
                    f"Phase 1 episode_{ep}",
                    [{"name": name, "node_id": nid, "source": f"episode_{ep}"}],
                    "verify",
                    "low",
                )
                edge_count += 1

    data["nodes"] = nodes
    data["next_person_id"] = next_person
    data["next_investigation_id"] = next_inv
    _save_nodes(data)
    return edge_count


def _ep_num(p: Path) -> int:
    m = re.search(r"episode_(\d+)", p.name, re.I)
    return int(m.group(1)) if m else 0


def _is_low_confidence(name: str, episode: int, nodes: dict) -> bool:
    """Heuristic: single-word names, unusual chars, or rare patterns."""
    if len(name) < 4:
        return True
    parts = name.split()
    if len(parts) < 2:  # Single name
        return True
    if any(not c.isalnum() and c not in " -'" for c in name):  # Unusual chars
        return True
    return False


def _names_similar(a: str, b: str) -> bool:
    """Simple similarity: same first+last, or one contains the other."""
    if a.lower() == b.lower():
        return True
    a_parts = set(a.lower().split())
    b_parts = set(b.lower().split())
    overlap = a_parts & b_parts
    return len(overlap) >= 2 or (len(overlap) == 1 and len(a_parts) <= 2 and len(b_parts) <= 2)


def export_corrections() -> list[tuple[str, str]]:
    """Export (incorrect, correct) pairs from canonical nodes for transcript correction."""
    data = _load_nodes()
    pairs = []
    for nid, node in data.get("nodes", {}).items():
        canonical = node.get("canonical_name", "")
        for alias in node.get("aliases", []):
            if alias != canonical:
                pairs.append((alias, canonical))
        for corr in node.get("corrections", []):
            fr = corr.get("from", "")
            to = corr.get("to", canonical)
            if fr and fr != to:
                pairs.append((fr, to))
    return pairs


def main():
    parser = argparse.ArgumentParser(description="Canonical node dictionary & learning")
    sub = parser.add_subparsers(dest="cmd")

    # Ingest
    ing = sub.add_parser("ingest", help="Ingest nodes from Phase 1 output")
    ing.add_argument("dir", type=Path, help="phase1_output/ directory")
    ing.add_argument("--project", type=Path, default=PROJECT_DIR, help="Project root")

    # Review
    rev = sub.add_parser("review", help="Review edge cases")
    rev.add_argument("--list", action="store_true", help="List pending")
    rev.add_argument("--resolve", nargs="+", metavar="ARG", help="Resolve: EC_ID approve | EC_ID edit NAME | EC_ID deny")

    # Adjustments
    adj = sub.add_parser("adjustments", help="View adjustments log")
    adj.add_argument("--tail", type=int, default=0, help="Show last N entries")

    # Export
    exp = sub.add_parser("export-corrections", help="Export corrections for transcript apply")

    args = parser.parse_args()

    if args.cmd == "ingest":
        edge_count = ingest_phase1_dir(args.dir)
        print(f"Ingested from {args.dir}. Edge cases logged: {edge_count}")
        if edge_count:
            print("  Run: python scripts/canonical_nodes.py review --list")

    elif args.cmd == "review":
        if args.list:
            pending = list_pending_edge_cases()
            if not pending:
                print("No pending edge cases.")
                return
            print(f"Pending edge cases ({len(pending)}):\n")
            for ec in pending:
                print(f"  {ec['id']} [{ec['type']}] {ec.get('suggested_action', '?')}")
                for c in ec.get("candidates", []):
                    print(f"    - {c.get('name')} ({c.get('node_id', 'new')})")
                print()

        elif args.resolve:
            ec_id = args.resolve[0]
            action = args.resolve[1].lower() if len(args.resolve) > 1 else ""
            edit_val = " ".join(args.resolve[2:]) if action == "edit" and len(args.resolve) > 2 else None
            if action == "edit" and not edit_val:
                print("edit requires value: review --resolve EC_ID edit 'Canonical Name'")
                sys.exit(1)
            if resolve_edge_case(ec_id, action, edit_val):
                print(f"Resolved {ec_id}")
            else:
                print(f"Edge case {ec_id} not found or not pending")
                sys.exit(1)

    elif args.cmd == "adjustments":
        if not ADJUSTMENTS_FILE.exists():
            print("No adjustments yet.")
            return
        lines = ADJUSTMENTS_FILE.read_text(encoding="utf-8").strip().split("\n")
        lines = [l for l in lines if l]
        if args.tail:
            lines = lines[-args.tail:]
        print(f"Adjustments (last {len(lines)}):\n")
        for line in lines:
            adj = json.loads(line)
            print(f"  {adj['id']} [{adj['action']}] {adj.get('edge_case_id', '')}")
            print(f"    {adj.get('human_decision', adj.get('after', {}))}")
            print()

    elif args.cmd == "export-corrections":
        pairs = export_corrections()
        for inc, cor in pairs:
            print(f"{inc}\t{cor}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
