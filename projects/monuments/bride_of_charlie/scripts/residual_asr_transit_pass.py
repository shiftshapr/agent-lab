#!/usr/bin/env python3
"""Transit pass 2: residual ASR person forks on cff0eb8+ trees."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PROJECT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import collapse_identity_forks_pr37 as c  # noqa: E402

MANUAL_COLLAPSE = {
    "N-64": "N-42",
    "N-138": "N-42",
    "N-85": "N-70",
    "N-130": "N-109",
    "N-140": "N-94",
    "N-153": "N-137",
}

TOPIC_SWAPS = (
    ("N-1148", "N-1126"),
    ("N-1158", "N-1150"),
    ("N-1204", "N-1189"),
)


def _fix_topic_intro_slips(draft_paths: list[Path]) -> None:
    """Swap topic register blocks for mis-assigned ids (Transit P1) without touching ledger order."""

    def swap_blocks(text: str, a: str, b: str) -> str:
        if a == b:
            return text
        ha = re.compile(
            rf"(^\*\*{re.escape(a)}\*\*[\s\S]*?)(?=^\*\*(?:N-|C-|A-)|\Z)",
            re.MULTILINE,
        )
        hb = re.compile(
            rf"(^\*\*{re.escape(b)}\*\*[\s\S]*?)(?=^\*\*(?:N-|C-|A-)|\Z)",
            re.MULTILINE,
        )
        ma, mb = ha.search(text), hb.search(text)
        if not ma or not mb:
            return text
        ba, bb = ma.group(1), mb.group(1)
        ba2 = re.sub(rf"^\*\*{re.escape(a)}\*\*", f"**{b}**", ba, count=1, flags=re.MULTILINE)
        bb2 = re.sub(rf"^\*\*{re.escape(b)}\*\*", f"**{a}**", bb, count=1, flags=re.MULTILINE)
        text = text[: ma.start()] + ba2 + text[ma.end() : mb.start()] + bb2 + text[mb.end() :]
        return c._replace_ids(text, {a: b, b: a})

    for path in draft_paths:
        text = path.read_text(encoding="utf-8")
        for a, b in TOPIC_SWAPS:
            text = swap_blocks(text, a, b)
        path.write_text(text, encoding="utf-8")


def _swap_pair(text: str, a: str, b: str) -> str:
    if a == b:
        return text
    tmp = f"__SWAP_{c._nid_num(a)}_{c._nid_num(b)}__"
    text = c._replace_ids(text, {a: tmp, b: a})
    return text.replace(tmp, b)


def _sort_new_nodes_ledger_eps9plus(draft_paths: list[Path]) -> None:
    def sort_line(text: str) -> str:
        def repl(m: re.Match[str]) -> str:
            prefix, body = m.group(1), m.group(2)
            parts = [p.strip() for p in body.split(",") if p.strip()]
            persons = sorted([p for p in parts if c._nid_num(p) < 1000], key=c._nid_num)
            topics = sorted([p for p in parts if c._nid_num(p) >= 1000], key=c._nid_num)
            return prefix + ", ".join(persons + topics)

        return c._NEW_NODES_LINE.sub(repl, text)

    for path in draft_paths:
        m = re.search(r"episode_(\d{3})", path.name)
        if not m or int(m.group(1)) < 9:
            continue
        text = path.read_text(encoding="utf-8")
        sorted_text = sort_line(text)
        if sorted_text != text:
            path.write_text(sorted_text, encoding="utf-8")


def _person_first_intro_key(draft_paths: list[Path]) -> dict[str, tuple[int, int, int]]:
    """Person id -> (first_ep, ledger_index, old_num) for dense reclaim sorting."""
    keys: dict[str, tuple[int, int, int]] = {}
    for path in sorted(draft_paths):
        m_ep = re.search(r"episode_(\d{3})", path.name)
        ep = int(m_ep.group(1)) if m_ep else 999
        text = path.read_text(encoding="utf-8")
        m = c._NEW_NODES_LINE.search(text)
        if m:
            for idx, part in enumerate(m.group(2).split(",")):
                nid = part.strip()
                if not nid.startswith("N-") or c._nid_num(nid) >= 1000:
                    continue
                keys.setdefault(nid, (ep, idx, c._nid_num(nid)))
        for hm in c._NODE_HEADER.finditer(text):
            nid = hm.group(1)
            if c._nid_num(nid) >= 1000:
                continue
            keys.setdefault(nid, (ep, 9999, c._nid_num(nid)))
    return keys


def _dense_person_reclaim(collapse: dict[str, str], draft_paths: list[Path]) -> dict[str, str]:
    """Remap person ids >=59 to dense N-59.. in first-intro order after collapse."""

    def resolve(nid: str) -> str:
        while nid in collapse:
            nid = collapse[nid]
        return nid

    intro = _person_first_intro_key(draft_paths)
    persons: set[str] = set()
    for path in draft_paths:
        for hm in c._NODE_HEADER.finditer(path.read_text(encoding="utf-8")):
            nid = hm.group(1)
            if c._nid_num(nid) < 1000:
                persons.add(resolve(nid))

    ordered = sorted(
        (p for p in persons if c._nid_num(p) > 58),
        key=lambda p: intro.get(p, (999, 9999, c._nid_num(p))),
    )

    dense: dict[str, str] = {}
    n = 59
    for old in ordered:
        new = f"N-{n}"
        if old != new:
            dense[old] = new
        n += 1
    return dense


def main() -> int:
    collapse = dict(MANUAL_COLLAPSE)
    retire = set(collapse.keys())
    draft_paths = sorted((PROJECT / "drafts").glob("episode_*.md"))
    draft_paths = [p.resolve() for p in draft_paths if "cross" not in p.name.lower()]
    p1_paths = [p.resolve() for p in sorted((PROJECT / "phase1_output").glob("episode_*.json"))]

    c._touch_files(draft_paths, collapse, retire, fix_nodes_line=True)
    c._touch_files(p1_paths, collapse, set(), fix_nodes_line=False)

    dense_p = _dense_person_reclaim(collapse, draft_paths)
    print(f"collapse {len(collapse)} dense_person {len(dense_p)}")
    if dense_p:
        c._touch_files(draft_paths, dense_p, set(), fix_nodes_line=True)
        c._touch_files(p1_paths, dense_p, set(), fix_nodes_line=False)
        _sort_new_nodes_ledger_eps9plus(draft_paths)

    for path in draft_paths:
        text = path.read_text(encoding="utf-8")
        for wrong, right in [
            ("Andrew Kovac", "Andrew Kolvet"),
            ("Andrew Kovit", "Andrew Kolvet"),
            ("Andrew Kovace", "Andrew Kolvet"),
            ("Andrew Kovett", "Andrew Kolvet"),
            ("Andrew Kovette", "Andrew Kolvet"),
            ("Tyler James Robinson", "Tyler Robinson"),
            ("Eric Bolling", "Eric Bowling"),
            ("Phil Leman", "Phil Lyman"),
            ("Bob Schman", "Bob Shaman"),
        ]:
            text = re.sub(
                rf"(^\*\*N-\d+\*\*\s+){re.escape(wrong)}",
                rf"\1{right}",
                text,
                flags=re.MULTILINE,
            )
        path.write_text(text, encoding="utf-8")

    for path in draft_paths:
        m = re.search(r"episode_(\d{3})", path.name)
        if not m:
            continue
        text = path.read_text(encoding="utf-8")
        if int(m.group(1)) == 9:
            text = c._apply_orphan_orgs(text, 9, {})
        path.write_text(text, encoding="utf-8")

    for ep in range(9, 19):
        import subprocess

        subprocess.run(
            [sys.executable, str(SCRIPTS / "build_inscription_from_drafts.py"), "--episode", str(ep)],
            cwd=str(PROJECT),
            check=True,
        )
    (PROJECT / "canonical" / "nodes.json").write_text(
        json.dumps(c._rebuild_canonical_from_drafts(), indent=2) + "\n",
        encoding="utf-8",
    )
    c._refresh_sha_stamps(range(9, 19))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
