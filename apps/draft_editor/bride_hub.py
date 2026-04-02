"""
Bride of Charlie hub: cached index, activate-episode jobs, fileid resolution.

Phases 0–2 of the metawebbook hub plan (Draft Editor backend).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

_SCHEMA_VERSION = 5
_INDEX_SUBPATH = Path(".draft-editor-cache") / "bride_index.json"
_REGISTRY_REL = Path("config") / "episode_registry.json"
_LINKS_REL = Path("input") / "youtube_links.txt"
_JOB_MAX_AGE_SEC = 7200

_jobs_lock = threading.Lock()
_index_lock = threading.Lock()
_activate_lock = threading.Lock()  # youtube_links + registry writes

# --- paths ---


def bride_cache_dir(agent_lab_root: Path) -> Path:
    d = agent_lab_root / ".draft-editor-cache" / "bride-activate-jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def index_path(agent_lab_root: Path) -> Path:
    return agent_lab_root / _INDEX_SUBPATH


def _job_path(agent_lab_root: Path, job_id: str) -> Path | None:
    jid = re.sub(r"[^a-fA-F0-9]", "", job_id or "")
    if not jid or len(jid) > 32:
        return None
    return bride_cache_dir(agent_lab_root) / f"{jid.lower()}.json"


def _job_read(agent_lab_root: Path, job_id: str) -> dict[str, Any] | None:
    path = _job_path(agent_lab_root, job_id)
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _job_write(agent_lab_root: Path, job_id: str, data: dict[str, Any]) -> None:
    path = _job_path(agent_lab_root, job_id)
    if path is None:
        return
    with _jobs_lock:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)


def _prune_jobs(agent_lab_root: Path) -> None:
    d = bride_cache_dir(agent_lab_root)
    cutoff = time.time() - _JOB_MAX_AGE_SEC
    for p in d.glob("*.json"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink(missing_ok=True)
        except OSError:
            pass


# --- fingerprint ---


def _collect_watch_paths(bride: Path) -> list[Path]:
    roots = [
        bride / "inscription",
        bride / "transcripts",
        bride / "transcripts_corrected",
        bride / "phase1_output",
        bride / "drafts",
        bride / "config",
        bride / "input",
    ]
    out: list[Path] = []
    for r in roots:
        if r.is_dir():
            out.append(r)
    for name in (
        _REGISTRY_REL,
        _LINKS_REL,
        Path("config") / "editorial_transcript_rules.json",
        Path("config") / "transcript_suspicious_patterns.json",
    ):
        p = bride / name
        if p.is_file():
            out.append(p)
    return out


def compute_fingerprint(bride: Path) -> str:
    """Cheap change detector: max mtime + total size snapshot."""
    best: float = 0.0
    total_size = 0
    count = 0
    for base in _collect_watch_paths(bride):
        if base.is_file():
            try:
                st = base.stat()
                best = max(best, st.st_mtime)
                total_size += st.st_size
                count += 1
            except OSError:
                continue
            continue
        try:
            for p in base.rglob("*"):
                if p.is_file():
                    try:
                        st = p.stat()
                        best = max(best, st.st_mtime)
                        total_size += st.st_size
                        count += 1
                    except OSError:
                        continue
        except OSError:
            continue
    raw = f"{best:.6f}|{count}|{total_size}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


# --- file ids ---


def make_file_id(rel_under_bride: str) -> str:
    rel = rel_under_bride.strip().replace("\\", "/").lstrip("/")
    return hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16]


def timestamp_to_start_seconds(raw: str | None) -> int | None:
    """
    First clock time in a hub string → seconds from episode start for YouTube ``start=``.

    Handles ``22:04–22:17``, ``1:05:30``, ``23:15``, ``claim_timestamp``-style values.
    """
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    m3 = re.search(r"(?<![\d])(\d{1,2}):(\d{2}):(\d{2})(?![\d])", s)
    if m3:
        return (
            int(m3.group(1)) * 3600 + int(m3.group(2)) * 60 + int(m3.group(3))
        )
    m2 = re.search(r"(?<![\d])(\d{1,3}):(\d{2})(?![\d:])", s)
    if m2:
        return int(m2.group(1)) * 60 + int(m2.group(2))
    return None


def find_entity_in_inscription_data(
    data: dict[str, Any], entity_id: str
) -> tuple[str, dict[str, Any]] | None:
    """
    Return ``(kind, record)`` for ``entity_id`` in one inscription JSON document.

    ``kind`` is ``node`` | ``claim`` | ``artifact`` | ``artifact_family`` | ``meme``.
    """
    eid = (entity_id or "").strip()
    if not eid:
        return None

    def _nid(d: dict[str, Any]) -> str:
        return str(d.get("@id") or d.get("ref") or "").strip()

    for n in data.get("nodes") or []:
        if isinstance(n, dict) and _nid(n) == eid:
            return "node", n
    for c in data.get("claims") or []:
        if isinstance(c, dict) and _nid(c) == eid:
            return "claim", c
    for fam in data.get("artifacts") or []:
        if not isinstance(fam, dict):
            continue
        fam_id = str(fam.get("@id") or fam.get("family_ref") or "").strip()
        if fam_id == eid:
            return "artifact_family", fam
        for sub in fam.get("sub_items") or []:
            if isinstance(sub, dict) and _nid(sub) == eid:
                return "artifact", sub
    for m in data.get("memes") or []:
        if isinstance(m, dict) and _nid(m) == eid:
            return "meme", m
    return None


def _as_id_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [val.strip()] if val.strip() else []
    return [str(x).strip() for x in val if x is not None and str(x).strip()]


def collect_related_entity_ids(kind: str, record: dict[str, Any]) -> dict[str, list[str]]:
    """Cross-reference ids for modals (deduped, stable order)."""
    nodes: list[str] = []
    claims: list[str] = []
    arts: list[str] = []

    if kind == "node":
        nodes.extend(_as_id_list(record.get("related_nodes")))
        claims.extend(_as_id_list(record.get("related_claims")))
        arts.extend(_as_id_list(record.get("related_artifacts")))
    elif kind == "claim":
        arts.extend(_as_id_list(record.get("anchored_artifacts")))
        nodes.extend(_as_id_list(record.get("related_nodes")))
        claims.extend(_as_id_list(record.get("supports_claim_refs")))
        claims.extend(_as_id_list(record.get("contradicts_claim_refs")))
    elif kind == "artifact":
        claims.extend(_as_id_list(record.get("related_claims")))
        nodes.extend(_as_id_list(record.get("related_nodes")))
    elif kind == "artifact_family":
        for sub in record.get("sub_items") or []:
            if isinstance(sub, dict):
                sid = str(sub.get("@id") or sub.get("ref") or "").strip()
                if sid:
                    arts.append(sid)
    elif kind == "meme":
        for occ in record.get("occurrences") or []:
            if not isinstance(occ, dict):
                continue
            sp = occ.get("speaker_node_ref")
            if sp:
                nodes.append(str(sp).strip())

    def _dedupe(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return {
        "nodes": _dedupe(nodes),
        "claims": _dedupe(claims),
        "artifacts": _dedupe(arts),
    }


def transcript_and_timestamp_for_kind(
    kind: str, record: dict[str, Any]
) -> tuple[str | None, str | None]:
    """Return ``(transcript_snippet_or_text, raw_timestamp_string)``."""
    if kind == "artifact":
        return (
            record.get("transcript_snippet"),
            record.get("video_timestamp") or record.get("claim_timestamp"),
        )
    if kind == "claim":
        return (
            record.get("transcript_snippet"),
            record.get("video_timestamp") or record.get("claim_timestamp"),
        )
    if kind == "node":
        # Prefer inscription ``transcript_snippet`` / timestamps when present; else bio only (no seek).
        sn = (record.get("transcript_snippet") or "").strip() or None
        ts = record.get("video_timestamp") or record.get("claim_timestamp")
        ts_s = str(ts).strip() if ts not in (None, "") else None
        if sn or ts_s:
            return sn or (record.get("description") or "").strip() or None, ts_s
        return (record.get("description"), None)
    if kind == "artifact_family":
        return (record.get("bundle_name"), None)
    if kind == "meme":
        for occ in record.get("occurrences") or []:
            if not isinstance(occ, dict):
                continue
            q = (occ.get("quote") or "").strip()
            ts = occ.get("video_timestamp")
            ts_s = str(ts).strip() if ts not in (None, "") else None
            if q or ts_s:
                return (q or None, ts_s)
        ctx = (record.get("context") or "").strip()
        return (ctx or None, None)
    return None, None


def _claim_record_id(c: dict[str, Any]) -> str:
    return str(c.get("@id") or c.get("ref") or "").strip()


def _claims_index_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for c in data.get("claims") or []:
        if isinstance(c, dict):
            cid = _claim_record_id(c)
            if cid:
                out[cid] = c
    return out


def _claim_applies_to_node(claim: dict[str, Any], node_id: str) -> bool:
    """
    If a claim lists ``related_nodes``, only those ids are treated as anchored subjects.

    This drops stale edges such as ``N-1.related_claims`` containing ``C-1014`` when
    ``C-1014.related_nodes`` is only ``[N-2, N-9]`` (the claim is about Erika, not Charlie).
    When ``related_nodes`` is empty, we still honor ``node.related_claims`` (legacy rows).
    """
    rel = _as_id_list(claim.get("related_nodes"))
    if not rel:
        return True
    return node_id in rel


def _gather_node_claim_evidence(
    data: dict[str, Any], node_id: str, node_record: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Collect transcript lines + times from claims linked to this node.

    Always includes claims whose ``related_nodes`` contains this id. Also includes ids from
    ``node.related_claims`` only when the claim either has no ``related_nodes`` or lists this
    node among them (see ``_claim_applies_to_node``).
    """
    by_id = _claims_index_by_id(data)
    want: set[str] = set()
    for cid in _as_id_list(node_record.get("related_claims")):
        c = by_id.get(cid)
        if not c:
            continue
        if _claim_applies_to_node(c, node_id):
            want.add(cid)
    for c in data.get("claims") or []:
        if not isinstance(c, dict):
            continue
        cid = _claim_record_id(c)
        if cid and node_id in _as_id_list(c.get("related_nodes")):
            want.add(cid)
    rows: list[dict[str, Any]] = []
    for cid in sorted(want, key=lambda i: global_row_sort_key({"id": i, "episode": 0})):
        c = by_id.get(cid)
        if not c:
            continue
        text = (c.get("transcript_snippet") or "").strip()
        if not text:
            text = (c.get("claim") or "").strip()
        raw_ts = c.get("video_timestamp") or c.get("claim_timestamp")
        ts_str = str(raw_ts).strip() if raw_ts not in (None, "") else None
        start_sec = timestamp_to_start_seconds(ts_str)
        label = (c.get("label") or "").strip() or None
        rows.append(
            {
                "claim_id": cid,
                "label": label,
                "text": text or None,
                "video_timestamp_raw": ts_str,
                "start_seconds": start_sec,
            }
        )

    def _sk(r: dict[str, Any]) -> tuple[int, int]:
        s = r.get("start_seconds")
        if s is None:
            return (1, 0)
        return (0, int(s))

    rows.sort(key=_sk)
    return rows


def _primary_node_evidence(
    evidence: list[dict[str, Any]], node_record: dict[str, Any]
) -> dict[str, Any]:
    """Pick snippet + seek time: prefer text that matches the node's name, else first timestamped row."""
    if not evidence:
        raise ValueError("evidence must be non-empty")
    name = (node_record.get("name") or "").strip().lower()
    if name:
        parts = [p for p in re.split(r"\s+", name) if len(p) > 1]
        for row in evidence:
            t = (row.get("text") or "").lower()
            if not t:
                continue
            if name in t:
                return row
            for w in parts:
                if w in t:
                    return row
    for row in evidence:
        if row.get("start_seconds") is not None:
            return row
    return evidence[0]


NODE_CLAIM_SCREEN_HANDLING_POLICY: dict[str, Any] = {
    "server_auto_fixes": False,
    "summary": (
        "The API only reports issues; it does not rewrite inscription JSON. "
        "Fixes are editorial except where noted."
    ),
    "when_to_address": {
        "node_claim_subject_mismatch": (
            "Before treating node detail (transcript + seek) as authoritative for that pair, "
            "or during any inscription QA pass. Requires a human choice (see remediation.options)."
        ),
        "node_claim_missing": (
            "Immediately: either remove the stale claim id from the node or add the missing "
            "claim object to this file."
        ),
        "claim_node_missing": (
            "Immediately: fix the typo or add the missing node, or remove the bad id from the claim."
        ),
        "claim_node_backlink_missing": (
            "During graph cleanup or after errors are fixed. Usually add the claim id to the node "
            "(see remediation); low risk if claim.related_nodes is already correct."
        ),
        "inscription_unreadable": "Before any other QA: repair JSON or file permissions.",
    },
    "severity": {
        "error": "Inconsistency or broken reference; hub behavior may omit or mis-attribute evidence.",
        "warning": "Symmetric edge missing; hub may still resolve via claim.related_nodes alone.",
    },
}


def _remediation_for_node_claim_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Structured hints for humans or a future offline fix script (not applied by the server)."""
    kind = str(issue.get("kind") or "")
    ins = str(issue.get("inscription") or "")
    nid = issue.get("node_id")
    cid = issue.get("claim_id")

    if kind == "node_claim_subject_mismatch":
        return {
            "requires_editorial_choice": True,
            "hub_behavior": (
                "Detail view will not use this claim for this node until the graph agrees "
                "(_claim_applies_to_node)."
            ),
            "options": [
                {
                    "action": "add_node_to_claim_related_nodes",
                    "when": (
                        "The segment is relevant to this entity (e.g. spouse, series namesake, "
                        "same household) even if the quoted text names someone else."
                    ),
                    "edit": f"In {ins}, add {nid!r} to claim {cid!r}'s related_nodes array.",
                },
                {
                    "action": "remove_claim_from_node_related_claims",
                    "when": (
                        "The claim is only about other related_nodes; the node link was redundant "
                        "or mistaken."
                    ),
                    "edit": f"In {ins}, remove {cid!r} from node {nid!r}'s related_claims array.",
                },
            ],
        }

    if kind == "claim_node_backlink_missing":
        return {
            "requires_editorial_choice": False,
            "hub_behavior": (
                "Evidence still loads from claim.related_nodes for this node; the missing backlink "
                "only affects symmetry and some future queries."
            ),
            "recommended_action": "append_claim_to_node_related_claims",
            "edit": f"In {ins}, add {cid!r} to node {nid!r}'s related_claims array.",
        }

    if kind == "node_claim_missing":
        return {
            "requires_editorial_choice": True,
            "options": [
                {
                    "action": "remove_claim_id_from_node",
                    "when": "The claim id is obsolete or belongs in another episode file.",
                    "edit": f"In {ins}, remove {cid!r} from node {nid!r}'s related_claims.",
                },
                {
                    "action": "add_claim_to_file",
                    "when": "The claim should exist here but was never serialized.",
                    "edit": f"In {ins}, add a Claim object with @id/ref {cid!r} to the claims array.",
                },
            ],
        }

    if kind == "claim_node_missing":
        return {
            "requires_editorial_choice": True,
            "options": [
                {
                    "action": "remove_node_id_from_claim",
                    "when": "Typo or wrong episode.",
                    "edit": f"In {ins}, remove {nid!r} from claim {cid!r}'s related_nodes.",
                },
                {
                    "action": "add_node_to_file",
                    "when": "The node should exist in this episode.",
                    "edit": f"In {ins}, add a Node with @id/ref {nid!r} to the nodes array.",
                },
            ],
        }

    if kind in ("inscription_unreadable", "inscription_invalid"):
        return {
            "recommended_action": "repair_json",
            "edit": f"Fix JSON syntax or encoding for {ins!r}.",
        }

    return {"note": "No specific remediation template for this kind."}


def screen_node_claim_consistency(
    bride: Path, *, include_backlinks: bool = True
) -> dict[str, Any]:
    """
    Find inconsistencies between ``nodes[].related_claims`` and ``claims[].related_nodes``.

    * **node_claim_subject_mismatch** (error): Node lists a claim id, the claim exists and has a
      non-empty ``related_nodes``, but this node id is not in that list — the hub will not use
      that claim for this node's transcript/detail (same issue as Charlie vs C-1014 before a fix).
    * **node_claim_missing** (error): Node lists a claim id that does not exist in the file. The
      generator/repair path (``node_claim_sync`` / ``repair_inscription_node_claims.py``) drops these
      edges automatically so exports can pass validation.
    * **claim_node_missing** (error): Claim lists a node id that does not exist in the file.
    * **claim_node_backlink_missing** (warning): Claim lists a node in ``related_nodes`` but that
      node's ``related_claims`` does not include this claim (incomplete reverse edge).

    When ``include_backlinks`` is False, only the first three kinds are reported.

    Each issue includes a ``remediation`` object. The response includes ``handling_policy`` —
    the server does **not** auto-edit files.
    """
    issues: list[dict[str, Any]] = []

    def _add(
        kind: str,
        severity: str,
        *,
        episode: int,
        inscription: str,
        detail: str,
        **extra: Any,
    ) -> None:
        row: dict[str, Any] = {
            "kind": kind,
            "severity": severity,
            "episode": episode,
            "inscription": inscription,
            "detail": detail,
        }
        row.update(extra)
        issues.append(row)

    for p in sorted(bride.glob("inscription/episode_*.json")):
        rel_in = str(p.relative_to(bride)).replace("\\", "/")
        m = re.search(r"episode_(\d+)\.json$", p.name)
        ep = int(m.group(1)) if m else 0
        try:
            raw = p.read_text(encoding="utf-8")
            data = json.loads(raw)
        except OSError as e:
            _add(
                "inscription_unreadable",
                "error",
                episode=ep,
                inscription=rel_in,
                detail=str(e),
            )
            continue
        except json.JSONDecodeError as e:
            _add(
                "inscription_unreadable",
                "error",
                episode=ep,
                inscription=rel_in,
                detail=str(e),
            )
            continue

        if not isinstance(data, dict):
            _add(
                "inscription_invalid",
                "error",
                episode=ep,
                inscription=rel_in,
                detail="Root JSON value is not an object.",
            )
            continue

        by_id = _claims_index_by_id(data)
        nodes_by_id: dict[str, dict[str, Any]] = {}
        for n in data.get("nodes") or []:
            if isinstance(n, dict):
                nid = str(n.get("@id") or n.get("ref") or "").strip()
                if nid:
                    nodes_by_id[nid] = n

        for nid, n in nodes_by_id.items():
            for cid in _as_id_list(n.get("related_claims")):
                c = by_id.get(cid)
                if not c:
                    _add(
                        "node_claim_missing",
                        "error",
                        episode=ep,
                        inscription=rel_in,
                        node_id=nid,
                        claim_id=cid,
                        detail="Node references a claim id not present in this file's claims array.",
                    )
                    continue
                rel = _as_id_list(c.get("related_nodes"))
                if rel and nid not in rel:
                    _add(
                        "node_claim_subject_mismatch",
                        "error",
                        episode=ep,
                        inscription=rel_in,
                        node_id=nid,
                        claim_id=cid,
                        claim_related_nodes=rel,
                        detail="Node lists this claim but claim.related_nodes does not include this "
                        "node (while claim.related_nodes is non-empty).",
                    )

        if include_backlinks:
            for c in data.get("claims") or []:
                if not isinstance(c, dict):
                    continue
                cid = _claim_record_id(c)
                if not cid:
                    continue
                for nid in _as_id_list(c.get("related_nodes")):
                    node = nodes_by_id.get(nid)
                    if not node:
                        _add(
                            "claim_node_missing",
                            "error",
                            episode=ep,
                            inscription=rel_in,
                            claim_id=cid,
                            node_id=nid,
                            detail="Claim references a node id not present in this file's nodes array.",
                        )
                        continue
                    n_claims = _as_id_list(node.get("related_claims"))
                    if cid not in n_claims:
                        _add(
                            "claim_node_backlink_missing",
                            "warning",
                            episode=ep,
                            inscription=rel_in,
                            claim_id=cid,
                            node_id=nid,
                            detail="Claim lists this node in related_nodes but node's related_claims "
                            "does not include this claim.",
                        )

    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    by_kind: dict[str, int] = {}
    for it in issues:
        k = str(it.get("kind") or "unknown")
        by_kind[k] = by_kind.get(k, 0) + 1
        it["remediation"] = _remediation_for_node_claim_issue(it)

    return {
        "ok": len(errors) == 0,
        "issue_count": len(issues),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
        "by_kind": by_kind,
        "handling_policy": NODE_CLAIM_SCREEN_HANDLING_POLICY,
    }


def _load_bride_transcript_media_module(bride: Path) -> Any | None:
    script = bride / "scripts" / "bride_transcript_media.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("bride_transcript_media_hub", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resolve_entity_detail(
    bride: Path,
    agent_lab_root: Path,
    entity_id: str,
    *,
    episode_hint: int | None = None,
) -> dict[str, Any]:
    """
    Load inscription JSON(s) and return one entity for hub detail modals / API.

    Includes YouTube ``watch`` / ``embed`` URLs when ``video_id_for_episode`` resolves.
    """
    eid = (entity_id or "").strip()
    if not eid:
        return {"found": False, "error": "empty id"}

    paths: list[tuple[int, Path]] = []
    for p in sorted(bride.glob("inscription/episode_*.json")):
        m = re.search(r"episode_(\d+)\.json$", p.name)
        if not m:
            continue
        ep = int(m.group(1))
        if episode_hint is not None and ep != int(episode_hint):
            continue
        paths.append((ep, p))

    hit: tuple[str, dict[str, Any]] | None = None
    found_ep: int | None = None
    found_path: Path | None = None
    for ep, p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        hit = find_entity_in_inscription_data(data, eid)
        if hit:
            found_ep, found_path = ep, p
            break

    if not hit or found_path is None or found_ep is None:
        return {"found": False, "error": "not found", "id": eid}

    kind, record = hit
    rel_in_bride = str(found_path.relative_to(bride)).replace("\\", "/")
    fid = make_file_id(rel_in_bride)
    snip, ts_raw = transcript_and_timestamp_for_kind(kind, record)
    transcript_snippets: list[dict[str, Any]] | None = None
    start_sec: int | None = None

    if kind == "node":
        ev = _gather_node_claim_evidence(data, eid, record)
        if ev:
            transcript_snippets = ev
            prim = _primary_node_evidence(ev, record)
            if prim.get("text"):
                snip = prim["text"]
            else:
                for row in ev:
                    if row.get("text"):
                        snip = row["text"]
                        break
            ts_raw = prim.get("video_timestamp_raw") or ts_raw
            ps = prim.get("start_seconds")
            if ps is not None:
                start_sec = int(ps)
            else:
                start_sec = timestamp_to_start_seconds(ts_raw)
        else:
            start_sec = timestamp_to_start_seconds(ts_raw)
    else:
        start_sec = timestamp_to_start_seconds(ts_raw)

    media_mod = _load_bride_transcript_media_module(bride)
    video_id: str | None = None
    youtube: dict[str, str] | None = None
    if media_mod is not None:
        video_id = media_mod.video_id_for_episode(found_ep, bride)
        if video_id:
            youtube = media_mod.youtube_urls(video_id, start_sec)

    related = collect_related_entity_ids(kind, record)

    out: dict[str, Any] = {
        "found": True,
        "id": eid,
        "kind": kind,
        "episode": found_ep,
        "inscription_path": rel_in_bride,
        "inscription_file_id": fid,
        "record": record,
        "transcript_snippet": snip,
        "video_timestamp_raw": ts_raw,
        "start_seconds": start_sec,
        "video_id": video_id,
        "youtube": youtube,
        "related": related,
    }
    if transcript_snippets is not None:
        out["transcript_snippets"] = transcript_snippets
    return out


def _safe_bride_path(bride: Path, rel: str) -> Path | None:
    """Resolve rel under bride; reject traversal."""
    rel = rel.strip().replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        return None
    p = (bride / rel).resolve()
    try:
        bride_r = bride.resolve()
    except OSError:
        return None
    if bride_r not in p.parents and p != bride_r:
        return None
    return p


# --- registry & links ---


def _youtube_lines(project: Path) -> list[str]:
    path = project / _LINKS_REL
    if not path.is_file():
        return []
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def _parse_video_id(url: str) -> str | None:
    for p in (
        r"(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
    ):
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def parse_video_id_from_url(url: str) -> str | None:
    """Public alias for URL → 11-char YouTube video id."""
    return _parse_video_id(url)


def find_existing_episode_for_video_id(project: Path, video_id: str) -> int | None:
    """If ``video_id`` already appears in ``youtube_links.txt`` or registry, return its 1-based episode index."""
    vid = (video_id or "").strip()
    if not vid:
        return None
    for i, line in enumerate(_youtube_lines(project), start=1):
        if _parse_video_id(line) == vid:
            return i
    reg = load_registry(project)
    for e in reg.get("episodes") or []:
        try:
            if str(e.get("video_id") or "") == vid:
                return int(e["episode"])
        except (TypeError, ValueError):
            continue
    return None


def load_registry(project: Path) -> dict[str, Any]:
    path = project / _REGISTRY_REL
    if not path.is_file():
        return {"schema_version": 1, "episodes": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "episodes": []}


def save_registry(project: Path, doc: dict[str, Any]) -> None:
    path = project / _REGISTRY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def append_episode_activation(
    project: Path, youtube_url: str, video_id: str
) -> tuple[int, str]:
    """
    Append URL to youtube_links.txt and registry. Returns (episode_number, normalized_url).
    """
    norm = youtube_url.strip()
    if "watch?v=" not in norm and "youtu.be/" not in norm:
        norm = f"https://www.youtube.com/watch?v={video_id}"
    with _activate_lock:
        lines = _youtube_lines(project)
        ep = len(lines) + 1
        links_path = project / _LINKS_REL
        links_path.parent.mkdir(parents=True, exist_ok=True)
        # Preserve file: read raw, append line
        if links_path.is_file():
            raw = links_path.read_text(encoding="utf-8")
            if raw and not raw.endswith("\n"):
                raw += "\n"
        else:
            raw = (
                "# Bride of Charlie — YouTube episode links (one per line)\n"
                "# Lines starting with # are ignored.\n#\n"
            )
        raw += f"{norm}\n"
        tmp = links_path.with_suffix(".txt.tmp")
        tmp.write_text(raw, encoding="utf-8")
        tmp.replace(links_path)

        reg = load_registry(project)
        eps = list(reg.get("episodes") or [])
        eps.append(
            {
                "episode": ep,
                "youtube_url": norm,
                "video_id": video_id,
                "activated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        reg["episodes"] = eps
        save_registry(project, reg)
        return ep, norm


# --- extract entities from inscription ---


def _flatten_inscription_entities(data: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"nodes": [], "claims": [], "artifacts": [], "memes": []}
    for n in data.get("nodes") or []:
        if isinstance(n, dict) and n.get("@id"):
            out["nodes"].append(str(n["@id"]))
    for c in data.get("claims") or []:
        if isinstance(c, dict) and c.get("@id"):
            out["claims"].append(str(c["@id"]))
    for fam in data.get("artifacts") or []:
        if not isinstance(fam, dict):
            continue
        if fam.get("@id"):
            out["artifacts"].append(str(fam["@id"]))
        for sub in fam.get("sub_items") or []:
            if isinstance(sub, dict) and sub.get("@id"):
                out["artifacts"].append(str(sub["@id"]))
    for m in data.get("memes") or []:
        if isinstance(m, dict):
            mid = str(m.get("@id") or m.get("ref") or "").strip()
            if mid:
                out["memes"].append(mid)
    return out


def _trunc_label(val: Any, max_len: int) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _dedupe_preserve(xs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _cap_ids(xs: list[str], n: int = 10) -> list[str]:
    return xs[:n]


def _related_bundle_node(n: dict[str, Any]) -> dict[str, Any]:
    rn = _as_id_list(n.get("related_nodes"))
    rc = _as_id_list(n.get("related_claims"))
    ra = _as_id_list(n.get("related_artifacts"))
    return {
        "related_counts": {
            "nodes": len(rn),
            "claims": len(rc),
            "artifacts": len(ra),
        },
        "related": {
            "nodes": _cap_ids(rn),
            "claims": _cap_ids(rc),
            "artifacts": _cap_ids(ra),
        },
    }


def _related_bundle_claim(c: dict[str, Any]) -> dict[str, Any]:
    ra = _as_id_list(c.get("anchored_artifacts"))
    rn = _as_id_list(c.get("related_nodes"))
    other: list[str] = []
    other.extend(_as_id_list(c.get("supports_claim_refs")))
    other.extend(_as_id_list(c.get("contradicts_claim_refs")))
    other = _dedupe_preserve(other)
    return {
        "related_counts": {
            "nodes": len(rn),
            "claims": len(other),
            "artifacts": len(ra),
        },
        "related": {
            "nodes": _cap_ids(rn),
            "claims": _cap_ids(other),
            "artifacts": _cap_ids(ra),
        },
    }


def _related_bundle_artifact(sub: dict[str, Any]) -> dict[str, Any]:
    rc = _as_id_list(sub.get("related_claims"))
    rn = _as_id_list(sub.get("related_nodes"))
    return {
        "related_counts": {"nodes": len(rn), "claims": len(rc), "artifacts": 0},
        "related": {"nodes": _cap_ids(rn), "claims": _cap_ids(rc), "artifacts": []},
    }


def _related_bundle_meme(m: dict[str, Any]) -> dict[str, Any]:
    speakers: list[str] = []
    for occ in m.get("occurrences") or []:
        if not isinstance(occ, dict):
            continue
        sp = occ.get("speaker_node_ref")
        if sp:
            s = str(sp).strip()
            if s:
                speakers.append(s)
    speakers = _dedupe_preserve(speakers)
    return {
        "related_counts": {"nodes": len(speakers), "claims": 0, "artifacts": 0},
        "related": {"nodes": _cap_ids(speakers), "claims": [], "artifacts": []},
    }


def _related_bundle_family(fam: dict[str, Any]) -> dict[str, Any]:
    subs: list[str] = []
    for sub in fam.get("sub_items") or []:
        if isinstance(sub, dict):
            sid = str(sub.get("@id") or sub.get("ref") or "").strip()
            if sid:
                subs.append(sid)
    return {
        "related_counts": {"nodes": 0, "claims": 0, "artifacts": len(subs)},
        "related": {"nodes": [], "claims": [], "artifacts": _cap_ids(subs)},
    }


def _global_row_node(
    n: dict[str, Any], ep: int, ins_rel: str, ins_fid: str
) -> dict[str, Any]:
    rid = str(n.get("@id") or "").strip()
    rb = _related_bundle_node(n)
    return {
        "id": rid,
        "episode": ep,
        "inscription": ins_rel,
        "inscription_file_id": ins_fid,
        "entity_kind": "node",
        "title": str(n.get("name") or rid),
        "subtitle": _trunc_label(n.get("type") or n.get("@type"), 96),
        **rb,
    }


def _global_row_claim(
    c: dict[str, Any], ep: int, ins_rel: str, ins_fid: str
) -> dict[str, Any]:
    rid = str(c.get("@id") or "").strip()
    rb = _related_bundle_claim(c)
    return {
        "id": rid,
        "episode": ep,
        "inscription": ins_rel,
        "inscription_file_id": ins_fid,
        "entity_kind": "claim",
        "title": str(c.get("label") or rid),
        "subtitle": _trunc_label(c.get("claim"), 160),
        **rb,
    }


def _global_row_artifact_family(
    fam: dict[str, Any], ep: int, ins_rel: str, ins_fid: str
) -> dict[str, Any]:
    rid = str(fam.get("@id") or fam.get("family_ref") or "").strip()
    rb = _related_bundle_family(fam)
    return {
        "id": rid,
        "episode": ep,
        "inscription": ins_rel,
        "inscription_file_id": ins_fid,
        "entity_kind": "artifact_family",
        "title": str(fam.get("bundle_name") or rid),
        "subtitle": "Artifact family",
        **rb,
    }


def _global_row_meme(
    m: dict[str, Any], ep: int, ins_rel: str, ins_fid: str
) -> dict[str, Any]:
    rid = str(m.get("@id") or m.get("ref") or "").strip()
    occ = [x for x in (m.get("occurrences") or []) if isinstance(x, dict)]
    rb = _related_bundle_meme(m)
    n_occ = len(occ)
    sub_parts = [str(m.get("type") or "meme")]
    if n_occ:
        sub_parts.append(f"{n_occ} occurrence(s)")
    return {
        "id": rid,
        "episode": ep,
        "inscription": ins_rel,
        "inscription_file_id": ins_fid,
        "entity_kind": "meme",
        "title": str(m.get("canonical_term") or rid),
        "subtitle": _trunc_label(" · ".join(sub_parts), 120),
        **rb,
    }


def _global_row_artifact(
    sub: dict[str, Any], ep: int, ins_rel: str, ins_fid: str
) -> dict[str, Any]:
    rid = str(sub.get("@id") or sub.get("ref") or "").strip()
    rb = _related_bundle_artifact(sub)
    return {
        "id": rid,
        "episode": ep,
        "inscription": ins_rel,
        "inscription_file_id": ins_fid,
        "entity_kind": "artifact",
        "title": _trunc_label(sub.get("description"), 140) or rid,
        "subtitle": _trunc_label(sub.get("video_timestamp"), 48),
        **rb,
    }


def global_row_sort_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    """Numeric hub id first (N-2 before N-10; N-11 before N-1000; A-1000 before A-1000.1), then episode.

    Episode is secondary so cross-episode lists read in id order (N-11 after N-10, not after N-1006).
    """
    try:
        ep = int(row.get("episode") or 0)
    except (TypeError, ValueError):
        ep = 0
    eid = str(row.get("id") or "").strip()
    m = re.match(r"^([A-Za-z]+)-(\d+)(?:\.(\d+))?$", eid)
    if not m:
        return (10**9, 10**9, ep, eid)
    main = int(m.group(2))
    sub = int(m.group(3)) if m.group(3) is not None else -1
    return (main, sub, ep, eid)


# --- index build ---


def _glob_one(bride: Path, pattern: str) -> str | None:
    matches = sorted(bride.glob(pattern))
    if not matches:
        return None
    try:
        return str(matches[0].relative_to(bride)).replace("\\", "/")
    except ValueError:
        return None


def _glob_one_path(bride: Path, pattern: str) -> Path | None:
    matches = sorted(bride.glob(pattern))
    return matches[0] if matches else None


_TRANS_DIFF_MAX_CHARS = 450_000


def transcript_diff_for_episode(
    bride: Path,
    episode: int,
    *,
    normalize: bool = False,
    context_lines: int = 3,
) -> dict[str, Any]:
    """Unified diff between raw ``transcripts/`` and ``transcripts_corrected/`` for one episode."""
    import difflib
    import unicodedata

    if episode < 1:
        return {"error": "episode must be ≥ 1"}
    raw_glob = f"transcripts/episode_{episode:03d}_*.txt"
    cor_glob = f"transcripts_corrected/episode_{episode:03d}_*.txt"
    raw_p = _glob_one_path(bride, raw_glob)
    cor_p = _glob_one_path(bride, cor_glob)
    if not raw_p or not raw_p.is_file():
        return {"error": "raw transcript not found", "episode": episode}
    if not cor_p or not cor_p.is_file():
        return {"error": "enhanced transcript not found", "episode": episode}
    try:
        raw_text = raw_p.read_text(encoding="utf-8", errors="replace")
        cor_text = cor_p.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"error": str(e), "episode": episode}
    if normalize:
        raw_text = unicodedata.normalize("NFC", raw_text)
        cor_text = unicodedata.normalize("NFC", cor_text)
    a = raw_text.splitlines()
    b = cor_text.splitlines()
    raw_rel = str(raw_p.relative_to(bride)).replace("\\", "/")
    cor_rel = str(cor_p.relative_to(bride)).replace("\\", "/")
    n_ctx = max(0, min(int(context_lines), 100))
    lines = list(
        difflib.unified_diff(
            a,
            b,
            fromfile=raw_rel,
            tofile=cor_rel,
            lineterm="",
            n=n_ctx,
        )
    )
    unified = "\n".join(lines)
    truncated = len(unified) > _TRANS_DIFF_MAX_CHARS
    if truncated:
        unified = (
            unified[:_TRANS_DIFF_MAX_CHARS] + "\n\n... [truncated by server]\n"
        )
    return {
        "episode": episode,
        "raw_path": raw_rel,
        "enhanced_path": cor_rel,
        "normalize": normalize,
        "line_counts": {"raw": len(a), "enhanced": len(b), "diff_lines": len(lines)},
        "unified_diff": unified,
        "truncated": truncated,
    }


def _episode_numbers_from_inscriptions(bride: Path) -> list[int]:
    nums: list[int] = []
    for p in bride.glob("inscription/episode_*.json"):
        m = re.search(r"episode_(\d+)\.json$", p.name)
        if m:
            nums.append(int(m.group(1)))
    return sorted(set(nums))


def episode_numbers_for_ui(bride: Path) -> list[int]:
    """
    Same episode range as ``build_index`` (YouTube link lines, inscription files, registry).
    Used by the Draft Editor transcript tab so the episode dropdown matches the project.
    """
    lines = _youtube_lines(bride)
    ins_eps = _episode_numbers_from_inscriptions(bride)
    reg = load_registry(bride)
    reg_by_ep = {
        int(e["episode"]): e
        for e in (reg.get("episodes") or [])
        if e.get("episode") is not None
    }
    max_ep = max(
        [0, len(lines), max(ins_eps) if ins_eps else 0] + list(reg_by_ep.keys())
    )
    return list(range(1, max_ep + 1)) if max_ep else []


def build_index(bride: Path, agent_lab_root: Path) -> dict[str, Any]:
    fingerprint = compute_fingerprint(bride)
    try:
        rel_root = str(bride.resolve().relative_to(agent_lab_root.resolve())).replace(
            "\\", "/"
        )
    except ValueError:
        rel_root = str(bride.resolve()).replace("\\", "/")

    lines = _youtube_lines(bride)
    reg = load_registry(bride)
    reg_by_ep = {int(e["episode"]): e for e in (reg.get("episodes") or []) if e.get("episode") is not None}

    ins_eps = _episode_numbers_from_inscriptions(bride)
    max_ep = max([0, len(lines), max(ins_eps) if ins_eps else 0] + list(reg_by_ep.keys()))
    episode_nums = list(range(1, max_ep + 1)) if max_ep else []

    file_ids: dict[str, str] = {}
    episodes_out: list[dict[str, Any]] = []
    global_nodes: list[dict[str, Any]] = []
    global_claims: list[dict[str, Any]] = []
    global_artifacts: list[dict[str, Any]] = []
    global_memes: list[dict[str, Any]] = []

    def add_file_slot(key: str, rel: str | None) -> dict[str, Any]:
        if not rel:
            return {"role": key, "path": None, "exists": False, "file_id": None}
        exists = (bride / rel).is_file()
        fid = make_file_id(rel)
        file_ids[fid] = rel
        return {
            "role": key,
            "path": rel,
            "exists": exists,
            "file_id": fid,
        }

    for ep in episode_nums:
        vid = None
        url = None
        if 1 <= ep <= len(lines):
            url = lines[ep - 1]
            vid = _parse_video_id(url)
        if ep in reg_by_ep:
            url = reg_by_ep[ep].get("youtube_url") or url
            vid = reg_by_ep[ep].get("video_id") or vid or (url and _parse_video_id(url))

        ins_rel = f"inscription/episode_{ep:03d}.json"
        if not (bride / ins_rel).is_file():
            alt = f"inscription/episode_{ep}.json"
            ins_rel = alt if (bride / alt).is_file() else ins_rel

        raw_glob = f"transcripts/episode_{ep:03d}_*.txt"
        cor_glob = f"transcripts_corrected/episode_{ep:03d}_*.txt"
        phase_glob = f"phase1_output/episode_{ep:03d}_*.json"
        draft_glob = f"drafts/episode_{ep:03d}_*.md"

        ins_path = ins_rel if (bride / ins_rel).is_file() else None
        entities = {"nodes": [], "claims": [], "artifacts": [], "memes": []}
        if ins_path and (bride / ins_path).is_file():
            try:
                data = json.loads((bride / ins_path).read_text(encoding="utf-8"))
                entities = _flatten_inscription_entities(data)
                ins_fid = make_file_id(ins_path)
                ins_rel = str(ins_path).replace("\\", "/")
                for n in data.get("nodes") or []:
                    if isinstance(n, dict) and n.get("@id"):
                        global_nodes.append(_global_row_node(n, ep, ins_rel, ins_fid))
                for c in data.get("claims") or []:
                    if isinstance(c, dict) and c.get("@id"):
                        global_claims.append(_global_row_claim(c, ep, ins_rel, ins_fid))
                for m in data.get("memes") or []:
                    if isinstance(m, dict) and (m.get("@id") or m.get("ref")):
                        global_memes.append(_global_row_meme(m, ep, ins_rel, ins_fid))
                for fam in data.get("artifacts") or []:
                    if not isinstance(fam, dict):
                        continue
                    if fam.get("@id"):
                        global_artifacts.append(
                            _global_row_artifact_family(fam, ep, ins_rel, ins_fid)
                        )
                    for sub in fam.get("sub_items") or []:
                        if isinstance(sub, dict) and (
                            sub.get("@id") or sub.get("ref")
                        ):
                            global_artifacts.append(
                                _global_row_artifact(sub, ep, ins_rel, ins_fid)
                            )
            except (OSError, json.JSONDecodeError):
                pass

        ep_entry = {
            "episode": ep,
            "video_id": vid,
            "youtube_url": url,
            "files": {
                "raw_transcript": add_file_slot("raw_transcript", _glob_one(bride, raw_glob)),
                "enhanced_transcript": add_file_slot(
                    "enhanced_transcript", _glob_one(bride, cor_glob)
                ),
                "inscription": add_file_slot("inscription", ins_path),
                "phase1_output": add_file_slot(
                    "phase1_output", _glob_one(bride, phase_glob)
                ),
                "draft_markdown": add_file_slot(
                    "draft_markdown", _glob_one(bride, draft_glob)
                ),
                "suspicious_patterns": add_file_slot(
                    "suspicious_patterns",
                    "config/transcript_suspicious_patterns.json"
                    if (bride / "config" / "transcript_suspicious_patterns.json").is_file()
                    else None,
                ),
                "editorial_transcript_rules": add_file_slot(
                    "editorial_transcript_rules",
                    "config/editorial_transcript_rules.json"
                    if (bride / "config" / "editorial_transcript_rules.json").is_file()
                    else None,
                ),
            },
            "entity_ids": entities,
        }
        episodes_out.append(ep_entry)

    # Dedupe globals by id (keep first episode)
    def dedupe(lst: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out2: list[dict[str, Any]] = []
        for x in lst:
            i = x.get("id")
            if not i or i in seen:
                continue
            seen.add(str(i))
            out2.append(x)
        return out2

    doc: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": time.time(),
        "fingerprint": fingerprint,
        "bride_project_root": rel_root,
        "file_ids": file_ids,
        "episodes": episodes_out,
        "global": {
            "nodes": sorted(dedupe(global_nodes), key=global_row_sort_key),
            "claims": sorted(dedupe(global_claims), key=global_row_sort_key),
            "artifacts": sorted(dedupe(global_artifacts), key=global_row_sort_key),
            "memes": sorted(dedupe(global_memes), key=global_row_sort_key),
        },
    }
    return doc


def get_or_build_index(bride: Path, agent_lab_root: Path, *, force: bool = False) -> dict[str, Any]:
    path = index_path(agent_lab_root)
    fp = compute_fingerprint(bride)
    if not force and path.is_file():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if cached.get("fingerprint") == fp and cached.get("schema_version") == _SCHEMA_VERSION:
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    with _index_lock:
        fp2 = compute_fingerprint(bride)
        if (
            not force
            and path.is_file()
        ):
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                if cached.get("fingerprint") == fp2 and cached.get("schema_version") == _SCHEMA_VERSION:
                    return cached
            except (OSError, json.JSONDecodeError):
                pass
        doc = build_index(bride, agent_lab_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
        return doc


def invalidate_index_cache(agent_lab_root: Path) -> None:
    p = index_path(agent_lab_root)
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


# --- resolve file by id ---


def resolve_file_id(
    file_id: str, bride: Path, agent_lab_root: Path
) -> tuple[Path, str] | tuple[None, None]:
    idx = get_or_build_index(bride, agent_lab_root)
    rel = (idx.get("file_ids") or {}).get(file_id.strip().lower())
    if not rel:
        return None, None
    p = _safe_bride_path(bride, rel)
    if p is None:
        return None, None
    return p, rel


def etag_for_path(p: Path) -> str | None:
    if not p.is_file():
        return None
    try:
        st = p.stat()
        return f'W/"{st.st_mtime_ns}-{st.st_size}"'
    except OSError:
        return None


# --- activate worker ---


def _run_build_corrected(agent_lab: Path, bride: Path) -> dict[str, Any]:
    script = bride / "scripts" / "neo4j_corrections.py"
    if not script.is_file():
        return {"skipped": True, "reason": "neo4j_corrections.py not found"}
    cmd = [
        "uv",
        "run",
        "--project",
        str(agent_lab / "framework" / "deer-flow" / "backend"),
        "python",
        str(script),
        "apply-dir",
        str(bride / "transcripts"),
        "--output-dir",
        str(bride / "transcripts_corrected"),
    ]
    try:
        r = subprocess.run(
            cmd,
            cwd=str(agent_lab),
            capture_output=True,
            text=True,
            timeout=600,
        )
        return {
            "returncode": r.returncode,
            "stderr": (r.stderr or "")[-2000:],
            "stdout_tail": (r.stdout or "")[-1000:],
        }
    except Exception as e:
        return {"error": str(e)}


def activate_worker(
    job_id: str,
    youtube_url: str,
    bride: Path,
    agent_lab_root: Path,
) -> None:
    prev = _job_read(agent_lab_root, job_id) or {}
    started = float(prev.get("started") or time.time())
    _job_write(
        agent_lab_root,
        job_id,
        {
            "status": "running",
            "stage": "parse",
            "started": started,
            "result": None,
            "error": None,
        },
    )
    try:
        vid = _parse_video_id(youtube_url)
        if not vid:
            raise ValueError("Invalid or unsupported YouTube URL")

        _job_write(
            agent_lab_root,
            job_id,
            {
                "status": "running",
                "stage": "registry",
                "started": started,
                "result": None,
                "error": None,
            },
        )
        ep, norm = append_episode_activation(bride, youtube_url, vid)

        _job_write(
            agent_lab_root,
            job_id,
            {
                "status": "running",
                "stage": "fetch_transcript",
                "started": started,
                "episode": ep,
                "youtube_url": norm,
                "result": None,
                "error": None,
            },
        )

        import importlib.util

        ft_path = bride / "scripts" / "fetch_transcripts.py"
        spec = importlib.util.spec_from_file_location("bride_fetch_transcripts", ft_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("fetch_transcripts.py not found")
        ft = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ft)

        fetch_out = ft.fetch_and_write_episode(ep, norm, project_dir=bride)

        _job_write(
            agent_lab_root,
            job_id,
            {
                "status": "running",
                "stage": "build_corrected",
                "started": started,
                "episode": ep,
                "fetch": fetch_out,
                "result": None,
                "error": None,
            },
        )
        corrected = _run_build_corrected(agent_lab_root, bride)

        invalidate_index_cache(agent_lab_root)

        _job_write(
            agent_lab_root,
            job_id,
            {
                "status": "done",
                "stage": "done",
                "started": started,
                "episode": ep,
                "youtube_url": norm,
                "video_id": vid,
                "result": {"fetch": fetch_out, "corrected": corrected},
                "error": None,
            },
        )
    except Exception as e:
        _job_write(
            agent_lab_root,
            job_id,
            {
                "status": "error",
                "stage": "error",
                "started": started,
                "result": None,
                "error": str(e),
            },
        )


def prune_activate_jobs(agent_lab_root: Path) -> None:
    _prune_jobs(agent_lab_root)


def activate_job_write(agent_lab_root: Path, job_id: str, data: dict[str, Any]) -> None:
    _job_write(agent_lab_root, job_id, data)


def activate_job_read(agent_lab_root: Path, job_id: str) -> dict[str, Any] | None:
    return _job_read(agent_lab_root, job_id)


def prune_activate_jobs(agent_lab_root: Path) -> None:
    _prune_jobs(agent_lab_root)


def activate_job_write(agent_lab_root: Path, job_id: str, data: dict[str, Any]) -> None:
    _job_write(agent_lab_root, job_id, data)


def activate_job_read(agent_lab_root: Path, job_id: str) -> dict[str, Any] | None:
    return _job_read(agent_lab_root, job_id)
