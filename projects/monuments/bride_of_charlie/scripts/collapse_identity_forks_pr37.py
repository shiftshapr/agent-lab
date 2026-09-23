#!/usr/bin/env python3
"""
PR37 Transit: collapse person/topic identity forks to first-intro ids, dense-reclaim
person N-59+ and topic/org/place N-1067+, refresh inscription/canonical alignment.

Usage (from repo root):
  python3 projects/monuments/bride_of_charlie/scripts/collapse_identity_forks_pr37.py --report REPORT.json --apply
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
sys.path.insert(0, str(SCRIPTS))

import pipeline_gates as pg  # noqa: E402

_ID_TOKEN = re.compile(r"(?<![A-Za-z0-9-])(N-\d+)(?![0-9])")
_NODE_HEADER = re.compile(r"^\*\*(N-\d+)\*\*\s+(.+)$", re.MULTILINE)
_NEW_NODES_LINE = re.compile(r"(-\s*New Nodes Introduced:\s*)(.+)$", re.MULTILINE)
_ORPHAN_ORGS = [
    ("N-1071", 9, "Fox News", "C-1122"),
    ("N-1073", 9, "YWLS Conference", "C-1118"),
    ("N-1131", 13, "Calira Engineering", None),
    ("N-1133", 13, "CIA", None),
    ("N-1150", 14, "Candace Intelligence Agency", None),
    ("N-1151", 14, "Daily Wire", None),
    ("N-1165", 15, "Calira Engineering", None),
    ("N-1167", 15, "LDS Church", None),
    ("N-1178", 16, "Calera Engineering", None),
    ("N-1181", 16, "Alex Clark Podcast", None),
    ("N-1184", 16, "CIA", None),
    ("N-1213", 17, "CIA", None),
    ("N-1214", 17, "Church of Jesus Christ of Latter-day Saints", None),
    ("N-1215", 17, "Turning Point UK", None),
    ("N-1220", 17, "The Wellness Company", None),
    ("N-1221", 17, "CDC", None),
]


def _nid_num(nid: str) -> int:
    return int(nid.split("-")[1])


def _apply_shift_remap(text: str, remap: dict[str, str]) -> str:
    """Apply a dense-band permutation one hop at a time (high ids first)."""
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


def _load_first_ep(report: dict, canonical: dict) -> dict[str, int]:
    first: dict[str, int] = {}
    for row in report["person_band"].get("new_persons_9_18", []):
        first[row["id"]] = row["ep"]
    for nid, node in canonical.get("nodes", {}).items():
        eps = node.get("episodes") or []
        if eps:
            first.setdefault(nid, min(eps))
        elif node.get("first_seen_episode"):
            first.setdefault(nid, int(node["first_seen_episode"]))
    return first


def _pick_keeper(ids: list[str], first_ep: dict[str, int]) -> str:
    def key(nid: str) -> tuple[int, int]:
        return (first_ep.get(nid, 999), _nid_num(nid))

    return min(ids, key=key)


def _build_collapse(report: dict, first_ep: dict[str, int]) -> dict[str, str]:
    """retired_id -> keeper_id (not identity on keepers)."""
    collapse: dict[str, str] = {}
    fork_lists: list[list[str]] = []
    for fork in report["person_band"]["identity_forks"]:
        fork_lists.append(fork["ids"])
    for fork in report["person_band"]["asr_variant_forks"]:
        fork_lists.append(fork["ids"])
    for fork in report["topic_band"]["identity_forks"]:
        fork_lists.append(fork["ids"])
    # Cross-name ASR clusters (Transit report)
    fork_lists.append(["N-65", "N-145", "N-232"])

    def resolve(nid: str) -> str:
        while nid in collapse:
            nid = collapse[nid]
        return nid

    for ids in fork_lists:
        keeper = _pick_keeper(ids, first_ep)
        for i in ids:
            if i != keeper:
                collapse[i] = keeper

    changed = True
    while changed:
        changed = False
        for old, mid in list(collapse.items()):
            root = resolve(mid)
            if root != mid:
                collapse[old] = root
                changed = True

    return collapse


def _parse_person_intro_order(report: dict) -> list[str]:
    rows = report["person_band"]["new_persons_9_18"]
    return [r["id"] for r in rows]


def _dense_person_remap(
    collapse: dict[str, str],
    canonical: dict,
    intro_order: list[str],
) -> dict[str, str]:
    """old -> new for person ids >= 59 after collapse."""
    def resolve(nid: str) -> str:
        while nid in collapse:
            nid = collapse[nid]
        return nid

    seen: set[str] = set()
    ordered: list[str] = []
    for nid in intro_order:
        r = resolve(nid)
        if _nid_num(r) <= 58:
            continue
        if r not in seen:
            seen.add(r)
            ordered.append(r)

    dense: dict[str, str] = {}
    n = 59
    for old in ordered:
        new = f"N-{n}"
        if old != new:
            dense[old] = new
        n += 1
    return dense


_TOPIC_HOLES_9_18 = (
    1081,
    1126,
    1143,
    1144,
    1164,
    1166,
    1194,
    1195,
    1199,
    1200,
)


def _compact_topic_register_ids(draft_paths: list[Path]) -> dict[str, str]:
    """Dense N-1000+ band in ledger first-intro order (matches intro_order gate)."""
    first_intro_idx: dict[str, int] = {}
    header_ep: dict[str, int] = {}
    idx = 0
    for path in sorted(draft_paths):
        m_ep = re.search(r"episode_(\d{3})", path.name)
        ep = int(m_ep.group(1)) if m_ep else 999
        text = path.read_text(encoding="utf-8")
        m = _NEW_NODES_LINE.search(text)
        if m:
            for part in m.group(2).split(","):
                nid = part.strip()
                if not nid.startswith("N-"):
                    continue
                if _nid_num(nid) >= 1000 and nid not in first_intro_idx:
                    first_intro_idx[nid] = idx
                    idx += 1
        for hm in _NODE_HEADER.finditer(text):
            nid = hm.group(1)
            if _nid_num(nid) >= 1000:
                header_ep.setdefault(nid, ep)
    all_ids = set(first_intro_idx) | set(header_ep)
    if not all_ids:
        return {}
    for nid in all_ids:
        if nid not in first_intro_idx:
            first_intro_idx[nid] = idx
            idx += 1
    ordered = sorted(
        all_ids,
        key=lambda n: (first_intro_idx[n], header_ep.get(n, 999), _nid_num(n)),
    )
    lo = min(_nid_num(n) for n in ordered)
    if lo < 1000:
        lo = 1000
    compact: dict[str, str] = {}
    for i, old in enumerate(ordered):
        new = lo + i
        if _nid_num(old) != new:
            compact[old] = f"N-{new}"
    return compact


def _dense_topic_remap(collapse: dict[str, str], canonical: dict, report: dict) -> dict[str, str]:
    def resolve(nid: str) -> str:
        while nid in collapse:
            nid = collapse[nid]
        return nid

    seen: list[str] = []
    topic_rows = report.get("topic_band", {}).get("new_topics_9_18") or []
    for row in topic_rows:
        r = resolve(row["id"])
        if _nid_num(r) >= 1067 and r not in seen:
            seen.append(r)
    candidates: list[tuple[int, int, str]] = []
    for nid, node in canonical.get("nodes", {}).items():
        num = _nid_num(nid)
        if num < 1067 or node.get("type") == "person":
            continue
        r = resolve(nid)
        eps = node.get("episodes") or [999]
        candidates.append((min(eps), _nid_num(r), r))
    candidates.sort()
    for _, _, r in candidates:
        if r not in seen:
            seen.append(r)

    dense: dict[str, str] = {}
    n = 1067
    for old in seen:
        new = f"N-{n}"
        if old != new:
            dense[old] = new
        n += 1
    return dense


def _merge_remaps(
    collapse: dict[str, str],
    dense_p: dict[str, str],
    dense_t: dict[str, str],
) -> dict[str, str]:
    """Compose collapse (chain) → dense person (one hop) → dense topic (chain)."""

    def resolve(nid: str) -> str:
        out = nid
        seen_c: set[str] = set()
        while out in collapse and collapse[out] != out:
            if out in seen_c:
                break
            seen_c.add(out)
            out = collapse[out]
        if out in dense_p:
            out = dense_p[out]
        if out in dense_t:
            out = dense_t[out]
        return out

    keys: set[str] = set()
    for m in (collapse, dense_p, dense_t):
        keys.update(m.keys())
    return {k: resolve(k) for k in keys if resolve(k) != k}


def _remove_node_blocks(text: str, retire: set[str]) -> str:
    if not retire:
        return text
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = re.match(r"^\*\*(N-\d+)\*\*", lines[i])
        if m and m.group(1) in retire:
            i += 1
            while i < len(lines):
                if re.match(r"^\*\*(N-\d+|C-\d+|A-\d+)\*\*", lines[i]) or lines[i].startswith("## "):
                    break
                if lines[i].strip() == "---" and i + 1 < len(lines):
                    break
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


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
            if tok not in seen:
                seen.add(tok)
                new_parts.append(tok)
        return prefix + ", ".join(new_parts)

    return _NEW_NODES_LINE.sub(repl, text)


def _apply_orphan_orgs(text: str, ep: int, full_remap: dict[str, str]) -> str:
    for nid, oep, _name, claim in _ORPHAN_ORGS:
        if oep != ep:
            continue
        rid = full_remap.get(nid, nid)
        if claim:
            pat = re.compile(
                rf"(\*\*{re.escape(rid)}\*\*[^\n]+\n(?:.*\n)*?\*Related:\s*)([^\n*]*)(\*)",
                re.MULTILINE,
            )

            def add_claim(m: re.Match[str]) -> str:
                rel = m.group(2).strip()
                ids = [x.strip() for x in rel.split(",") if x.strip()]
                if claim not in ids:
                    ids.append(claim)
                return m.group(1) + ", ".join(ids) + m.group(3)

            text, n = pat.subn(add_claim, text, count=1)
            if n == 0 and rid not in text:
                continue
        else:
            # drop org block if still orphan without claim anchor
            text = _remove_node_blocks(text, {rid})
    return text


_NODE_TYPE_RE = re.compile(r"^Node Type:\s*(\S+)", re.MULTILINE | re.IGNORECASE)


def _json_type(label: str) -> str:
    lab = label.strip().lower()
    if lab == "person":
        return "person"
    if lab == "organization":
        return "organization"
    if lab == "place":
        return "place"
    if lab == "topic":
        return "topic"
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
                {
                    "canonical_name": name,
                    "type": ntype,
                    "aliases": [],
                    "episodes": [],
                },
            )
            if ep not in ent["episodes"]:
                ent["episodes"].append(ep)
            if name and name != ent["canonical_name"]:
                if name not in ent["aliases"]:
                    ent["aliases"].append(name)
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


def _touch_files(paths: list[Path], remap: dict[str, str], retire: set[str], fix_nodes_line: bool) -> list[str]:
    touched: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        updated = _replace_ids(raw, remap)
        if path.suffix == ".md":
            updated = _remove_node_blocks(updated, retire)
            if fix_nodes_line:
                updated = _fix_new_nodes_line(updated, remap)
            m = re.search(r"episode_(\d{3})", path.name)
            if m:
                updated = _apply_orphan_orgs(updated, int(m.group(1)), remap)
        if updated != raw:
            path.write_text(updated, encoding="utf-8")
            touched.append(str(path.relative_to(PROJECT)))
    return touched


def _refresh_sha_stamps(eps: range) -> None:
    for ep in eps:
        tpath = pg.resolve_corrected_transcript(PROJECT, ep)
        if tpath and tpath.is_file():
            d = pg.sha256_file(tpath)
            pg.write_transcript_sha_stamp(ep, d)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    canonical_path = PROJECT / "canonical" / "nodes.json"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    first_ep = _load_first_ep(report, canonical)
    collapse = _build_collapse(report, first_ep)
    intro = _parse_person_intro_order(report)
    dense_p = _dense_person_remap(collapse, canonical, intro)
    dense_t = _dense_topic_remap(collapse, canonical, report)
    full = _merge_remaps(collapse, dense_p, dense_t)
    retire = set(collapse.keys()) - set(full.values())

    print(f"collapse pairs: {len(collapse)}")
    print(f"dense person moves: {len(dense_p)}")
    print(f"dense topic moves: {len(dense_t)}")
    print(f"retire register blocks: {len(retire)}")

    if args.dry_run and not args.apply:
        for cluster in report["person_band"]["identity_forks"][:5]:
            k = _pick_keeper(cluster["ids"], first_ep)
            print(f"  {cluster['norm_name']}: keep {k} <- {[i for i in cluster['ids'] if i != k]}")
        return 0

    draft_paths = sorted((PROJECT / "drafts").glob("episode_*.md"))
    draft_paths = [p for p in draft_paths if "cross" not in p.name.lower()]
    p1_paths = sorted((PROJECT / "phase1_output").glob("episode_*.json"))

    touched = _touch_files(draft_paths, full, retire, fix_nodes_line=True)
    touched += _touch_files(p1_paths, full, set(), fix_nodes_line=False)

    topic_full = _merge_remaps(collapse, {}, dense_t)
    stale_ledger = tuple(f"N-{h}" for h in _TOPIC_HOLES_9_18)
    ledger_fixup = {k: topic_full[k] for k in stale_ledger if k in topic_full}
    if ledger_fixup:
        for path in list(draft_paths) + list(p1_paths):
            if not path.is_file():
                continue
            raw = path.read_text(encoding="utf-8")
            updated = _replace_ids(raw, ledger_fixup)
            updated = _fix_new_nodes_line(updated, ledger_fixup)
            if updated != raw:
                path.write_text(updated, encoding="utf-8")
                touched.append(str(path.relative_to(PROJECT)))

    topic_compact = _compact_topic_register_ids(draft_paths)
    if topic_compact:
        for path in draft_paths + p1_paths:
            if not path.is_file():
                continue
            raw = path.read_text(encoding="utf-8")
            updated = _replace_ids(raw, topic_compact)
            updated = _fix_new_nodes_line(updated, topic_compact)
            if updated != raw:
                path.write_text(updated, encoding="utf-8")
                touched.append(str(path.relative_to(PROJECT)))

    def _sort_new_nodes_ledger(text: str) -> str:
        def repl(m: re.Match[str]) -> str:
            prefix, body = m.group(1), m.group(2)
            parts = [p.strip() for p in body.split(",") if p.strip()]
            persons = sorted([p for p in parts if _nid_num(p) < 1000], key=_nid_num)
            topics = sorted([p for p in parts if _nid_num(p) >= 1000], key=_nid_num)
            return prefix + ", ".join(persons + topics)

        return _NEW_NODES_LINE.sub(repl, text)

    for path in draft_paths:
        m = re.search(r"episode_(\d{3})", path.name)
        if not m or int(m.group(1)) < 9:
            continue
        text = path.read_text(encoding="utf-8")
        sorted_text = _sort_new_nodes_ledger(text)
        if sorted_text != text:
            path.write_text(sorted_text, encoding="utf-8")

    _ASR_HEADER_FIXES = [
        (r"Andrew Kovett", "Andrew Kovac"),
        (r"Andrew Kovette", "Andrew Kovac"),
        (r"Bill Aman", "Bill Ackman"),
        (r"Harley Pasternak", "Harley Pastnic"),
        (r"Megan Kelly", "Megyn Kelly"),
    ]
    for path in draft_paths:
        text = path.read_text(encoding="utf-8")
        for wrong, right in _ASR_HEADER_FIXES:
            text = re.sub(
                rf"(^\*\*N-\d+\*\*\s+){re.escape(wrong)}",
                rf"\1{right}",
                text,
                flags=re.MULTILINE,
            )
        text = text.replace("Utah Valley University (UVU)", "Utah Valley University")
        path.write_text(text, encoding="utf-8")

    for ep in range(9, 19):
        subprocess.run(
            [sys.executable, str(SCRIPTS / "build_inscription_from_drafts.py"), "--episode", str(ep)],
            cwd=str(PROJECT),
            check=True,
        )

    canonical = _rebuild_canonical_from_drafts()
    canonical_path.write_text(json.dumps(canonical, indent=2) + "\n", encoding="utf-8")
    touched.append("canonical/nodes.json")

    _refresh_sha_stamps(range(9, 19))

    print(f"touched {len(touched)} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
