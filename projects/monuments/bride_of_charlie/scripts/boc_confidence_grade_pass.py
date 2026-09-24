#!/usr/bin/env python3
"""
BoC confidence-grade pass (post PR37 / tip 318d609):
  1) Dense-reclaim Topic/Org/Place N-1000+ in register first-intro order (eps 1–18).
  2) Remap contract: drafts, phase1, edge_cases, retired_node_ids, inscription, canonical.
  3) Backfill empty Person register *Related* from claim/artifact citations (YWLS pattern).

Usage (repo root):
  python3 projects/monuments/bride_of_charlie/scripts/boc_confidence_grade_pass.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = PROJECT.parents[2]
_VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
PYTHON = str(_VENV_PY) if _VENV_PY.is_file() else sys.executable
sys.path.insert(0, str(SCRIPTS))

import pipeline_gates as pg  # noqa: E402

_ID_TOKEN = re.compile(r"(?<![A-Za-z0-9-])(N-\d+)(?![0-9])")
_NODE_HEADER = re.compile(r"^\*\*(N-\d+)\*\*\s+(.+)$", re.MULTILINE)
_NEW_NODES_LINE = re.compile(r"(-\s*New Nodes Introduced:\s*)(.+)$", re.MULTILINE)
_NODE_TYPE_RE = re.compile(r"^Node Type:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
_RELATED_NODES_LINE = re.compile(r"^Related Nodes:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_CLAIM_HEADER = re.compile(r"^\*\*(C-\d+)\*\*", re.MULTILINE)
_CA_TOKEN = re.compile(r"\b([CA]-[\d.]+)\b")
_PERSON_TYPES = frozenset({"person", "investigationtarget"})


def _nid_num(nid: str) -> int:
    return int(nid.split("-")[1])


def _replace_ids(text: str, remap: dict[str, str]) -> str:
    if not remap:
        return text
    temp: dict[str, str] = {}
    ordered = sorted(
        (k for k in remap if remap[k] != k),
        key=_nid_num,
        reverse=True,
    )
    for i, old in enumerate(ordered):
        temp[old] = f"__IDTMP_{i:04d}__"
    out = text
    for old, tmp in temp.items():
        out = _ID_TOKEN.sub(lambda m, o=old, t=tmp: t if m.group(1) == o else m.group(0), out)
    rev = {v: remap[k] for k, v in temp.items()}
    for tmp, new in rev.items():
        out = out.replace(tmp, new)
    return out


def _apply_shift_remap(text: str, remap: dict[str, str]) -> str:
    ordered = sorted(
        (k for k, v in remap.items() if v != k),
        key=_nid_num,
        reverse=True,
    )
    for _ in range(len(ordered) + 3):
        changed = False
        for old in ordered:
            new = remap.get(old)
            if not new or new == old or old not in text:
                continue
            updated = _replace_ids(text, {old: new})
            if updated != text:
                text = updated
                changed = True
        if not changed:
            break
    return text


def _topic_first_intro_order(draft_paths: list[Path]) -> list[str]:
    """First register-header appearance order for N-1000+ across eps 1–18."""
    seen: set[str] = set()
    ordered: list[str] = []
    for path in sorted(draft_paths):
        if "cross" in path.name.lower():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _NODE_HEADER.finditer(text):
            nid = m.group(1)
            if _nid_num(nid) < 1000 or nid in seen:
                continue
            seen.add(nid)
            ordered.append(nid)
    return ordered


def _build_topic_remap(ordered: list[str]) -> dict[str, str]:
    remap: dict[str, str] = {}
    for i, old in enumerate(ordered):
        new = f"N-{1000 + i}"
        if old != new:
            remap[old] = new
    return remap


def _fix_new_nodes_line(text: str, remap: dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        prefix, body = m.group(1), m.group(2)
        parts = [p.strip() for p in body.split(",")]
        new_parts: list[str] = []
        seen: set[str] = set()
        for p in parts:
            tok = p.strip()
            if tok in remap:
                tok = remap[tok]
            if tok and tok not in seen:
                seen.add(tok)
                new_parts.append(tok)
        return prefix + ", ".join(new_parts)

    return _NEW_NODES_LINE.sub(repl, text)


def _sync_new_nodes_introduced(draft_paths: list[Path]) -> None:
    """Ensure each node's first global register appearance is listed on that episode's ledger line."""
    first_ep: dict[str, int] = {}
    for path in sorted(draft_paths):
        if "cross" in path.name.lower():
            continue
        m_ep = re.search(r"episode_(\d{3})", path.name)
        if not m_ep:
            continue
        ep = int(m_ep.group(1))
        text = path.read_text(encoding="utf-8")
        for hm in _NODE_HEADER.finditer(text):
            nid = hm.group(1)
            if _nid_num(nid) < 1000:
                continue
            first_ep.setdefault(nid, ep)

    for path in sorted(draft_paths):
        if "cross" in path.name.lower():
            continue
        m_ep = re.search(r"episode_(\d{3})", path.name)
        if not m_ep:
            continue
        ep = int(m_ep.group(1))
        text = path.read_text(encoding="utf-8")
        m = _NEW_NODES_LINE.search(text)
        if not m:
            continue
        parts = [p.strip() for p in m.group(2).split(",") if p.strip()]
        present = set(parts)
        for nid, fep in first_ep.items():
            if fep == ep and nid not in present:
                parts.append(nid)
        persons = sorted([p for p in parts if _nid_num(p) < 1000], key=_nid_num)
        topics = sorted([p for p in parts if _nid_num(p) >= 1000], key=_nid_num)
        updated = text[: m.start(2)] + ", ".join(persons + topics) + text[m.end(2) :]
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def _sort_new_nodes_ledger(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        prefix, body = m.group(1), m.group(2)
        parts = [p.strip() for p in body.split(",") if p.strip()]
        persons = sorted([p for p in parts if _nid_num(p) < 1000], key=_nid_num)
        topics = sorted([p for p in parts if _nid_num(p) >= 1000], key=_nid_num)
        return prefix + ", ".join(persons + topics)

    return _NEW_NODES_LINE.sub(repl, text)


def _collect_episode_citations(content: str) -> dict[str, set[str]]:
    """N-id -> C-/A- ids that cite it on claims (Related Nodes + anchored artifacts)."""
    cites: dict[str, set[str]] = defaultdict(set)
    claim_starts = [(m.start(), m.group(1)) for m in _CLAIM_HEADER.finditer(content)]
    for i, (start, cid) in enumerate(claim_starts):
        end = claim_starts[i + 1][0] if i + 1 < len(claim_starts) else len(content)
        block = content[start:end]
        rn = _RELATED_NODES_LINE.search(block)
        if not rn:
            continue
        nids = re.findall(r"N-\d+", rn.group(1))
        anchored = re.findall(r"A-[\d.]+", block)
        for nid in nids:
            cites[nid].add(cid)
            cites[nid].update(anchored)
    for m in re.finditer(r"^\*Related:\s*([^*\n]+)\*", content, re.MULTILINE):
        chunk = m.group(1)
        if not re.search(r"\b[CA]-\d", chunk):
            continue
        ca_ids = _CA_TOKEN.findall(chunk)
        for nid in re.findall(r"N-\d+", chunk):
            cites[nid].update(ca_ids)
    return cites


def _kind_key(x: str) -> tuple:
    if x.startswith("A-"):
        return (0, x)
    if x.startswith("C-"):
        return (1, x)
    return (2, x)


def _merge_register_related(block: str, extra: set[str]) -> str:
    found: list[str] = []
    for m in re.finditer(r"^\*Related:\s*([^*]*)\*", block, re.MULTILINE):
        raw = m.group(1).strip()
        if raw:
            for part in re.split(r"[,;]", raw):
                tok = part.strip()
                if tok and re.match(r"^[NCA]-", tok):
                    found.append(tok)
    merged = sorted(set(found) | extra, key=_kind_key)
    if not merged:
        return block
    new_line = "*Related: " + ", ".join(merged) + "*"
    if not re.search(r"^\*Related:", block, re.MULTILINE):
        return block.rstrip() + "\n\n" + new_line + "\n"
    out_lines: list[str] = []
    replaced = False
    for line in block.splitlines():
        if line.startswith("*Related:"):
            if not replaced:
                out_lines.append(new_line)
                replaced = True
            continue
        out_lines.append(line)
    if not replaced:
        out_lines.append(new_line)
    return "\n".join(out_lines) + ("\n" if block.endswith("\n") else "")


def _backfill_person_related(text: str) -> str:
    cites = _collect_episode_citations(text)
    parts: list[str] = []
    last = 0
    for m in _NODE_HEADER.finditer(text):
        if m.start() > last:
            parts.append(text[last : m.start()])
        nid = m.group(1)
        nxt = _NODE_HEADER.search(text, m.end())
        block_end = nxt.start() if nxt else len(text)
        block = text[m.start() : block_end]
        tm = _NODE_TYPE_RE.search(block)
        ntype = (tm.group(1).strip().lower() if tm else "")
        if ntype in _PERSON_TYPES and _nid_num(nid) < 1000:
            related_lines = list(re.finditer(r"^\*Related:\s*([^*]*)\*", block, re.MULTILINE))
            first_empty = bool(related_lines and not related_lines[0].group(1).strip())
            multi_related = len(related_lines) > 1
            extra = {x for x in cites.get(nid, set()) if x.startswith(("C-", "A-"))}
            if extra and (first_empty or multi_related or not related_lines):
                block = _merge_register_related(block, extra)
        parts.append(block)
        last = block_end
    parts.append(text[last:])
    return "".join(parts)


def _json_type(label: str) -> str:
    lab = label.strip().lower()
    if lab == "person":
        return "person"
    if lab == "organization":
        return "organization"
    if lab == "place":
        return "place"
    return "topic"


def _rebuild_canonical_from_drafts() -> dict:
    nodes: dict[str, dict] = {}
    for ep in range(1, 19):
        path = PROJECT / "drafts" / f"episode_{ep:03d}.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for m in _NODE_HEADER.finditer(text):
            nid, name = m.group(1), m.group(2).strip()
            start = m.end()
            nxt = _NODE_HEADER.search(text, start)
            block = text[start : nxt.start() if nxt else len(text)]
            tm = _NODE_TYPE_RE.search(block)
            ntype = _json_type(tm.group(1)) if tm else "person"
            ent = nodes.setdefault(
                nid,
                {"canonical_name": name, "type": ntype, "aliases": [], "episodes": []},
            )
            if ep not in ent["episodes"]:
                ent["episodes"].append(ep)
    for ent in nodes.values():
        ent["episodes"] = sorted(ent["episodes"])
    person_max = max(
        (_nid_num(k) for k, v in nodes.items() if v.get("type") == "person"),
        default=58,
    )
    inv_max = max(
        (_nid_num(k) for k, v in nodes.items() if v.get("type") != "person"),
        default=1066,
    )
    return {
        "version": 1,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_person_id": person_max + 1,
        "next_investigation_id": inv_max + 1,
        "nodes": nodes,
    }


def _update_retired(remap: dict[str, str], names: dict[str, str]) -> None:
    path = PROJECT / "config" / "retired_node_ids.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    retired = data.setdefault("retired", {})
    for old, new in sorted(remap.items(), key=lambda kv: _nid_num(kv[0])):
        key = f"pr38-topic-{old}"
        retired[key] = {
            "survives_as": new,
            "canonical_name": names.get(new) or names.get(old) or "",
            "reason": f"PR38 dense Topic/Org/Place intro-order reclaim; was {old}.",
        }
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _touch_paths(paths: list[Path], remap: dict[str, str], fix_ledger: bool) -> int:
    n = 0
    for path in paths:
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        updated = _replace_ids(raw, remap)
        if fix_ledger and path.suffix == ".md":
            updated = _fix_new_nodes_line(updated, remap)
            updated = _sort_new_nodes_ledger(updated)
            updated = _backfill_person_related(updated)
        if updated != raw:
            path.write_text(updated, encoding="utf-8")
            n += 1
    return n


def _count_header_intro_violations(draft_paths: list[Path]) -> int:
    ordered = _topic_first_intro_order(draft_paths)
    prev = 0
    count = 0
    for nid in ordered:
        num = _nid_num(nid)
        if num < prev:
            count += 1
        prev = num
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.apply:
        print("Dry-run: pass --apply to mutate monument files.")
        return 0

    draft_paths = sorted((PROJECT / "drafts").glob("episode_*.md"))
    ordered = _topic_first_intro_order(draft_paths)
    remap = _build_topic_remap(ordered)
    print(f"topic nodes: {len(ordered)}; remap moves: {len(remap)}")
    print(f"header intro-order violations before: {_count_header_intro_violations(draft_paths)}")

    canon_before = json.loads((PROJECT / "canonical" / "nodes.json").read_text())
    names = {k: v.get("canonical_name", "") for k, v in canon_before.get("nodes", {}).items()}

    p1_paths = sorted((PROJECT / "phase1_output").glob("*.json"))
    edge = PROJECT / "canonical" / "edge_cases.jsonl"
    extra: list[Path] = [edge] if edge.is_file() else []
    cross = sorted((PROJECT / "drafts").glob("cross_*.md"))
    docs = sorted((PROJECT / "docs").glob("*.md")) if (PROJECT / "docs").is_dir() else []

    n = _touch_paths(draft_paths + cross + p1_paths + extra + docs, remap, fix_ledger=True)
    _sync_new_nodes_introduced(draft_paths)
    print(f"text/json touched: {n}")

    _update_retired(remap, names)

    for ep in range(1, 19):
        subprocess.run(
            [PYTHON, str(SCRIPTS / "build_inscription_from_drafts.py"), "--episode", str(ep)],
            cwd=str(PROJECT),
            check=True,
        )

    canonical = _rebuild_canonical_from_drafts()
    (PROJECT / "canonical" / "nodes.json").write_text(
        json.dumps(canonical, indent=2) + "\n",
        encoding="utf-8",
    )

    for ep in range(9, 19):
        tpath = pg.resolve_corrected_transcript(PROJECT, ep)
        if tpath and tpath.is_file():
            pg.write_transcript_sha_stamp(ep, pg.sha256_file(tpath))

    print(f"header intro-order violations after: {_count_header_intro_violations(draft_paths)}")
    if remap:
        sample = list(sorted(remap.items(), key=lambda kv: _nid_num(kv[0])))[:8]
        print("sample remap:", sample)
        print("...", len(remap), "total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
