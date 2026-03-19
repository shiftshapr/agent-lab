"""
Phase 1 JSON validation: JSON Schema + same-episode reference integrity.

Used after LLM extraction (before persisting Phase 1) and optionally before Phase 2.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_ART_FAMILY = re.compile(r"^ART_\d+$")
_ART_SUB = re.compile(r"^ART_\d+\.\d+$")
_CLAIM = re.compile(r"^CLAIM_\d+$")
_NODE = re.compile(r"^NODE_(\d+|1\d{3})$")


def _collect_defined_refs(data: dict[str, Any]) -> tuple[set[str], set[str], set[str], set[str]]:
    """artifact families, artifact sub_items, claims, nodes."""
    families: set[str] = set()
    subs: set[str] = set()
    for art in data.get("artifacts", []):
        fr = art.get("family_ref")
        if fr:
            families.add(str(fr))
        for sub in art.get("sub_items", []):
            r = sub.get("ref")
            if r:
                subs.add(str(r))
    claims = {str(c["ref"]) for c in data.get("claims", []) if c.get("ref")}
    nodes = {str(n["ref"]) for n in data.get("nodes", []) if n.get("ref")}
    return families, subs, claims, nodes


def _check_artifact_ref(ref: str, families: set[str], subs: set[str]) -> bool:
    if _ART_SUB.match(ref):
        return ref in subs
    if _ART_FAMILY.match(ref):
        return ref in families
    return False


def check_reference_integrity(data: dict[str, Any], label: str = "") -> list[str]:
    """
    Ensure cross-references point to entities defined in this document.
    Returns human-readable error lines (empty if OK).
    """
    prefix = f"{label}: " if label else ""
    families, subs, claims, nodes = _collect_defined_refs(data)
    errors: list[str] = []

    def bad(msg: str) -> None:
        errors.append(f"{prefix}{msg}")

    for i, claim in enumerate(data.get("claims", []), 1):
        cref = claim.get("ref") or f"claim#{i}"
        for r in claim.get("anchored_artifacts", []) or []:
            r = str(r)
            if not _check_artifact_ref(r, families, subs):
                bad(f"{cref} anchored_artifacts: unknown or missing artifact ref {r!r}")
        for r in claim.get("related_nodes", []) or []:
            r = str(r)
            if r not in nodes:
                bad(f"{cref} related_nodes: unknown node ref {r!r}")
        for key in ("contradicts_claim_refs", "supports_claim_refs"):
            for r in claim.get(key, []) or []:
                r = str(r)
                if r not in claims:
                    bad(f"{cref} {key}: unknown claim ref {r!r}")
                elif r == claim.get("ref"):
                    bad(f"{cref} {key}: must not reference itself ({r!r})")

    for fi, art in enumerate(data.get("artifacts", []), 1):
        fam = art.get("family_ref") or f"family#{fi}"
        for si, sub in enumerate(art.get("sub_items", []), 1):
            sref = sub.get("ref") or f"{fam}.{si}"
            for r in sub.get("related_claims", []) or []:
                r = str(r)
                if r not in claims:
                    bad(f"{sref} related_claims: unknown claim ref {r!r}")
            for r in sub.get("related_nodes", []) or []:
                r = str(r)
                if r not in nodes:
                    bad(f"{sref} related_nodes: unknown node ref {r!r}")
            for r in sub.get("same_as_artifact_refs", []) or []:
                r = str(r)
                if r not in subs:
                    bad(f"{sref} same_as_artifact_refs: unknown artifact sub ref {r!r}")
                if r == sub.get("ref"):
                    bad(f"{sref} same_as_artifact_refs: must not reference itself ({r!r})")

    for i, node in enumerate(data.get("nodes", []), 1):
        nref = node.get("ref") or f"node#{i}"
        for r in node.get("related_artifacts", []) or []:
            r = str(r)
            if not _check_artifact_ref(r, families, subs):
                bad(f"{nref} related_artifacts: unknown artifact ref {r!r}")
        for r in node.get("related_claims", []) or []:
            r = str(r)
            if r not in claims:
                bad(f"{nref} related_claims: unknown claim ref {r!r}")

    for mi, meme in enumerate(data.get("memes", []), 1):
        mid = meme.get("ref") or f"meme#{mi}"
        for oi, occ in enumerate(meme.get("occurrences", []) or [], 1):
            sp = occ.get("speaker_node_ref")
            if sp:
                sp = str(sp)
                if not _NODE.match(sp):
                    bad(f"{mid} occurrence[{oi}] speaker_node_ref: invalid format {sp!r}")
                elif sp not in nodes:
                    bad(f"{mid} occurrence[{oi}] speaker_node_ref: unknown node {sp!r}")

    return errors


def validate_json_schema(data: dict[str, Any], schema_path: Path) -> list[str]:
    """Validate data against JSON Schema; return error lines."""
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema not installed; pip/uv add jsonschema"]

    try:
        import json

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except OSError as e:
        return [f"cannot read schema {schema_path}: {e}"]
    except json.JSONDecodeError as e:
        return [f"invalid schema JSON: {e}"]

    errors: list[str] = []
    validator = jsonschema.Draft7Validator(schema)
    for err in validator.iter_errors(data):
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"schema[{loc}]: {err.message}")
    return errors[:50]


def validate_phase1(
    data: dict[str, Any],
    schema_path: Path | None,
    *,
    check_refs: bool = True,
    check_schema: bool = True,
) -> list[str]:
    """
    Full Phase 1 validation. Returns a list of issues (empty if OK).
    If schema_path is None or missing, schema check is skipped.
    """
    out: list[str] = []
    if check_schema and schema_path and schema_path.is_file():
        out.extend(validate_json_schema(data, schema_path))
    if check_refs:
        out.extend(check_reference_integrity(data))
    return out
