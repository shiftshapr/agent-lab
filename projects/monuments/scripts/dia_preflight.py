#!/usr/bin/env python3
"""
DIA monument preflight — merge-blocking gates for episode drafts + inscription sync.

Exit 0 only when no P0/P1 findings. See projects/monuments/DIA_PREFLIGHT.md.

Usage (from agent-lab root):
  uv run python projects/monuments/scripts/dia_preflight.py --monument bride_of_charlie
  uv run python projects/monuments/scripts/dia_preflight.py --monument bride_of_charlie --json /tmp/preflight.json
  uv run python projects/monuments/scripts/dia_preflight.py --self-test
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[3]
MONUMENTS_ROOT = REPO_ROOT / "projects" / "monuments"

Severity = Literal["P0", "P1", "P2", "WARN"]

NODE_HEADER_RE = re.compile(r"^\*\*N-(\d+)\*\*\s+(.+)$", re.MULTILINE)
MEME_HEADER_RE = re.compile(r"^\*\*M-(\d+)\*\*\s*(?:\([^)]+\)\s*)?(.+)$", re.MULTILINE)
NODE_TYPE_RE = re.compile(r"^Node Type:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
NODE_RELATED_RE = re.compile(r"^\*Related:\s*([^*]+)\*", re.MULTILINE)
N_ID_TOKEN_RE = re.compile(r"\bN-(\d+)\b")
M_ID_TOKEN_RE = re.compile(r"\bM-(\d+)\b")
EPISODE_DRAFT_RE = re.compile(r"episode_(\d+)\.md$", re.I)
NEW_NODES_INTRO_RE = re.compile(r"New Nodes Introduced:\s*(.+)$", re.MULTILINE)
RELATED_NODES_LINE_RE = re.compile(r"^Related Nodes:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
MENTIONS_LINE_RE = re.compile(r"^Mentions:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
CLAIM_HEADER_RE = re.compile(r"^\*\*(C-\d+)\*\*\s+(.+)$", re.MULTILINE)
CLAIM_BODY_LINE_RE = re.compile(r"^Claim:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
# Skip non-definition claim headers (continuation / omission notes).
CLAIM_META_LABEL_RE = re.compile(
    r"(?i)\b(already\s+listed|omitted|supplemental|continuing\s+the\s+register)\b"
)

# Timecode: require HH:MM:SS (two colon-separated numeric segments before seconds).
# Rejects bare M:SS like 5:30 or 22:04 without hour field when only one colon group.
TIMESTAMP_FIELD_RE = re.compile(
    r"^(Claim Timestamp|Video Timestamp|Event Timestamp):\s*(.+)$",
    re.MULTILINE | re.IGNORECASE,
)
VALID_HMS_RE = re.compile(
    r"^\s*(\d{1,2}):(\d{2}):(\d{2})(?:\s*[–\-—]\s*(\d{1,2}):(\d{2}):(\d{2}))?\s*$"
)
BARE_MS_RE = re.compile(r"^\s*\d{1,2}:\d{2}(?:\s*[–\-—]\s*\d{1,2}:\d{2})?\s*$")

PERSON_TYPES = frozenset({"person", "investigationtarget"})
TOPIC_BAND_TYPES = frozenset({"topic", "organization", "organisation", "place", "org"})
# 2026-10-04 lock: persons are N-1..N-999 or N-10000+. N-1000..N-9999 stays topic/org/place.
PERSON_HIGH_MIN = 10000
TOPIC_BAND_MAX = 9999


def nid_band(nid: int) -> str:
    if nid < 1000:
        return "person"
    if nid >= PERSON_HIGH_MIN:
        return "person_high"
    return "topic"


@dataclass
class Finding:
    severity: Severity
    check: str
    message: str
    location: str | None = None


@dataclass
class PreflightReport:
    monument: str
    monument_dir: str
    git_head: str | None = None
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: Severity, check: str, message: str, location: str | None = None) -> None:
        self.findings.append(Finding(severity, check, message, location))

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {"P0": 0, "P1": 0, "P2": 0, "WARN": 0}
        for f in self.findings:
            out[f.severity] = out.get(f.severity, 0) + 1
        return out

    def hard_fail(self) -> bool:
        c = self.counts()
        return c["P0"] > 0 or c["P1"] > 0


def _norm_name(name: str) -> str:
    return " ".join(name.strip().split())


def _parse_node_type(block: str) -> str:
    m = NODE_TYPE_RE.search(block)
    if not m:
        return ""
    return m.group(1).strip().lower()


def _parse_register_related(block: str) -> list[str]:
    m = NODE_RELATED_RE.search(block)
    if not m:
        return []
    raw = m.group(1)
    out: list[str] = []
    for part in re.split(r"[,;]", raw):
        tok = part.strip()
        if tok.lower().startswith("same_as:"):
            tok = tok.split(":", 1)[1].strip()
        if re.match(r"^N-\d+$", tok):
            out.append(tok)
    return out


def _register_related_is_empty(block: str) -> bool:
    m = NODE_RELATED_RE.search(block)
    if not m:
        return True
    return not m.group(1).strip()


@dataclass
class RegisterEntry:
    nid: int
    name: str
    node_type: str
    episode: int
    episode_file: str
    order_in_episode: int
    register_related: list[str]
    register_block: str = ""


def _split_node_register(content: str) -> list[tuple[int, str, str]]:
    """Return (nid, name, block_text) in file order."""
    headers = list(NODE_HEADER_RE.finditer(content))
    out: list[tuple[int, str, str]] = []
    for i, hm in enumerate(headers):
        nid = int(hm.group(1))
        name = hm.group(2).strip()
        start = hm.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
        out.append((nid, name, content[start:end]))
    return out


def load_draft_episodes(drafts_dir: Path) -> list[tuple[int, str, Path, str]]:
    rows: list[tuple[int, str, Path, str]] = []
    for path in sorted(drafts_dir.glob("episode_*.md")):
        if "cross_episode" in path.name.lower():
            continue
        m = EPISODE_DRAFT_RE.search(path.name)
        if not m:
            continue
        ep = int(m.group(1))
        rows.append((ep, path.name, path, path.read_text(encoding="utf-8")))
    rows.sort(key=lambda r: r[0])
    return rows


def collect_register_entries(episodes: list[tuple[int, str, Path, str]]) -> list[RegisterEntry]:
    entries: list[RegisterEntry] = []
    for ep, ep_name, _path, content in episodes:
        if "## 4. Node Register" not in content and "## 4." not in content:
            reg = content
        else:
            reg = content.split("## 4. Node Register", 1)[-1]
            if "## 5." in reg:
                reg = reg.split("## 5.", 1)[0]
        blocks = _split_node_register(reg)
        for order, (nid, name, block) in enumerate(blocks):
            entries.append(
                RegisterEntry(
                    nid=nid,
                    name=name,
                    node_type=_parse_node_type(block),
                    episode=ep,
                    episode_file=ep_name,
                    order_in_episode=order,
                    register_related=_parse_register_related(block),
                    register_block=block,
                )
            )
    return entries


def first_introduction_meta(
    entries: list[RegisterEntry],
) -> dict[int, RegisterEntry]:
    seen: dict[int, RegisterEntry] = {}
    for e in entries:
        if e.nid not in seen:
            seen[e.nid] = e
    return seen


def load_forbidden_retired_citations(config_path: Path, active_ids: set[int]) -> set[int]:
    """
    Tombstone keys legacy-N-X document history. A tombstoned X is never reclaimed for a new
    entity (one person, one node); X stays citable only while it is still the active id of the
    same entity (survivor collapse onto the lowest id). Forbid citing N-X when X is not on the
    active register (unmapped ghost ids).
    """
    if not config_path.is_file():
        return set()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    forbidden: set[int] = set()
    for key, meta in (data.get("retired") or {}).items():
        m = re.match(r"legacy-N-(\d+)$", key, re.I)
        if not m:
            continue
        nid = int(m.group(1))
        if nid not in active_ids:
            forbidden.add(nid)
    return forbidden


def load_canonical_nodes(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("nodes") or {})


def load_density_baseline(monument_dir: Path) -> tuple[set[int], set[int]]:
    """
    Optional CKA partial-ingest baseline: N-ids first introduced under BoC eps 1–8
    (ledger order in episode_000) count toward band density without duplicating register rows.
    """
    path = monument_dir / "config" / "preflight_ledger_baseline.json"
    if not path.is_file():
        return set(), set()
    data = json.loads(path.read_text(encoding="utf-8"))
    person = {int(x) for x in data.get("person_node_ids") or []}
    topic = {int(x) for x in data.get("topic_node_ids") or []}
    return person, topic


def load_inscription_node_names(inscription_dir: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    for jpath in sorted(inscription_dir.glob("episode_*.json")):
        if not re.match(r"episode_\d{3}\.json$", jpath.name):
            continue
        data = json.loads(jpath.read_text(encoding="utf-8"))
        for node in data.get("nodes") or []:
            ref = node.get("@id") or node.get("ref") or ""
            m = re.match(r"N-(\d+)$", str(ref))
            if not m:
                continue
            nid = int(m.group(1))
            nm = node.get("name") or node.get("canonical_name") or ""
            if nm:
                names[nid] = _norm_name(str(nm))
    return names


def collect_claim_artifact_related_n_ids(
    episodes: list[tuple[int, str, Path, str]],
) -> set[int]:
    """N-* cited on Claim/Artifact Related Nodes / Mentions lines (Lane-class airtime proxy)."""
    cited: set[int] = set()
    for _ep, _name, _path, content in episodes:
        # Claim register and artifact inline *Related:* (not register section)
        for m in RELATED_NODES_LINE_RE.finditer(content):
            for nm in N_ID_TOKEN_RE.finditer(m.group(1)):
                cited.add(int(nm.group(1)))
        for m in MENTIONS_LINE_RE.finditer(content):
            for nm in N_ID_TOKEN_RE.finditer(m.group(1)):
                cited.add(int(nm.group(1)))
        for m in re.finditer(r"^\*Related:\s*([^*\n]+)\*", content, re.MULTILINE):
            # Skip node-register blocks: only count lines with C- or A- refs
            chunk = m.group(1)
            if re.search(r"\b[CA]-\d", chunk):
                for nm in N_ID_TOKEN_RE.finditer(chunk):
                    cited.add(int(nm.group(1)))
    return cited


def collect_intro_order_from_ledger(
    episodes: list[tuple[int, str, Path, str]],
) -> list[tuple[int, int, int]]:
    """(episode_num, index_in_meta_line, nid) in first-introduction order."""
    ordered: list[tuple[int, int, int]] = []
    seen: set[int] = set()
    for ep, _name, _path, content in episodes:
        m = NEW_NODES_INTRO_RE.search(content)
        if not m:
            continue
        ids = [int(x) for x in re.findall(r"N-(\d+)", m.group(1))]
        for idx, nid in enumerate(ids):
            if nid in seen:
                continue
            seen.add(nid)
            ordered.append((ep, idx, nid))
    return ordered


def check_person_band(
    report: PreflightReport,
    intro: dict[int, RegisterEntry],
    *,
    monument_dir: Path | None = None,
) -> None:
    baseline_person: set[int] = set()
    baseline_topic: set[int] = set()
    if monument_dir is not None:
        baseline_person, baseline_topic = load_density_baseline(monument_dir)
    for nid, ent in intro.items():
        nt = ent.node_type
        is_person = nid < 1000 or nt in PERSON_TYPES
        if nt in TOPIC_BAND_TYPES and nid < 1000:
            report.add(
                "P0",
                "person_band",
                f"{ent.episode_file}: N-{nid} typed {ent.node_type!r} in Person band (<1000)",
                f"N-{nid}",
            )
        if nt in PERSON_TYPES and 1000 <= nid <= TOPIC_BAND_MAX:
            report.add(
                "P0",
                "person_band",
                f"{ent.episode_file}: Person N-{nid} ({ent.name}) sits in N-1000..N-9999 (topic band); persons are N-1..N-999 or N-10000+",
                f"N-{nid}",
            )
        if nid < 1000 and nt in TOPIC_BAND_TYPES:
            report.add(
                "P0",
                "person_band",
                f"{ent.episode_file}: Topic/Org/Place N-{nid} must be N-1000+",
                f"N-{nid}",
            )

    person_present = {n for n in intro if n < 1000} | baseline_person
    person_ids = sorted(person_present)
    if person_ids:
        expected = list(range(1, person_ids[-1] + 1))
        missing = sorted(set(expected) - person_present)
        if missing:
            report.add(
                "P0",
                "person_density",
                f"Person band not dense N-1..N-{person_ids[-1]}; missing {', '.join(f'N-{x}' for x in missing[:20])}"
                + (" …" if len(missing) > 20 else ""),
            )

    topic_present = {n for n in intro if 1000 <= n <= TOPIC_BAND_MAX} | baseline_topic
    topic_ids = sorted(topic_present)
    if topic_ids:
        lo, hi = topic_ids[0], topic_ids[-1]
        missing = [n for n in range(lo, hi + 1) if n not in topic_present]
        if missing:
            report.add(
                "P0",
                "topic_band_density",
                f"N-1000+ band not dense; missing {', '.join(f'N-{x}' for x in missing[:20])}"
                + (" …" if len(missing) > 20 else ""),
            )


def check_intro_order(
    report: PreflightReport,
    ledger_order: list[tuple[int, int, int]],
    intro: dict[int, RegisterEntry],
) -> None:
    """First-introduction order (Episode Ledger Summary) must follow ascending N-id per band."""

    def band(nid: int) -> str:
        return nid_band(nid)

    prev_by_band: dict[str, int] = {}
    for ep, _idx, nid in ledger_order:
        b = band(nid)
        prev_id = prev_by_band.get(b)
        if prev_id is not None and nid < prev_id:
            ent = intro.get(nid)
            name = ent.name if ent else "?"
            report.add(
                "P0",
                "intro_order",
                (
                    f"Swiss cheese: ep{ep} introduces N-{nid} ({name}) after N-{prev_id} "
                    f"but id is lower (ledger New Nodes Introduced order)"
                ),
                f"N-{nid}",
            )
        prev_by_band[b] = nid


def check_related_and_retired(
    report: PreflightReport,
    episodes: list[tuple[int, str, Path, str]],
    intro: dict[int, RegisterEntry],
    forbidden_retired: set[int],
    claim_related: set[int],
) -> None:
    known = set(intro.keys())
    cited_retired: set[tuple[str, int]] = set()
    unknown: set[tuple[str, int]] = set()
    for _ep, ep_name, _path, content in episodes:
        for m in N_ID_TOKEN_RE.finditer(content):
            nid = int(m.group(1))
            if nid in forbidden_retired:
                cited_retired.add((ep_name, nid))
            elif nid not in known:
                unknown.add((ep_name, nid))

    for ep_name, nid in sorted(cited_retired):
        report.add(
            "P0",
            "retired_citation",
            f"{ep_name}: cites tombstone id N-{nid} (not on active register)",
            f"N-{nid}",
        )
    for ep_name, nid in sorted(unknown):
        report.add(
            "P1",
            "unknown_node",
            f"{ep_name}: cites N-{nid} not in Node Register",
            f"N-{nid}",
        )

    for nid, ent in intro.items():
        is_person = ent.node_type in PERSON_TYPES or (ent.nid < 1000 and ent.node_type not in TOPIC_BAND_TYPES)
        if not is_person:
            continue
        if nid not in claim_related:
            report.add(
                "P0",
                "register_orphan",
                f"{ent.episode_file}: Person N-{nid} ({ent.name}) never cited on Claim/Artifact Related Nodes",
                f"N-{nid}",
            )
        elif _register_related_is_empty(ent.register_block):
            report.add(
                "P2",
                "register_related_empty",
                f"{ent.episode_file}: Person N-{nid} ({ent.name}) has empty register *Related* but appears in claims",
                f"N-{nid}",
            )


def check_name_sync(
    report: PreflightReport,
    draft_names: dict[int, str],
    canonical: dict[str, dict[str, Any]],
    inscription_names: dict[int, str],
) -> None:
    for key, meta in canonical.items():
        m = re.match(r"N-(\d+)$", key)
        if not m:
            continue
        nid = int(m.group(1))
        cname = _norm_name(str(meta.get("canonical_name") or ""))
        dname = draft_names.get(nid)
        if dname and cname and _norm_name(dname) != cname:
            report.add(
                "P0",
                "remap_sync",
                f"canonical/nodes.json N-{nid} name {cname!r} != draft register {dname!r}",
                f"N-{nid}",
            )
        iname = inscription_names.get(nid)
        if dname and iname and _norm_name(dname) != iname:
            report.add(
                "P0",
                "remap_sync",
                f"inscription N-{nid} name {iname!r} != draft register {dname!r}",
                f"N-{nid}",
            )

    for nid, dname in draft_names.items():
        key = f"N-{nid}"
        if key not in canonical:
            report.add(
                "P1",
                "remap_sync",
                f"Draft register N-{nid} ({dname}) missing from canonical/nodes.json",
                f"N-{nid}",
            )


def _claim_register_slice(content: str) -> str:
    """Return Claim Register body when a section header is present; else full content."""
    for marker in ("## 5. Claim Register", "## V. Claim Register", "## Claim Register"):
        if marker in content:
            reg = content.split(marker, 1)[1]
            # Stop at next numbered/lettered major section when present.
            nxt = re.search(r"^##\s+[6VI]\b", reg, re.MULTILINE)
            if nxt:
                reg = reg[: nxt.start()]
            return reg
    return content


def _norm_claim_text(s: str) -> str:
    return " ".join(s.strip().split())


def collect_claim_definitions(
    episodes: list[tuple[int, str, Path, str]],
) -> list[tuple[str, int, str, str, str]]:
    """
    Return (claim_id, episode, episode_file, label, claim_body) for real claim headers.
    Skips meta / continuation labels that are not minted definitions.
    """
    rows: list[tuple[str, int, str, str, str]] = []
    for ep, ep_name, _path, content in episodes:
        if ep == 0:
            continue
        reg = _claim_register_slice(content)
        headers = list(CLAIM_HEADER_RE.finditer(reg))
        for i, hm in enumerate(headers):
            cid = hm.group(1)
            label = _norm_claim_text(hm.group(2))
            if not label or CLAIM_META_LABEL_RE.search(label):
                continue
            start = hm.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(reg)
            block = reg[start:end]
            cm = CLAIM_BODY_LINE_RE.search(block)
            body = _norm_claim_text(cm.group(1)) if cm else ""
            rows.append((cid, ep, ep_name, label, body))
    return rows


def check_claim_forks(
    report: PreflightReport,
    episodes: list[tuple[int, str, Path, str]],
) -> None:
    """
    P0: same C-id must not carry different labels (or materially different Claim: bodies)
    across episodes. That pattern is a fork / ID collision, not a revision.

    Fix: mint a new C-id and wire Revises: (and Contradicts: when opposition is explicit).
    Never mutate or reuse the old id for a new airing.
    """
    by_cid: dict[str, list[tuple[int, str, str, str]]] = {}
    for cid, ep, ep_name, label, body in collect_claim_definitions(episodes):
        by_cid.setdefault(cid, []).append((ep, ep_name, label, body))

    for cid, rows in sorted(by_cid.items(), key=lambda kv: int(kv[0].split("-", 1)[1])):
        if len(rows) < 2:
            continue
        # Compare across distinct episodes (same-ep duplicates still checked if labels differ).
        labels = {(ep, label) for ep, _fn, label, _body in rows}
        distinct_labels = {label for _ep, label in labels}
        bodies = {body for _ep, _fn, _label, body in rows if body}
        label_fork = len(distinct_labels) > 1
        body_fork = len(bodies) > 1
        if not label_fork and not body_fork:
            continue
        # Build a short exemplar pair for the message.
        a = rows[0]
        b = next((r for r in rows[1:] if r[2] != a[2] or (r[3] and a[3] and r[3] != a[3])), rows[1])
        reason = []
        if label_fork:
            reason.append(f"labels {a[2]!r} vs {b[2]!r}")
        if body_fork:
            reason.append("Claim: bodies differ")
        locs = ", ".join(sorted({f"ep{ep}({fn})" for ep, fn, _l, _b in rows}))
        report.add(
            "P0",
            "claim_fork",
            (
                f"{cid} reused with different content across {locs}: {'; '.join(reason)}. "
                f"Fork / ID collision, not a revision. Remint a new C-id and add "
                f"Revises: {cid} (and Contradicts: {cid} if the airing explicitly opposes)."
            ),
            cid,
        )


def check_memes(report: PreflightReport, episodes: list[tuple[int, str, Path, str]]) -> None:

    global_term: dict[int, str] = {}
    per_ep: dict[tuple[int, int], str] = {}
    for ep, ep_name, _path, content in episodes:
        for m in MEME_HEADER_RE.finditer(content):
            mid = int(m.group(1))
            term = _norm_name(m.group(2))
            key = (ep, mid)
            if key in per_ep and _norm_name(per_ep[key]) != term:
                report.add(
                    "P0",
                    "meme_reuse",
                    f"{ep_name}: M-{mid} reused for different terms {per_ep[key]!r} vs {term!r}",
                    f"M-{mid}",
                )
            per_ep[key] = term
            prev = global_term.get(mid)
            if prev and prev != term:
                report.add(
                    "P0",
                    "meme_global",
                    f"M-{mid} global term mismatch {prev!r} vs {term!r} ({ep_name})",
                    f"M-{mid}",
                )
            global_term[mid] = term

    if global_term:
        ids = sorted(global_term)
        missing = [i for i in range(1, ids[-1] + 1) if i not in global_term]
        if missing:
            report.add(
                "P1",
                "meme_density",
                f"Meme ids not dense M-1..M-{ids[-1]}; missing {', '.join(f'M-{x}' for x in missing)}",
            )


def check_stamps(report: PreflightReport, episodes: list[tuple[int, str, Path, str]]) -> None:
    for ep, ep_name, _path, content in episodes:
        for m in TIMESTAMP_FIELD_RE.finditer(content):
            field_name, raw = m.group(1), m.group(2).strip()
            if field_name.lower().startswith("event timestamp"):
                continue  # often dates, not HMS
            if not re.search(r"\d:\d", raw):
                continue
            if VALID_HMS_RE.match(raw):
                continue
            if BARE_MS_RE.match(raw):
                report.add(
                    "P1",
                    "stamp_form",
                    f"{ep_name}: {field_name} must be HH:MM:SS (got bare M:SS): {raw!r}",
                    ep_name,
                )
            elif re.search(r"\d:\d{2}:\d{2}", raw):
                continue
            else:
                report.add(
                    "P2",
                    "stamp_form",
                    f"{ep_name}: {field_name} not HH:MM:SS: {raw!r}",
                    ep_name,
                )


def check_tip(report: PreflightReport, monument_dir: Path, tip_sha: str | None, pack_path: Path | None) -> None:
    head = _git_head(monument_dir)
    report.git_head = head
    if tip_sha:
        want = tip_sha.strip().lower()
        if head and not head.lower().startswith(want):
            report.add(
                "P0",
                "tip_match",
                f"git HEAD {head} does not match --tip {tip_sha}",
            )
    if pack_path:
        pack = pack_path if pack_path.is_dir() else pack_path.parent
        tip_file = pack / "TIP.txt"
        manifest = pack / "MANIFEST"
        for label, p in (("TIP.txt", tip_file), ("MANIFEST", manifest)):
            if not p.is_file():
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            sha = _extract_sha_from_pack(text)
            if sha and head and not head.lower().startswith(sha.lower()):
                report.add(
                    "P0",
                    "tip_match",
                    f"pack {label} sha {sha} != git HEAD {head}",
                )
            break


def _extract_sha_from_pack(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if re.fullmatch(r"[0-9a-f]{7,40}", line, re.I):
            return line
        m = re.search(r"\b([0-9a-f]{7,40})\b", line, re.I)
        if m and ("tip" in line.lower() or "sha" in line.lower() or "commit" in line.lower()):
            return m.group(1)
    m = re.search(r"\b([0-9a-f]{40})\b", text, re.I)
    return m.group(1) if m else None


def _git_head(monument_dir: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# ---------------------------------------------------------------------------
# Wave 1 adversarial gates (CKA audit 9f16249: PPL-P0-1, PPL-P1-3, MEN-P1-1,
# CLM-P1-1, CLM-P1-2, CLM-P1-5). All are merge-blocking (P1).
# ---------------------------------------------------------------------------

HONORIFIC_RE = re.compile(
    r"^(?:Father|Fr\.|Pastor|Rev\.|Reverend|Dr\.|Mr\.|Mrs\.|Ms\.|Sen\.|Senator|Rep\.|Judge|Bishop|Rabbi|Sheriff|Officer|Detective)\s+[A-Z]"
)
NAME_SUFFIX_RE = re.compile(r"^(?:Jr\.?|Sr\.?|II|III|IV|V)$")
TRANSCRIPT_MARKER_RE = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]")
CLAIM_TS_LINE_RE = re.compile(r"^Claim Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
CLAIM_HEADER_ANY_RE = re.compile(r"^\*\*(C-\d+)\b[^*\n]*\*\*", re.MULTILINE)
YOUTUBE_ID_META_RE = re.compile(r"^\s*-\s*\*\*YouTube id\*\*:\s*(\S+)", re.MULTILINE | re.IGNORECASE)
END_TOLERANCE_SECONDS = 60
TRANSCRIPT_EXTS = (".txt", ".md")  # CKA: eps 1-10 are .txt, eps 11+ are .md
HOLE_MINTED_RE = re.compile(r"^[ \t]*-[ \t]*Hole-minted Nodes \(([A-Za-z0-9_.\-]+)\):[ \t]*(.*)$", re.MULTILINE)
REUSED_NODES_RE = re.compile(r"^[ \t]*-[ \t]*Reused Nodes Appearing:[ \t]*(.*)$", re.MULTILINE)
NEW_NODES_LINE_RE = re.compile(r"New Nodes Introduced:[ \t]*(.*)$", re.MULTILINE)


def _hms_seconds(raw: str) -> int | None:
    m = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", raw)
    if not m:
        return None
    h, mi, s = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s


def _marker_seconds(tok: str) -> int:
    parts = [int(x) for x in tok.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def find_transcript(monument_dir: Path, ep: int) -> Path | None:
    for sub in ("transcripts_corrected", "transcripts"):
        d = monument_dir / sub
        if not d.is_dir():
            continue
        for ext in TRANSCRIPT_EXTS:
            hits = sorted(d.glob(f"episode_{ep:03d}_*{ext}")) or sorted(d.glob(f"episode_{ep:03d}{ext}"))
            if hits:
                return hits[0]
    return None


def iter_claim_blocks(content: str) -> list[tuple[str, str, str]]:
    """(claim_id, label, block_text) for claim definitions in the Claim Register."""
    reg = _claim_register_slice(content)
    headers = list(CLAIM_HEADER_RE.finditer(reg))
    out: list[tuple[str, str, str]] = []
    for i, hm in enumerate(headers):
        label = _norm_claim_text(hm.group(2))
        if not label or CLAIM_META_LABEL_RE.search(label):
            continue
        end = headers[i + 1].start() if i + 1 < len(headers) else len(reg)
        out.append((hm.group(1), label, reg[hm.start():end]))
    return out


ORG_TOPIC_WORDS = frozenset(
    """inc llc ltd corp corporation company church chapel university college school academy institute foundation
    ministries ministry media news network group party center centre department dept office agency bureau police
    county city state association society committee council club fund trust project program programme act bill court
    hotel ranch street road park lake valley airport base army navy force forces command unit team staff podcast show
    channel magazine times post journal tribune press radio tv records report timeline question anomaly allegation
    allegations claim claims discrepancy issue theory narrative case video footage clip photo statement memo letter
    timeline verification connection relationship scope position background identification review evidence""".split()
)
NAME_STOPWORDS = frozenset("the a an daily new old north south east west great saint".split())
RELATION_WORDS = frozenset(
    "son daughter wife husband brother sister mother father family friend team staff unknown unidentified".split()
)


def _norm_text(s: str) -> str:
    s = s.lower().replace("\u2019", "'").replace("\u2018", "'")
    s = re.sub(r"[^a-z0-9' ]", " ", s)
    return " ".join(s.split())


def _strip_name(name: str) -> str:
    n = re.sub(r"\([^)]*\)|\*[^*]*\*", " ", name).replace('"', " ")
    return _norm_name(n)


def _split_qualifier(name: str) -> tuple[str, str]:
    """Split 'Head - rest' on a spaced dash or colon; return (head, rest)."""
    parts = re.split(r"\s+[\u2014\u2013-]\s+|:\s", name, maxsplit=1)
    return parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")


def _person_name_index(canonical: dict[str, dict[str, Any]]) -> tuple[dict[str, int], set[str], set[str]]:
    full: dict[str, int] = {}
    firsts: set[str] = set()
    lasts: set[str] = set()
    for key, meta in canonical.items():
        m = re.match(r"N-(\d+)$", key)
        if not m:
            continue
        nid = int(m.group(1))
        if nid >= 1000 and nid < PERSON_HIGH_MIN:
            continue
        if str(meta.get("type") or "person").lower() not in PERSON_TYPES:
            continue
        for raw in [meta.get("canonical_name") or "", *(meta.get("aliases") or [])]:
            nm = _split_qualifier(_strip_name(str(raw)))[0]
            nm = re.split(r"'s\b|\u2019s\b", nm)[0].strip()
            if not nm:
                continue
            full.setdefault(_norm_text(nm), nid)
            toks = [t for t in re.findall(r"[A-Za-z][A-Za-z'.\-]*", nm) if not NAME_SUFFIX_RE.match(t)]
            caps = [t for t in toks if t[0].isupper()]
            if len(caps) >= 2:
                if len(caps[0]) >= 3 and caps[0].lower() not in RELATION_WORDS:
                    firsts.add(caps[0].lower())
                if len(caps[-1]) >= 3 and caps[-1].lower() not in RELATION_WORDS:
                    lasts.add(caps[-1].lower())
    return full, firsts, lasts


def person_like_reason(name: str, full: dict[str, int], firsts: set[str], lasts: set[str]) -> str:
    """Return a reason string when a topic-band name looks like a person, else ''.

    A capitalised qualifier after a dash ("Officer X - Body-Cam Anomaly") marks a topic about a
    person, not a person; a lower-case description ("Charlie Kirk - referenced throughout") does not.
    """
    head, rest = _split_qualifier(_strip_name(name))
    if not head or (rest and rest[:1].isupper()):
        return ""
    nh = _norm_text(head)
    if nh in full:
        return f"name matches Person N-{full[nh]}"
    toks = head.split()
    if HONORIFIC_RE.match(head) and 2 <= len(toks) <= 3:
        return "honorific plus personal name"
    words = [w.strip(".,") for w in toks]
    if len(words) == 2 and all(re.fullmatch(r"[A-Z][a-z][a-zA-Z'\-]*", w) for w in words):
        low = [w.lower() for w in words]
        if any(w in ORG_TOPIC_WORDS or w in NAME_STOPWORDS for w in low):
            return ""
        if low[0] in firsts:
            return "first-name plus surname shape (first name shared with a Person node)"
        if low[1] in lasts:
            return "first-name plus surname shape (surname shared with a Person node)"
    return ""


def check_person_like_topic(
    report: PreflightReport,
    intro: dict[int, RegisterEntry],
    canonical: dict[str, dict[str, Any]],
) -> None:
    """P1: a person minted in the topic band (N-1000..N-9999) under a non-person type."""
    full, firsts, lasts = _person_name_index(canonical)
    candidates: list[tuple[int, str, str, str]] = []
    for nid, ent in intro.items():
        if 1000 <= nid <= TOPIC_BAND_MAX:
            candidates.append((nid, ent.name, ent.node_type, ent.episode_file))
    for key, meta in canonical.items():
        m = re.match(r"N-(\d+)$", key)
        if m and 1000 <= int(m.group(1)) <= TOPIC_BAND_MAX:
            candidates.append(
                (int(m.group(1)), str(meta.get("canonical_name") or ""), str(meta.get("type") or "").lower(), "canonical/nodes.json")
            )
    seen: set[int] = set()
    for nid, name, ntype, where in candidates:
        if nid in seen:
            continue
        if ntype in PERSON_TYPES:
            if where == "canonical/nodes.json":
                seen.add(nid)
                report.add(
                    "P1",
                    "person_like_topic",
                    f"{where}: N-{nid} ({name}) is typed person in the topic band; persons live in N-1..N-999",
                    f"N-{nid}",
                )
            continue  # register rows typed person are already P0 person_band
        reason = person_like_reason(name, full, firsts, lasts)
        if reason:
            seen.add(nid)
            report.add(
                "P1",
                "person_like_topic",
                f"{where}: N-{nid} ({name}) typed {ntype or 'untyped'!r} in topic band but looks like a person ({reason}); "
                "move into a Person hole N-1..N-999 or collapse onto the existing Person",
                f"N-{nid}",
            )


GROUNDING_COMMON = frozenset(
    """the and of mr mrs ms dr jr sr st de la van von al el bin ben john james michael david robert mark paul peter chris
    jack mike matt tom tim joe dan bob bill steve scott ryan josh andrew kevin brian eric sam nick alex adam jason
    justin tyler lance charlie erika candace donald george thomas william richard joseph charles daniel jennifer mary
    elizabeth anna sarah amy lisa laura karen susan emily jessica host director father mother son daughter brother
    sister wife husband pastor reverend anonymous unknown unnamed producer caller resident victim operator camera
    event""".split()
)


def grounding_keys(names: list[str]) -> tuple[set[str], set[str]]:
    """Normalized full names (>=4 chars) and distinctive name words (>=4 chars, not common first names)."""
    full: set[str] = set()
    parts: set[str] = set()
    for raw in names:
        if not raw:
            continue
        nm = re.sub(r"\([^)]*\)|\*[^*]*\*", " ", str(raw)).replace('"', " ")
        nn = _norm_text(nm)
        if len(nn) >= 4 or re.fullmatch(r"\s*[A-Z]{3}\s*", nm):
            full.add(nn)  # 3-letter all-caps aliases (PBD, RFK) are distinctive
        for w in nn.split():
            if len(w) >= 4 and w not in GROUNDING_COMMON:
                parts.add(w)
    return full, parts


def load_gate_config(monument_dir: Path) -> dict[str, Any]:
    path = monument_dir / "config" / "preflight_gates.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def transcript_segments(raw: str) -> list[tuple[int, int, str]]:
    """(start_s, end_s, normalized text) per transcript marker, in file order.

    A segment runs from its marker to the next marker; an out-of-order marker (chapter list in the
    header) covers only its own second.
    """
    marks = list(TRANSCRIPT_MARKER_RE.finditer(raw))
    out: list[tuple[int, int, str]] = []
    for i, m in enumerate(marks):
        start = _marker_seconds(m.group(1))
        nxt = marks[i + 1] if i + 1 < len(marks) else None
        nsec = _marker_seconds(nxt.group(1)) if nxt else start + 60
        end = nsec if nsec >= start else start
        text = raw[m.end(): nxt.start() if nxt else len(raw)]
        out.append((start, end, _norm_text(text)))
    return out


def claim_window(block: str, ep: int, cfg: dict[str, Any]) -> tuple[int, int, int] | None:
    """(start - w, end + w, w) around the Claim Timestamp, or None when windowing is off / no timestamp."""
    w = cfg.get("window_seconds")
    if not w:
        return None
    if ep <= int(cfg.get("early_max_episode") or 0):
        w = cfg.get("window_seconds_early") or w
    tm = CLAIM_TS_LINE_RE.search(block)
    if not tm:
        return None
    secs = [int(h) * 3600 + int(mi) * 60 + int(sec) for h, mi, sec in re.findall(r"(\d{1,2}):(\d{2}):(\d{2})", tm.group(1))]
    if not secs or max(secs) <= 1:
        return None  # missing or placeholder stamp (00:00:00-00:00:01): ground on the whole episode
    return min(secs) - int(w), max(secs) + int(w), int(w)


def check_mention_grounding(
    report: PreflightReport,
    monument_dir: Path,
    episodes: list[tuple[int, str, Path, str]],
    intro: dict[int, RegisterEntry],
    canonical: dict[str, dict[str, Any]],
) -> None:
    """P1: a Mentions person whose name is absent from the claim text and the transcript near the claim.

    Optional config/preflight_gates.json:
      {"mention_grounding": {"exempt_ids": ["N-3"],
                             "first_name_ok": ["N-1", "N-2"],
                             "window_seconds": 240, "window_seconds_early": 480, "early_max_episode": 10,
                             "reviewed": [{"claim": "C-1", "node": "N-2", "reason": "..."}]}}
    exempt_ids covers the show host; first_name_ok lets the principals ground on a first name
    ("Charlie", "Erika"); reviewed rows are human-verified role references (e.g. "her husband").
    With window_seconds set, the transcript is searched only within +-window of the Claim
    Timestamp (the early value applies to episodes <= early_max_episode). Claims with no timestamp,
    a placeholder 00:00:00-00:00:01 stamp, or a timestamp past the last transcript marker fall
    back to the whole episode transcript.
    """
    cfg = load_gate_config(monument_dir).get("mention_grounding") or {}
    exempt = {str(x) for x in cfg.get("exempt_ids") or []}
    first_ok = {str(x) for x in cfg.get("first_name_ok") or []}
    reviewed = {(str(r.get("claim")), str(r.get("node"))) for r in cfg.get("reviewed") or []}
    keys_by_nid: dict[int, tuple[set[str], set[str]]] = {}

    def keys(nid: int) -> tuple[set[str], set[str]]:
        if nid not in keys_by_nid:
            meta = canonical.get(f"N-{nid}") or {}
            names = [str(meta.get("canonical_name") or ""), *(str(a) for a in meta.get("aliases") or [])]
            ent = intro.get(nid)
            if ent:
                names.append(ent.name)
            full, parts = grounding_keys(names)
            if f"N-{nid}" in first_ok:
                for nm in names:
                    toks = _norm_text(re.sub(r"\([^)]*\)", " ", nm)).split()
                    if toks and len(toks[0]) >= 3:
                        parts.add(toks[0])
            keys_by_nid[nid] = (full, parts)
        return keys_by_nid[nid]

    def hit(text: str, ks: tuple[set[str], set[str]]) -> bool:
        return any(re.search(r"\b" + re.escape(k) + r"\b", text) for k in ks[0] | ks[1])

    for ep, ep_name, _path, content in episodes:
        tpath = find_transcript(monument_dir, ep)
        if tpath is None:
            continue
        raw = tpath.read_text(encoding="utf-8", errors="replace")
        transcript = _norm_text(TRANSCRIPT_MARKER_RE.sub(" ", raw))
        segments = transcript_segments(raw)
        last_mark = max((seg[0] for seg in segments), default=None)
        cache: dict[int, bool] = {}
        for cid, _label, block in iter_claim_blocks(content):
            mm = MENTIONS_LINE_RE.search(block)
            if not mm:
                continue
            text = _norm_text(block)
            win = claim_window(block, ep, cfg)
            if win is not None and (last_mark is None or win[0] + win[2] > last_mark + END_TOLERANCE_SECONDS):
                win = None  # past the end: claim_ts_past_end reports it; ground on the whole episode
            wtext = None
            if win is not None:
                wtext = " ".join(t for a, b, t in segments if b >= win[0] and a <= win[1])
            for tok in N_ID_TOKEN_RE.finditer(mm.group(1)):
                nid = int(tok.group(1))
                key = f"N-{nid}"
                if 1000 <= nid < PERSON_HIGH_MIN or key in exempt or (cid, key) in reviewed:
                    continue
                ks = keys(nid)
                if not ks[0] and not ks[1]:
                    continue
                if hit(text, ks):
                    continue
                if wtext is not None:
                    if hit(wtext, ks):
                        continue
                    where = f"the transcript within +-{win[2]}s of the claim timestamp"
                else:
                    if nid not in cache:
                        cache[nid] = hit(transcript, ks)
                    if cache[nid]:
                        continue
                    where = "the episode transcript"
                name = (canonical.get(key) or {}).get("canonical_name") or (intro[nid].name if nid in intro else "?")
                report.add(
                    "P1",
                    "mention_grounding",
                    f"{ep_name}: {cid} Mentions {key} ({name}) but the name is absent from the claim text and {where}",
                    f"{cid}:{key}",
                )


def _episode_end_seconds(monument_dir: Path, ep: int, content: str, durations: dict[str, int]) -> tuple[int | None, str]:
    yt = None
    m = YOUTUBE_ID_META_RE.search(content)
    if m:
        yt = m.group(1).strip()
    tpath = find_transcript(monument_dir, ep)
    if not yt and tpath is not None:
        tm = re.match(rf"episode_{ep:03d}_(.+)\.(?:txt|md)$", tpath.name)
        if tm:
            yt = tm.group(1)
    if yt and yt in durations:
        return int(durations[yt]), f"YouTube duration ({yt})"
    if tpath is not None:
        marks = TRANSCRIPT_MARKER_RE.findall(tpath.read_text(encoding="utf-8", errors="replace"))
        if marks:
            return max(_marker_seconds(x) for x in marks), "last transcript marker"
    return None, ""


def check_claim_ts_past_end(
    report: PreflightReport,
    monument_dir: Path,
    episodes: list[tuple[int, str, Path, str]],
) -> None:
    """P1: Claim Timestamp after the end of the episode.

    End = config/yt_durations.json duration for the episode YouTube id, else the last transcript
    marker. Monuments without yt_durations.json skip this gate.
    """
    dpath = monument_dir / "config" / "yt_durations.json"
    if not dpath.is_file():
        return  # gate needs authoritative durations; monuments without yt_durations.json opt out
    durations = dict(json.loads(dpath.read_text(encoding="utf-8")).get("by_youtube_id") or {})
    for ep, ep_name, _path, content in episodes:
        end, source = _episode_end_seconds(monument_dir, ep, content, durations)
        if end is None:
            continue
        for cid, _label, block in iter_claim_blocks(content):
            tm = CLAIM_TS_LINE_RE.search(block)
            if not tm:
                continue
            start = _hms_seconds(tm.group(1))
            if start is None:
                continue
            if start > end + END_TOLERANCE_SECONDS:
                report.add(
                    "P1",
                    "claim_ts_past_end",
                    f"{ep_name}: {cid} Claim Timestamp {tm.group(1).strip()!r} is past the episode end ({end // 3600:02d}:{end % 3600 // 60:02d}:{end % 60:02d}, {source})",
                    cid,
                )


def check_claims_missing_from_drafts(
    report: PreflightReport,
    monument_dir: Path,
    episodes: list[tuple[int, str, Path, str]],
) -> None:
    """P1: claim minted in the inscription ledger but not defined in any draft."""
    ins_dir = monument_dir / "inscription"
    if not ins_dir.is_dir():
        return
    defined: set[str] = set()
    for _ep, _name, _path, content in episodes:
        defined.update(m.group(1) for m in CLAIM_HEADER_RE.finditer(content))
    for jpath in sorted(ins_dir.glob("episode_*.json")):
        if not re.match(r"episode_\d{3}\.json$", jpath.name):
            continue
        data = json.loads(jpath.read_text(encoding="utf-8"))
        for claim in data.get("claims") or []:
            cid = str(claim.get("@id") or claim.get("ref") or "")
            if re.match(r"C-\d+$", cid) and cid not in defined:
                report.add(
                    "P1",
                    "claim_missing_from_drafts",
                    f"inscription/{jpath.name}: {cid} is minted in the inscription but not defined in any draft",
                    cid,
                )


def check_duplicate_claim_headers(
    report: PreflightReport,
    episodes: list[tuple[int, str, Path, str]],
) -> None:
    """P1: the same C-id header appears more than once (including residue headers like **C-1 / C-2**)."""
    seen: dict[str, list[str]] = {}
    for _ep, ep_name, _path, content in episodes:
        reg = _claim_register_slice(content)
        base = content.find(reg) if reg else 0
        for m in CLAIM_HEADER_ANY_RE.finditer(reg):
            line_no = content.count("\n", 0, max(base, 0) + m.start()) + 1
            seen.setdefault(m.group(1), []).append(f"{ep_name}:{line_no}")
    for cid, locs in sorted(seen.items(), key=lambda kv: int(kv[0][2:])):
        if len(locs) > 1:
            report.add(
                "P1",
                "duplicate_claim_header",
                f"{cid} header defined {len(locs)} times ({', '.join(locs)}); no id may be defined twice",
                cid,
            )


def check_tombstone_collision(report: PreflightReport, canonical: dict[str, dict[str, Any]]) -> None:
    """P1: an active canonical id listed in another node's retired_ids."""
    for key, meta in canonical.items():
        for rid in meta.get("retired_ids") or []:
            if rid in canonical and rid != key:
                report.add(
                    "P1",
                    "tombstone_collision",
                    f"canonical/nodes.json: active {rid} ({canonical[rid].get('canonical_name')}) is also a retired id of {key} ({meta.get('canonical_name')})",
                    rid,
                )


ANNOT_RE = re.compile(r"\b(N-\d+)\s*\(([^()\n]{2,160})\)")
ANNOT_FILLER = frozenset(
    "assumed reference ref node entity if exists existing new prior likely possibly aka the de del da van von la le jr sr ii iii iv and or also".split()
)
ANNOT_DESCRIPTOR_CAPS = frozenset(
    "existing new context topic person people investigation referenced see cross host guest none tbd unknown unidentified verification note".split()
)
ANNOT_STOP = frozenset("the a an of and for with from".split())


def annotation_label_name(label: str) -> str:
    """Personal-name head of an 'N-x (Label)' annotation, or '' when the label is descriptive.

    The head is the text before a spaced dash, comma, semicolon, colon, ' / ' or 'vs'. Every word
    must be Capitalised (or filler such as 'existing', 'assumed', 'node'); any lower-case word or
    number marks a description ("verbal reference", "2 claims"), which is not checked.
    """
    head = re.split(r"\s+[\u2014\u2013-]\s+|,|;|:|\s/\s|\s+vs\.?\s+", label, maxsplit=1)[0]
    head = head.strip().strip('"\u201c\u201d')
    caps: list[str] = []
    for tok in head.split():
        w = tok.strip('.,"\u201c\u201d\'')
        if not w or w.lower() in ANNOT_FILLER:
            continue
        if re.fullmatch(r"[A-Z][A-Za-z'.\-]*|[A-Z]\.?", w):
            caps.append(w)
            continue
        return ""
    if not caps or (len(caps) == 1 and caps[0].lower() in ANNOT_DESCRIPTOR_CAPS):
        return ""
    return " ".join(caps)


def annotation_name_matches(label: str, names: list[str]) -> bool:
    """Label agrees with one of the node names: equal/contained, a shared word (>=3 chars), or acronym."""
    nl = _norm_text(label)
    lt = {t for t in nl.split() if len(t) >= 3 and t not in ANNOT_STOP}
    for n in names:
        nn = _norm_text(re.sub(r"\([^)]*\)", " ", n))
        if not nn:
            continue
        if nl == nn or nl in nn or nn in nl:
            return True
        if lt & {t for t in nn.split() if len(t) >= 3 and t not in ANNOT_STOP}:
            return True
        acr = "".join(w[0] for w in re.findall(r"[A-Za-z]+", n) if w[0].isupper()).lower()
        if len(nl.replace(" ", "")) >= 2 and nl.replace(" ", "") == acr:
            return True
    return False


def check_name_annotation_mismatch(
    report: PreflightReport,
    episodes: list[tuple[int, str, Path, str]],
    register: list[RegisterEntry],
    canonical: dict[str, dict[str, Any]],
) -> None:
    """P1: an inline 'N-x (Name)' annotation whose Name is not node x (wrong-person id use).

    Names come from canonical/nodes.json (canonical_name + aliases) when the id is there, else from
    every register row for the id. Descriptive labels ("verbal reference") are ignored.
    """
    reg_names: dict[int, list[str]] = {}
    for e in register:
        reg_names.setdefault(e.nid, []).append(e.name)
    for _ep, ep_name, _path, content in episodes:
        for line_no, line in enumerate(content.splitlines(), 1):
            for m in ANNOT_RE.finditer(line):
                label = annotation_label_name(m.group(2))
                if not label:
                    continue
                key = m.group(1)
                meta = canonical.get(key)
                names = (
                    [str(meta.get("canonical_name") or ""), *(str(a) for a in meta.get("aliases") or [])]
                    if meta
                    else reg_names.get(int(key[2:]), [])
                )
                if not names:
                    report.add(
                        "P1",
                        "name_annotation_mismatch",
                        f"{ep_name}:{line_no}: {key} ({m.group(2)}) annotates an id with no node",
                        f"{ep_name}:{line_no}:{key}",
                    )
                elif not annotation_name_matches(label, names):
                    report.add(
                        "P1",
                        "name_annotation_mismatch",
                        f"{ep_name}:{line_no}: {key} is annotated as {label!r} but node {key} is {names[0]!r}; retarget to the right id or drop it",
                        f"{ep_name}:{line_no}:{key}",
                    )


def collect_hole_minted(episodes: list[tuple[int, str, Path, str]]) -> list[tuple[int, str, str, int, int]]:
    """(episode, episode_file, batch, index, nid) for every 'Hole-minted Nodes (batch): ...' ledger line."""
    out: list[tuple[int, str, str, int, int]] = []
    for ep, ep_name, _path, content in episodes:
        for m in HOLE_MINTED_RE.finditer(content):
            for idx, tok in enumerate(re.findall(r"N-(\d+)", m.group(2))):
                out.append((ep, ep_name, m.group(1), idx, int(tok)))
    return out


def check_hole_minted(
    report: PreflightReport,
    monument_dir: Path,
    episodes: list[tuple[int, str, Path, str]],
    intro: dict[int, RegisterEntry],
    canonical: dict[str, dict[str, Any]],
) -> None:
    """P0 order lock for ids minted into free holes below the band frontier.

    Hole mints cannot sit on 'New Nodes Introduced' (that line must ascend) and must not hide on
    'Reused Nodes Appearing'. They go on '  - Hole-minted Nodes (<batch>): N-a, N-b' in the episode
    where each id gets its first register row. Per batch and band, ids must ascend in episode
    order (compact first-introduction order), and person-band batches must be compact: no free
    person id (not active, not tombstoned, not on the episode_000 baseline ledger) may remain
    below the batch maximum.
    """
    minted = collect_hole_minted(episodes)
    if not minted:
        return
    new_ids: dict[int, set[int]] = {}
    reused_ids: dict[int, set[int]] = {}
    baseline: set[int] = set()
    for ep, _name, _path, content in episodes:
        m = NEW_NODES_LINE_RE.search(content)
        new_ids[ep] = {int(x) for x in re.findall(r"N-(\d+)", m.group(1))} if m else set()
        rm = REUSED_NODES_RE.search(content)
        reused_ids[ep] = {int(x) for x in re.findall(r"N-(\d+)", rm.group(1))} if rm else set()
        if ep == 0:
            for lm in re.finditer(r"N-(\d+)", content):
                baseline.add(int(lm.group(1)))
    tombstoned: set[int] = set()
    rpath = monument_dir / "config" / "retired_node_ids.json"
    if rpath.is_file():
        for key in (json.loads(rpath.read_text(encoding="utf-8")).get("retired") or {}):
            km = re.search(r"N-(\d+)$", key)
            if km:
                tombstoned.add(int(km.group(1)))
    active = set(intro) | {int(k[2:]) for k in canonical if re.match(r"N-\d+$", k)}
    seq: dict[tuple[str, str], list[tuple[int, str, int]]] = {}
    for ep, ep_name, batch, _idx, nid in minted:
        ent = intro.get(nid)
        if ent is None:
            report.add("P0", "hole_mint_order", f"{ep_name}: Hole-minted N-{nid} ({batch}) has no register row", f"N-{nid}")
        elif ent.episode != ep:
            report.add(
                "P0",
                "hole_mint_order",
                f"{ep_name}: Hole-minted N-{nid} ({ent.name}) is first registered in {ent.episode_file}; list it there",
                f"N-{nid}",
            )
        if nid in new_ids.get(ep, set()) or nid in reused_ids.get(ep, set()):
            report.add(
                "P0",
                "hole_mint_order",
                f"{ep_name}: Hole-minted N-{nid} is also on the New or Reused line of the same episode",
                f"N-{nid}",
            )
        seq.setdefault((batch, nid_band(nid)), []).append((ep, ep_name, nid))
    for (batch, band), items in seq.items():
        prev = None
        for ep, ep_name, nid in items:
            if prev is not None and nid < prev[2]:
                report.add(
                    "P0",
                    "hole_mint_order",
                    f"{ep_name}: Hole-minted N-{nid} (batch {batch}) is introduced after N-{prev[2]} ({prev[1]}) but has a lower id; renumber to first-introduction order",
                    f"N-{nid}",
                )
            prev = (ep, ep_name, nid)
        if band == "person":
            top = max(nid for _e, _n, nid in items)
            free = [x for x in range(1, top) if x not in active and x not in tombstoned and x not in baseline]
            if free:
                report.add(
                    "P0",
                    "hole_mint_order",
                    f"Hole-minted batch {batch} reaches N-{top} but free person ids remain below it: "
                    + ", ".join(f"N-{x}" for x in free[:10]),
                    f"N-{top}",
                )


def run_preflight(
    monument_slug: str,
    *,
    tip_sha: str | None = None,
    pack_path: Path | None = None,
    skip_inscription: bool = False,
) -> PreflightReport:
    monument_dir = MONUMENTS_ROOT / monument_slug
    report = PreflightReport(monument=monument_slug, monument_dir=str(monument_dir))
    if not monument_dir.is_dir():
        report.add("P0", "monument", f"Unknown monument directory: {monument_dir}")
        return report

    scaffold_flag = monument_dir / "config" / "scaffold_only.json"
    drafts_dir = monument_dir / "drafts"
    if scaffold_flag.is_file() and not any(drafts_dir.glob("episode_*.md")):
        report.add(
            "WARN",
            "scaffold",
            "Monument is scaffold-only (config/scaffold_only.json); draft preflight gates skipped",
        )
        return report

    if not drafts_dir.is_dir():
        report.add("P0", "monument", f"Missing drafts/: {drafts_dir}")
        return report

    episodes = load_draft_episodes(drafts_dir)
    if not episodes:
        report.add("P0", "monument", "No episode_*.md drafts found")
        return report

    register = collect_register_entries(episodes)
    intro = first_introduction_meta(register)
    draft_names = {e.nid: _norm_name(e.name) for e in register}

    ledger_order = collect_intro_order_from_ledger(episodes)
    if not ledger_order:
        report.add(
            "P1",
            "intro_order",
            "No 'New Nodes Introduced' ledger lines found in drafts",
        )

    active_ids = set(intro.keys())
    forbidden_retired = load_forbidden_retired_citations(
        monument_dir / "config" / "retired_node_ids.json", active_ids
    )
    ingest_episodes = [e for e in episodes if e[0] > 0]
    claim_related = collect_claim_artifact_related_n_ids(ingest_episodes)

    check_person_band(report, intro, monument_dir=monument_dir)
    check_intro_order(report, ledger_order, intro)
    check_related_and_retired(
        report, ingest_episodes, intro, forbidden_retired, claim_related
    )
    check_stamps(report, ingest_episodes)
    check_claim_forks(report, ingest_episodes)
    check_memes(report, episodes)

    canonical = load_canonical_nodes(monument_dir / "canonical" / "nodes.json")
    inscription_names: dict[int, str] = {}
    if not skip_inscription:
        ins_dir = monument_dir / "inscription"
        if ins_dir.is_dir():
            inscription_names = load_inscription_node_names(ins_dir)
        else:
            report.add("P1", "remap_sync", f"Missing inscription/ at {ins_dir}")
    check_name_sync(report, draft_names, canonical, inscription_names)

    # Wave 1 adversarial gates (P1, merge-blocking).
    check_person_like_topic(report, intro, canonical)
    check_mention_grounding(report, monument_dir, ingest_episodes, intro, canonical)
    check_claim_ts_past_end(report, monument_dir, ingest_episodes)
    if not skip_inscription:
        check_claims_missing_from_drafts(report, monument_dir, ingest_episodes)
    check_duplicate_claim_headers(report, ingest_episodes)
    check_tombstone_collision(report, canonical)
    check_name_annotation_mismatch(report, ingest_episodes, register, canonical)
    check_hole_minted(report, monument_dir, episodes, intro, canonical)

    check_tip(report, monument_dir, tip_sha, pack_path)
    return report


def print_human(report: PreflightReport) -> None:
    counts = report.counts()
    print(f"DIA preflight — {report.monument} ({report.monument_dir})")
    if report.git_head:
        print(f"  git HEAD: {report.git_head[:12]}")
    print(
        f"  findings: P0={counts['P0']} P1={counts['P1']} P2={counts['P2']} WARN={counts['WARN']}"
    )
    for sev in ("P0", "P1", "P2", "WARN"):
        group = [f for f in report.findings if f.severity == sev]
        if not group:
            continue
        print(f"\n[{sev}]")
        for f in group:
            loc = f" ({f.location})" if f.location else ""
            print(f"  - [{f.check}]{loc} {f.message}")
    if report.hard_fail():
        print("\nRESULT: FAIL (merge-blocking)")
    else:
        print("\nRESULT: PASS (no P0/P1)")


WAVE1_FIXTURE_DRAFT = """## 1. Meta-Data

- **YouTube id**: vid001
- **Episode Ledger Summary**:
  - New Nodes Introduced: N-1, N-2, N-1001
  - Reused Nodes Appearing: none

## 4. Node Register

**N-1** Alice Smith

Node Type: Person

*Related: C-1*

**N-2** Bob Jones

Node Type: Person

*Related: C-1*

**N-1001** Alice Smith

*Related: C-1*

## 5. Claim Register

**C-1** Alice speaks

Claim Timestamp: 00:00:10
Claim: Alice Smith describes the event.
Mentions: N-1, N-2
Related Nodes: N-1001

---

**C-2** Late claim

Claim Timestamp: 00:30:00
Claim: Alice Smith adds a detail after the show ended.
Mentions: N-1

---

**C-1** Alice speaks

Claim Timestamp: 00:00:10
Claim: Alice Smith describes the event.
Mentions: N-1

---
"""


WAVE1_FIXTURE_DRAFT_EP2 = """## 1. Meta-Data

- **YouTube id**: vid002
- **Episode Ledger Summary**:
  - New Nodes Introduced: N-5
  - Reused Nodes Appearing: N-1
  - Hole-minted Nodes (fx): N-4, N-3

## 4. Node Register

**N-5** Carol King

Node Type: Person

*Related: C-3*

**N-4** Dan Brown

Node Type: Person

*Related: C-3*

**N-3** Eve Adams

Node Type: Person

*Related: C-3*

## 5. Claim Register

**C-3** Carol King on the radio

Claim Timestamp: 00:20:00
Claim: Carol King says Eve Adams staged the event; N-1 (Bob Jones) is cited for context.
Mentions: N-3, N-4, N-5
Related Nodes: N-1

---
"""


def build_wave1_fixture(root: Path) -> None:
    """Fixture monument that trips every Wave 1 gate (used by --self-test and pytest).

    Episode 2 uses a .md transcript, a +-240 s grounding window (Dan Brown is named only at
    00:00:30, far from the 00:20:00 claim), a wrong-person 'N-1 (Bob Jones)' annotation, and a
    Hole-minted line out of first-introduction order (N-4 before N-3).
    """
    for sub in ("drafts", "config", "canonical", "inscription", "transcripts_corrected"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "drafts" / "episode_001.md").write_text(WAVE1_FIXTURE_DRAFT, encoding="utf-8")
    (root / "drafts" / "episode_002.md").write_text(WAVE1_FIXTURE_DRAFT_EP2, encoding="utf-8")
    (root / "transcripts_corrected" / "episode_001_vid001.txt").write_text(
        "[00:00:05] Alice Smith speaks about the event. [00:01:50] Thanks for watching.\n", encoding="utf-8"
    )
    (root / "transcripts_corrected" / "episode_002_vid002.md").write_text(
        "# Episode 2\n\n[00:00:30] Dan Brown said hello.\n\n[00:01:00] Other topics.\n\n[00:19:50] Carol King is on air with Eve Adams.\n\n[00:30:00] Bye.\n",
        encoding="utf-8",
    )
    (root / "config" / "preflight_gates.json").write_text(
        json.dumps({"mention_grounding": {"window_seconds": 240}}), encoding="utf-8"
    )
    (root / "config" / "yt_durations.json").write_text(
        json.dumps({"by_youtube_id": {"vid001": 120}}), encoding="utf-8"
    )
    (root / "config" / "retired_node_ids.json").write_text(json.dumps({"retired": {}}), encoding="utf-8")
    (root / "canonical" / "nodes.json").write_text(
        json.dumps(
            {
                "nodes": {
                    "N-1": {"canonical_name": "Alice Smith", "type": "person", "retired_ids": ["N-2"]},
                    "N-2": {"canonical_name": "Bob Jones", "type": "person"},
                    "N-1001": {"canonical_name": "Alice Smith", "type": "topic"},
                }
            }
        ),
        encoding="utf-8",
    )
    (root / "inscription" / "episode_001.json").write_text(
        json.dumps(
            {
                "claims": [{"@id": "C-1"}, {"@id": "C-2"}, {"@id": "C-9"}],
                "nodes": [
                    {"@id": "N-1", "name": "Alice Smith"},
                    {"@id": "N-2", "name": "Bob Jones"},
                    {"@id": "N-1001", "name": "Alice Smith"},
                ],
            }
        ),
        encoding="utf-8",
    )


WAVE1_CHECKS = (
    "person_like_topic",
    "mention_grounding",
    "claim_ts_past_end",
    "claim_missing_from_drafts",
    "duplicate_claim_header",
    "tombstone_collision",
    "name_annotation_mismatch",
)

# Wave 1 P0 gates the fixture must trip.
WAVE1_P0_CHECKS = ("hole_mint_order",)

# Fixture findings that prove .md transcripts are read and grounding is windowed.
WAVE1_FIXTURE_LOCATIONS = ("C-3:N-4",)


def _run_fixture(slug: str, root: Path, *, skip_inscription: bool) -> PreflightReport:
    link = MONUMENTS_ROOT / slug
    made_link = False
    if not link.exists():
        link.symlink_to(root)
        made_link = True
    try:
        return run_preflight(slug, skip_inscription=skip_inscription)
    finally:
        if made_link:
            link.unlink()


def _self_test() -> int:
    """Minimal fixtures proving P0 gates fire."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "test_mon"
        drafts = root / "drafts"
        drafts.mkdir(parents=True)
        (root / "config").mkdir()
        (root / "canonical").mkdir()
        (root / "config" / "retired_node_ids.json").write_text(
            json.dumps({"retired": {"legacy-N-99": {"survives_as": "N-1"}}}),
            encoding="utf-8",
        )
        (root / "canonical" / "nodes.json").write_text(
            json.dumps({"nodes": {"N-1000": {"canonical_name": "Wrong Org", "type": "organization"}}}),
            encoding="utf-8",
        )
        md = """## 4. Node Register

**N-1000** Bad Person Name

Node Type: Person

*Related: C-1000*

## 5. Claim Register
**C-1000** test

Related Nodes: N-1000, N-99
Claim Timestamp: 5:30
Video Timestamp: 00:05:30
"""
        (drafts / "episode_001.md").write_text(md, encoding="utf-8")
        md2 = """## 4. Node Register

**N-1** Alice

Node Type: Person

*Related: C-1000*

## 5. Claim Register
**C-1000** different label entirely

Claim: A materially different claim body for the same id.
Related Nodes: N-1
Claim Timestamp: 00:01:00
"""
        (drafts / "episode_002.md").write_text(md2, encoding="utf-8")

        # Patch MONUMENTS_ROOT for test
        slug = "test_mon"
        # Run inline by pointing monument dir via symlink under monuments
        link = MONUMENTS_ROOT / slug
        made_link = False
        if not link.exists():
            link.symlink_to(root)
            made_link = True
        try:
            report = run_preflight(slug, skip_inscription=True)
        finally:
            if made_link:
                link.unlink()

        assert report.hard_fail(), report.findings
        checks = {f.check for f in report.findings if f.severity == "P0"}
        assert "person_band" in checks
        assert "retired_citation" in checks
        assert "claim_fork" in checks

    # Wave 1 gates: each must fire as P1 on its fixture.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "test_mon_w1"
        build_wave1_fixture(root)
        report = _run_fixture("test_mon_w1", root, skip_inscription=False)
        assert report.hard_fail(), report.findings
        p1 = {f.check for f in report.findings if f.severity == "P1"}
        missing = [c for c in WAVE1_CHECKS if c not in p1]
        assert not missing, (missing, report.findings)
        p0 = {f.check for f in report.findings if f.severity == "P0"}
        missing = [c for c in WAVE1_P0_CHECKS if c not in p0]
        assert not missing, (missing, report.findings)
        locs = {f.location for f in report.findings if f.check == "mention_grounding"}
        assert set(WAVE1_FIXTURE_LOCATIONS) <= locs, (locs, report.findings)
        assert "C-3:N-3" not in locs and "C-3:N-5" not in locs, locs
    print("self-test: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DIA monument preflight (merge-blocking gates)")
    ap.add_argument("--monument", required=False, help="Monument slug under projects/monuments/")
    ap.add_argument("--json", type=Path, help="Write machine-readable JSON report")
    ap.add_argument("--tip", dest="tip_sha", help="Require git HEAD to match this commit prefix")
    ap.add_argument("--pack", type=Path, help="DIA pack dir containing TIP.txt or MANIFEST")
    ap.add_argument("--skip-inscription", action="store_true", help="Skip inscription name sync")
    ap.add_argument("--self-test", action="store_true", help="Run built-in fixture checks")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not args.monument:
        ap.error("--monument is required unless --self-test")

    report = run_preflight(
        args.monument,
        tip_sha=args.tip_sha,
        pack_path=args.pack,
        skip_inscription=args.skip_inscription,
    )
    print_human(report)
    if args.json:
        payload = {
            "monument": report.monument,
            "monument_dir": report.monument_dir,
            "git_head": report.git_head,
            "counts": report.counts(),
            "hard_fail": report.hard_fail(),
            "findings": [asdict(f) for f in report.findings],
        }
        args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote JSON report to {args.json}")
    return 1 if report.hard_fail() else 0


if __name__ == "__main__":
    sys.exit(main())
