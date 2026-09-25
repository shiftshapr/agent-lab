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
    Tombstone keys legacy-N-X document history; X may be reclaimed on the active ledger.
    Forbid citing N-X only when X is not on the active register (unmapped ghost ids).
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
    """N-* cited on Claim/Artifact Related Nodes lines (Lane-class airtime proxy)."""
    cited: set[int] = set()
    for _ep, _name, _path, content in episodes:
        # Claim register and artifact inline *Related:* (not register section)
        for m in RELATED_NODES_LINE_RE.finditer(content):
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
        if nt in PERSON_TYPES and nid >= 1000:
            report.add(
                "P0",
                "person_band",
                f"{ent.episode_file}: Person N-{nid} ({ent.name}) must be N-1..N-999",
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

    topic_present = {n for n in intro if n >= 1000} | baseline_topic
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
        return "person" if nid < 1000 else "topic"

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
