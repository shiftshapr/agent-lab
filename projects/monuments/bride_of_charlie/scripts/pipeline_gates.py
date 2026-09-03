#!/usr/bin/env python3
"""
Bride of Charlie pipeline gates: name-freeze, draft transcript SHA freshness, verify grounding.

Usage (from agent-lab root or project dir):
  python projects/monuments/bride_of_charlie/scripts/pipeline_gates.py name-freeze [--episode N]
  python projects/monuments/bride_of_charlie/scripts/pipeline_gates.py invalidate-stale [--episode N]
  python projects/monuments/bride_of_charlie/scripts/pipeline_gates.py check-freshness [--episode N]

Imported by run_workflow.py, protocol_agent.py, episode_analysis_protocol.py, verify_drafts.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent.parent
LEXICON_PATH = PROJECT_DIR / "config" / "asr_leftover_lexicon.json"
STALE_DIR = PROJECT_DIR / "drafts" / ".stale"
SHA_STAMP_DIR = PROJECT_DIR / "drafts" / ".transcript_sha"

_DRAFT_SHA_RE = re.compile(
    r"^\-\s*\*\*Transcript SHA-256\*\*:\s*([0-9a-f]{64})\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_TIMESTAMP_LINE_RE = re.compile(r"^\[(\d{1,2}):(\d{2})\]", re.MULTILINE)
_HMS_RE = re.compile(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})")
_ARTIFACT_ITEM_PATTERN = re.compile(r"^\*\*A-(\d+)\.(\d+)\*\*\s+(.+)$", re.MULTILINE)
_CLAIM_PATTERN = re.compile(r"^\*\*C-(\d+)\*\*\s+(.+)$", re.MULTILINE)
_TRANSCRIPT_SNIPPET_PATTERN = re.compile(r"^Transcript Snippet:\s*(.+)$", re.MULTILINE)
_ANCHORED_ARTIFACTS_PATTERN = re.compile(
    r"^Anchored Artifacts:[ \t]*([^\n]*?)\s*$", re.MULTILINE
)
_RELATED_NODES_PATTERN = re.compile(r"^Related Nodes:[ \t]*([^\n]*?)\s*$", re.MULTILINE)
_CLAIM_TS_PATTERN = re.compile(r"^Claim Timestamp:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_ID_TOKEN = re.compile(r"^[A-Z]+-\d+(?:\.\d+)?$")


def _parse_id_list(raw: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[,;]", raw):
        id = part.strip()
        if id.lower().startswith("same_as:"):
            id = id.split(":", 1)[1].strip()
        if id and _ID_TOKEN.match(id):
            out.append(id)
    return out


def _extract_artifacts_for_audit(text: str, episode_num: int) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for match in _ARTIFACT_ITEM_PATTERN.finditer(text):
        artifact_id = f"A-{match.group(1)}.{match.group(2)}"
        start_pos = match.end()
        next_match = _ARTIFACT_ITEM_PATTERN.search(text, start_pos)
        next_claim = _CLAIM_PATTERN.search(text, start_pos)
        end_pos = len(text)
        for m in [next_match, next_claim]:
            if m and m.start() < end_pos:
                end_pos = m.start()
        section = text[start_pos:end_pos]
        snip_m = _TRANSCRIPT_SNIPPET_PATTERN.search(section)
        artifacts.append(
            {
                "id": artifact_id,
                "episode_num": episode_num,
                "transcript_snippet": snip_m.group(1).strip() if snip_m else None,
            }
        )
    return artifacts


def _extract_claims_for_audit(text: str, episode_num: int) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for match in _CLAIM_PATTERN.finditer(text):
        claim_id = f"C-{match.group(1)}"
        start_pos = match.end()
        next_match = _CLAIM_PATTERN.search(text, start_pos)
        end_pos = next_match.start() if next_match else len(text)
        section = text[start_pos:end_pos]
        anchor_m = _ANCHORED_ARTIFACTS_PATTERN.search(section)
        nodes_m = _RELATED_NODES_PATTERN.search(section)
        snip_m = _TRANSCRIPT_SNIPPET_PATTERN.search(section)
        ts_m = _CLAIM_TS_PATTERN.search(section)
        claims.append(
            {
                "id": claim_id,
                "episode_num": episode_num,
                "anchored_artifacts": _parse_id_list(anchor_m.group(1)) if anchor_m else [],
                "related_nodes": _parse_id_list(nodes_m.group(1)) if nodes_m else [],
                "transcript_snippet": snip_m.group(1).strip() if snip_m else None,
                "claim_timestamp": ts_m.group(1).strip() if ts_m else None,
            }
        )
    return claims


@dataclass
class LeftoverHit:
    pattern_id: str
    match: str
    note: str
    line_no: int | None = None


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_text(path.read_text(encoding="utf-8"))


def load_leftover_lexicon(path: Path | None = None) -> list[dict[str, Any]]:
    p = path or LEXICON_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("patterns") or [])


def _compile_pattern(entry: dict[str, Any]) -> re.Pattern[str]:
    flags = 0
    for f in entry.get("flags") or []:
        if f.upper() == "IGNORECASE":
            flags |= re.IGNORECASE
        elif f.upper() == "MULTILINE":
            flags |= re.MULTILINE
    return re.compile(str(entry["regex"]), flags)


def scan_text_for_leftovers(
    text: str,
    lexicon: list[dict[str, Any]] | None = None,
) -> list[LeftoverHit]:
    """Return lexicon hits in text (deduped by pattern_id + matched span)."""
    lex = lexicon if lexicon is not None else load_leftover_lexicon()
    hits: list[LeftoverHit] = []
    seen: set[tuple[str, str]] = set()
    lines = text.splitlines()
    for entry in lex:
        rx = _compile_pattern(entry)
        for m in rx.finditer(text):
            key = (str(entry.get("id") or ""), m.group(0))
            if key in seen:
                continue
            seen.add(key)
            line_no = text[: m.start()].count("\n") + 1
            hits.append(
                LeftoverHit(
                    pattern_id=str(entry.get("id") or "?"),
                    match=m.group(0),
                    note=str(entry.get("note") or ""),
                    line_no=line_no,
                )
            )
    return hits


def resolve_corrected_transcript(project_dir: Path, episode_num: int) -> Path | None:
    corr = sorted((project_dir / "transcripts_corrected").glob(f"episode_{episode_num:03d}_*.txt"))
    if corr:
        return corr[0]
    return None


def assert_name_freeze_for_transcript(path: Path, lexicon: list[dict[str, Any]] | None = None) -> list[str]:
    """Return error strings; empty list means pass."""
    if not path.is_file():
        return [f"transcript not found: {path}"]
    text = path.read_text(encoding="utf-8")
    hits = scan_text_for_leftovers(text, lexicon)
    if not hits:
        return []
    errs: list[str] = []
    for h in hits:
        loc = f"line {h.line_no}" if h.line_no else "?"
        errs.append(f"{path.name} {loc}: leftover ASR {h.pattern_id!r} → {h.match!r} ({h.note})")
    return errs


def assert_name_freeze_for_episode(project_dir: Path, episode_num: int) -> list[str]:
    tpath = resolve_corrected_transcript(project_dir, episode_num)
    if not tpath:
        return [f"episode {episode_num}: no transcripts_corrected file"]
    return assert_name_freeze_for_transcript(tpath)


def assert_name_freeze_all(project_dir: Path, episodes: list[int] | None = None) -> list[str]:
    corr_dir = project_dir / "transcripts_corrected"
    if not corr_dir.is_dir():
        return [f"transcripts_corrected/ missing under {project_dir}"]
    eps = episodes
    if eps is None:
        eps = sorted(
            {
                int(m.group(1))
                for p in corr_dir.glob("episode_*.txt")
                if (m := re.search(r"episode_(\d+)", p.name, re.I))
            }
        )
    out: list[str] = []
    for ep in eps:
        out.extend(assert_name_freeze_for_episode(project_dir, ep))
    return out


def parse_draft_transcript_sha(content: str) -> str | None:
    m = _DRAFT_SHA_RE.search(content)
    return m.group(1).lower() if m else None


def read_phase1_transcript_sha(phase1_path: Path) -> str | None:
    if not phase1_path.is_file():
        return None
    try:
        data = json.loads(phase1_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    sha = (data.get("meta") or {}).get("transcript_sha256")
    return str(sha).lower() if sha else None


def sha_stamp_path(episode_num: int) -> Path:
    return SHA_STAMP_DIR / f"episode_{episode_num:03d}.sha256"


def write_transcript_sha_stamp(episode_num: int, digest: str) -> None:
    SHA_STAMP_DIR.mkdir(parents=True, exist_ok=True)
    sha_stamp_path(episode_num).write_text(digest.lower() + "\n", encoding="utf-8")


def read_transcript_sha_stamp(episode_num: int) -> str | None:
    p = sha_stamp_path(episode_num)
    if not p.is_file():
        return None
    line = p.read_text(encoding="utf-8").strip().lower()
    return line if re.fullmatch(r"[0-9a-f]{64}", line) else None


def recorded_draft_sha(
    draft_path: Path | None,
    phase1_path: Path | None,
    episode_num: int,
) -> str | None:
    if draft_path and draft_path.is_file():
        sha = parse_draft_transcript_sha(draft_path.read_text(encoding="utf-8"))
        if sha:
            return sha
    if phase1_path and phase1_path.is_file():
        sha = read_phase1_transcript_sha(phase1_path)
        if sha:
            return sha
    return read_transcript_sha_stamp(episode_num)


def check_draft_freshness(
    project_dir: Path,
    episode_num: int,
    *,
    draft_path: Path | None = None,
    phase1_path: Path | None = None,
    transcript_path: Path | None = None,
) -> tuple[bool, str | None]:
    """
    Return (is_fresh, error_message).
    Fresh means recorded SHA matches corrected transcript bytes.
    Missing recorded SHA + corrected newer than draft → stale.
    """
    tpath = transcript_path or resolve_corrected_transcript(project_dir, episode_num)
    if not tpath or not tpath.is_file():
        return True, None

    current = sha256_file(tpath)
    drafts_dir = project_dir / "drafts"
    if draft_path is None:
        cands = sorted(drafts_dir.glob(f"episode_{episode_num:03d}_*.md"))
        draft_path = cands[0] if cands else None
    phase1_dir = project_dir / "phase1_output"
    if phase1_path is None and phase1_dir.is_dir():
        p1c = sorted(phase1_dir.glob(f"episode_{episode_num:03d}_*.json"))
        phase1_path = p1c[0] if p1c else None

    has_draft = draft_path and draft_path.is_file()
    has_phase1 = phase1_path and phase1_path.is_file()
    if not has_draft and not has_phase1:
        return True, None

    recorded = recorded_draft_sha(
        draft_path if has_draft else None,
        phase1_path if has_phase1 else None,
        episode_num,
    )
    if recorded:
        if recorded == current:
            return True, None
        return (
            False,
            f"episode {episode_num}: draft SHA {recorded[:16]}… != corrected {current[:16]}… "
            f"(re-extract with --force)",
        )

    # No hash on draft — compare mtimes
    draft_mtime = 0.0
    if has_draft:
        draft_mtime = max(draft_mtime, draft_path.stat().st_mtime)
    if has_phase1:
        draft_mtime = max(draft_mtime, phase1_path.stat().st_mtime)
    corr_mtime = tpath.stat().st_mtime
    if corr_mtime > draft_mtime + 1.0:
        return (
            False,
            f"episode {episode_num}: draft lacks Transcript SHA-256 and corrected transcript "
            f"is newer than draft (re-extract with --force)",
        )
    return True, None


def _stale_marker_path(episode_num: int) -> Path:
    return STALE_DIR / f"episode_{episode_num:03d}.json"


def mark_draft_stale(episode_num: int, reason: str) -> None:
    STALE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"episode": episode_num, "reason": reason}
    _stale_marker_path(episode_num).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def clear_stale_marker(episode_num: int) -> None:
    p = _stale_marker_path(episode_num)
    if p.is_file():
        p.unlink()


def is_marked_stale(episode_num: int) -> bool:
    return _stale_marker_path(episode_num).is_file()


def invalidate_stale_drafts(
    project_dir: Path,
    episodes: list[int] | None = None,
    *,
    remove_files: bool = True,
) -> list[str]:
    """Detect SHA drift; optionally remove draft + phase1. Returns list of actions taken."""
    drafts_dir = project_dir / "drafts"
    phase1_dir = project_dir / "phase1_output"
    if episodes is None:
        found: set[int] = set()
        if drafts_dir.is_dir():
            for p in drafts_dir.glob("episode_*.md"):
                if m := re.search(r"episode_(\d+)", p.name, re.I):
                    found.add(int(m.group(1)))
        if phase1_dir.is_dir():
            for p in phase1_dir.glob("episode_*.json"):
                if m := re.search(r"episode_(\d+)", p.name, re.I):
                    found.add(int(m.group(1)))
        episodes = sorted(found)

    actions: list[str] = []
    for ep in episodes:
        fresh, err = check_draft_freshness(project_dir, ep)
        if fresh or not err:
            clear_stale_marker(ep)
            continue
        mark_draft_stale(ep, err)
        actions.append(err)
        if not remove_files:
            continue
        for p in sorted(drafts_dir.glob(f"episode_{ep:03d}_*.md")):
            p.unlink()
            actions.append(f"removed stale draft {p.name}")
        if phase1_dir.is_dir():
            for p in sorted(phase1_dir.glob(f"episode_{ep:03d}_*.json")):
                p.unlink()
                actions.append(f"removed stale phase1 {p.name}")
    return actions


def _normalize_for_match(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def snippet_in_transcript(snippet: str, transcript: str) -> bool:
    if not snippet or not snippet.strip():
        return False
    norm_snip = _normalize_for_match(snippet)
    norm_tx = _normalize_for_match(transcript)
    if norm_snip in norm_tx:
        return True
    # Allow ellipsis gaps: "foo... bar" matches if both parts appear in order
    parts = [p.strip() for p in re.split(r"\.\.\.|…", snippet) if p.strip()]
    if len(parts) > 1:
        pos = 0
        for part in parts:
            np = _normalize_for_match(part)
            if not np:
                continue
            idx = norm_tx.find(np, pos)
            if idx < 0:
                return False
            pos = idx + len(np)
        return True
    return False


def _parse_hms_to_seconds(raw: str) -> int | None:
    raw = raw.strip()
    m = _HMS_RE.search(raw)
    if not m:
        return None
    h, mi, s = m.group(1), m.group(2), m.group(3)
    hours = int(h) if h else 0
    return hours * 3600 + int(mi) * 60 + int(s)


def _transcript_window_text(transcript: str, center_seconds: int | None, radius: int = 120) -> str:
    if center_seconds is None:
        return transcript
    chunks: list[str] = []
    for line in transcript.splitlines():
        m = _TIMESTAMP_LINE_RE.match(line)
        if not m:
            continue
        sec = int(m.group(1)) * 60 + int(m.group(2))
        if abs(sec - center_seconds) <= radius:
            chunks.append(line)
    return "\n".join(chunks) if chunks else transcript


def _person_name_tokens(name: str) -> list[str]:
    """Last name or distinctive token for grounding checks."""
    name = re.sub(r"\([^)]*\)", "", name).strip()
    name = re.sub(r"\*Also known as:.*", "", name, flags=re.IGNORECASE).strip()
    parts = [p for p in re.split(r"\s+", name) if p and p.lower() not in ("dr", "dr.", "colonel", "col")]
    if not parts:
        return []
    if len(parts) >= 2:
        return [parts[-1].lower()]
    return [parts[0].lower()]


def _load_node_names(content: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in re.finditer(r"^\*\*N-(\d+)\*\*\s+(.+)$", content, re.MULTILINE):
        nid = f"N-{int(m.group(1))}"
        if int(m.group(1)) >= 1000:
            continue
        out[nid] = m.group(2).strip()
    return out


def audit_draft_grounding(
    ep_name: str,
    content: str,
    transcript: str,
) -> list[str]:
    """
    Hard-fail checks for verify_drafts:
    - claims must have Anchored Artifacts
    - snippets must be non-empty and found in transcript (stamp)
    - related person names must appear in snippet or timestamp window
    """
    ep_m = re.search(r"episode_(\d+)", ep_name, re.I) or re.search(r"episode_(\d+)", content, re.I)
    ep_num = int(ep_m.group(1)) if ep_m else 0
    node_names = _load_node_names(content)
    artifacts = _extract_artifacts_for_audit(content, ep_num)
    claims = _extract_claims_for_audit(content, ep_num)
    errs: list[str] = []

    for art in artifacts:
        snip = (art.get("transcript_snippet") or "").strip()
        if not snip:
            errs.append(f"{ep_name} {art['id']}: empty Transcript Snippet")
            continue
        if not snippet_in_transcript(snip, transcript):
            errs.append(f"{ep_name} {art['id']}: stamp not found in transcript ({snip[:60]!r}…)")

    for claim in claims:
        cid = claim["id"]
        anchored = claim.get("anchored_artifacts") or []
        if not anchored:
            errs.append(f"{ep_name} {cid}: missing Anchored Artifacts")
        snip = (claim.get("transcript_snippet") or "").strip()
        if not snip:
            errs.append(f"{ep_name} {cid}: empty Transcript Snippet")
        elif not snippet_in_transcript(snip, transcript):
            errs.append(f"{ep_name} {cid}: stamp not found in transcript ({snip[:60]!r}…)")

        center = _parse_hms_to_seconds(claim.get("claim_timestamp") or "")
        window = _transcript_window_text(transcript, center)
        search_text = f"{snip}\n{window}"

        related_nodes = claim.get("related_nodes") or []
        person_tokens: list[str] = []
        for nid in related_nodes:
            nm = node_names.get(nid)
            if nm:
                person_tokens.extend(_person_name_tokens(nm))
        if person_tokens:
            norm_search = _normalize_for_match(search_text)
            missing = [t for t in person_tokens if t not in norm_search]
            if missing and snip:
                # Also try full transcript if window was empty/narrow
                norm_full = _normalize_for_match(transcript)
                missing = [t for t in person_tokens if t not in norm_search and t not in norm_full]
            if missing:
                names = ", ".join(sorted(set(missing)))
                errs.append(
                    f"{ep_name} {cid}: claim person name token(s) not in grounded window: {names}"
                )

    return errs


def audit_all_drafts(project_dir: Path, drafts_dir: Path | None = None) -> list[str]:
    ddir = drafts_dir or (project_dir / "drafts")
    errs: list[str] = []
    for p in sorted(ddir.glob("episode_*.md")):
        if "cross_episode" in p.name:
            continue
        m = re.search(r"episode_(\d+)", p.name, re.I)
        if not m:
            continue
        ep = int(m.group(1))
        tpath = resolve_corrected_transcript(project_dir, ep)
        if not tpath:
            errs.append(f"{p.name}: no transcripts_corrected for grounding audit")
            continue
        content = p.read_text(encoding="utf-8")
        fresh, stale_err = check_draft_freshness(project_dir, ep, draft_path=p)
        if not fresh and stale_err:
            errs.append(f"{p.name}: STALE — {stale_err}")
            continue
        if is_marked_stale(ep):
            errs.append(f"{p.name}: marked stale (corrected transcript drift)")
            continue
        transcript = tpath.read_text(encoding="utf-8")
        errs.extend(audit_draft_grounding(p.name, content, transcript))
    return errs


def _parse_episode_list(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return sorted(set(out)) if out else None


def main() -> int:
    ap = argparse.ArgumentParser(description="BoC pipeline gates")
    sub = ap.add_subparsers(dest="cmd", required=True)

    nf = sub.add_parser("name-freeze", help="Refuse if leftover ASR lexicon hits remain")
    nf.add_argument("--episode", type=str, default=None, help="Episode number or comma list")

    inv = sub.add_parser("invalidate-stale", help="Remove drafts whose transcript SHA drifted")
    inv.add_argument("--episode", type=str, default=None)
    inv.add_argument("--mark-only", action="store_true", help="Do not delete draft files")

    cf = sub.add_parser("check-freshness", help="Report stale drafts (non-zero if any)")
    cf.add_argument("--episode", type=str, default=None)

    args = ap.parse_args()
    episodes = _parse_episode_list(getattr(args, "episode", None))

    if args.cmd == "name-freeze":
        errs = assert_name_freeze_all(PROJECT_DIR, episodes)
        if errs:
            print("[name-freeze] REFUSED — leftover ASR forms in transcripts_corrected:", file=sys.stderr)
            for e in errs:
                print(f"  {e}", file=sys.stderr)
            return 1
        print("[name-freeze] OK — no leftover lexicon hits")
        return 0

    if args.cmd == "invalidate-stale":
        actions = invalidate_stale_drafts(
            PROJECT_DIR,
            episodes,
            remove_files=not args.mark_only,
        )
        if actions:
            print("[invalidate-stale] actions:")
            for a in actions:
                print(f"  {a}")
        else:
            print("[invalidate-stale] no stale drafts")
        return 0

    if args.cmd == "check-freshness":
        eps = episodes
        if eps is None:
            eps = sorted(
                {
                    int(m.group(1))
                    for p in (PROJECT_DIR / "drafts").glob("episode_*.md")
                    if (m := re.search(r"episode_(\d+)", p.name, re.I))
                }
            )
        stale: list[str] = []
        for ep in eps:
            fresh, err = check_draft_freshness(PROJECT_DIR, ep)
            if not fresh and err:
                stale.append(err)
        if stale:
            print("[check-freshness] STALE:", file=sys.stderr)
            for s in stale:
                print(f"  {s}", file=sys.stderr)
            return 1
        print("[check-freshness] OK")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
