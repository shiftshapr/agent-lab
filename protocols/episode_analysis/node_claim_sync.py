"""
Keep node.related_claims consistent with claims[].related_nodes during episode generation.

Policy (matches Draft Editor hub ``_claim_applies_to_node``):
- If a claim lists a non-empty ``related_nodes``, only those node refs may reference the claim
  from ``node.related_claims``. Other nodes drop that claim id.
- If ``related_nodes`` is empty or missing, the model's ``node.related_claims`` entries are kept
  (legacy / underspecified claims).
- Optionally add reverse edges: every ``claim.related_nodes`` entry gets the claim ref appended
  to that node's ``related_claims`` if missing.
- **Dangling claim refs**: Remove any ``related_claims`` entry that is not a key in ``claims[]``
  (fixes ``node_claim_missing`` in hub checks and Phase 1 ``check_reference_integrity`` for nodes
  and artifact sub-items).

Operates on **phase-1** JSON (NODE_*, CLAIM_* refs) before ``assign_ids_to_entities`` / markdown render.
"""

from __future__ import annotations

from typing import Any


def sync_placeholder_refs_from_jsonld(data: dict[str, Any]) -> None:
    """Copy @id into family_ref / ref / claim ref when the model omitted placeholder fields (in-place)."""
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


def _as_id_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        s = val.strip()
        return [s] if s else []
    return [str(x).strip() for x in val if x is not None and str(x).strip()]


def _node_ref(node: dict[str, Any]) -> str:
    return str(node.get("ref") or node.get("@id") or "").strip()


def _claim_ref(claim: dict[str, Any]) -> str:
    return str(claim.get("ref") or claim.get("@id") or "").strip()


def claim_lists_node(claim: dict[str, Any], node_ref: str) -> bool:
    """True if this node may list this claim on related_claims."""
    rel = _as_id_list(claim.get("related_nodes"))
    if not rel:
        return True
    return node_ref in rel


def sanitize_node_claim_graph_phase1(
    data: dict[str, Any], *, add_claim_backlinks: bool = True
) -> list[str]:
    """
    Mutate ``data`` in place. Returns human-readable log lines (drops + optional backlink adds).
    """
    log: list[str] = []
    claims = [c for c in (data.get("claims") or []) if isinstance(c, dict)]
    claims_by_ref: dict[str, dict[str, Any]] = {}
    for c in claims:
        cr = _claim_ref(c)
        if cr:
            claims_by_ref[cr] = c

    nodes = [n for n in (data.get("nodes") or []) if isinstance(n, dict)]

    # 0) Artifact sub-items: drop related_claims that are not in claims[]
    for fam in data.get("artifacts") or []:
        if not isinstance(fam, dict):
            continue
        for sub in fam.get("sub_items") or []:
            if not isinstance(sub, dict):
                continue
            sref = _node_ref(sub) or str(fam.get("family_ref") or fam.get("@id") or "").strip()
            kept_a: list[str] = []
            for cref in _as_id_list(sub.get("related_claims")):
                if cref not in claims_by_ref:
                    log.append(f"drop {sref or '?'} -> {cref} (no such claim in claims[])")
                    continue
                kept_a.append(cref)
            sub["related_claims"] = kept_a

    # 1) Drop node -> claim where claim.related_nodes is non-empty and omits this node;
    #    drop node -> claim when claim id is missing from claims[]
    for node in nodes:
        nr = _node_ref(node)
        if not nr:
            continue
        kept: list[str] = []
        for cref in _as_id_list(node.get("related_claims")):
            c = claims_by_ref.get(cref)
            if c is None:
                log.append(f"drop {nr} -> {cref} (no such claim in claims[])")
                continue
            if claim_lists_node(c, nr):
                kept.append(cref)
            else:
                log.append(f"drop {nr} -> {cref} (claim.related_nodes does not include {nr})")
        node["related_claims"] = kept

    # 2) Append claim ref onto each node in claim.related_nodes (symmetry)
    if add_claim_backlinks:
        for c in claims:
            cref = _claim_ref(c)
            if not cref:
                continue
            for nr in _as_id_list(c.get("related_nodes")):
                target = next((n for n in nodes if _node_ref(n) == nr), None)
                if not target:
                    continue
                rc = list(_as_id_list(target.get("related_claims")))
                if cref not in rc:
                    rc.append(cref)
                    target["related_claims"] = rc
                    log.append(f"add {nr} -> {cref} (backlink from claim.related_nodes)")

    return log


def sanitize_node_claim_graph_final(
    data: dict[str, Any], *, add_claim_backlinks: bool = True
) -> list[str]:
    """
    Same policy for **final** inscription JSON (N-*, C-* ids). Mutates in place.
    Use after ``apply_ids_to_json`` if the graph was built without phase-1 sanitization.
    """
    log: list[str] = []
    claims = [c for c in (data.get("claims") or []) if isinstance(c, dict)]
    claims_by_id: dict[str, dict[str, Any]] = {}
    for c in claims:
        cid = str(c.get("@id") or c.get("ref") or "").strip()
        if cid:
            claims_by_id[cid] = c

    nodes = [n for n in (data.get("nodes") or []) if isinstance(n, dict)]

    for fam in data.get("artifacts") or []:
        if not isinstance(fam, dict):
            continue
        for sub in fam.get("sub_items") or []:
            if not isinstance(sub, dict):
                continue
            sid = str(sub.get("@id") or sub.get("ref") or "").strip() or "?"
            kept_a: list[str] = []
            for cid in _as_id_list(sub.get("related_claims")):
                if cid not in claims_by_id:
                    log.append(f"drop {sid} -> {cid} (no such claim in claims[])")
                    continue
                kept_a.append(cid)
            sub["related_claims"] = kept_a

    for node in nodes:
        nid = str(node.get("@id") or node.get("ref") or "").strip()
        if not nid:
            continue
        kept: list[str] = []
        for cid in _as_id_list(node.get("related_claims")):
            c = claims_by_id.get(cid)
            if c is None:
                log.append(f"drop {nid} -> {cid} (no such claim in claims[])")
                continue
            reln = _as_id_list(c.get("related_nodes"))
            if not reln or nid in reln:
                kept.append(cid)
            else:
                log.append(f"drop {nid} -> {cid} (claim.related_nodes does not include {nid})")
        node["related_claims"] = kept

    if add_claim_backlinks:
        for c in claims:
            cid = str(c.get("@id") or c.get("ref") or "").strip()
            if not cid:
                continue
            for nid in _as_id_list(c.get("related_nodes")):
                target = next(
                    (n for n in nodes if str(n.get("@id") or n.get("ref") or "").strip() == nid),
                    None,
                )
                if not target:
                    continue
                rc = list(_as_id_list(target.get("related_claims")))
                if cid not in rc:
                    rc.append(cid)
                    target["related_claims"] = rc
                    log.append(f"add {nid} -> {cid} (backlink from claim.related_nodes)")

    return log
