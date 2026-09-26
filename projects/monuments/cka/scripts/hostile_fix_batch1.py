#!/usr/bin/env python3
"""
CKA Batch 1 — Bill D hostile hard-gates fix pass (drafts, transcripts, inscription, canonical).

Usage (from agent-lab root):
  python3 projects/monuments/cka/scripts/hostile_fix_batch1.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
CKA = Path(__file__).resolve().parents[1]
BOC = REPO / "projects" / "monuments" / "bride_of_charlie"
DRAFTS = CKA / "drafts"
CORR = CKA / "transcripts_corrected"
INS = CKA / "inscription"

NODE_HEADER = re.compile(r"^\*\*N-(\d+)\*\*\s", re.MULTILINE)
NEW_NODES = re.compile(r"^(\s*- New Nodes Introduced:\s*)(.+)$", re.MULTILINE)
REUSED_NODES = re.compile(r"^(\s*- Reused Nodes Appearing:\s*)(.+)$", re.MULTILINE)
YT_ID = re.compile(r"- \*\*YouTube id\*\*:\s*(\S+)", re.I)
VIDEO_RANGE = re.compile(r"^(- \*\*Video Timestamp Range\*\*:\s*)(.+)$", re.MULTILINE)
SOURCE_LINE = re.compile(r"^(- \*\*Source\*\*:\s*)(.+)$", re.MULTILINE)
ERIKA_LONG = "Erika Kirk (née Frantzey)"

AD_TRIGGER = re.compile(
    r"(?i)(american\s*financ|americanfinanc|promo\s*code|use\s+code\b)"
)
AD_CONTINUATION = re.compile(
    r"(?i)(pure\s*talk|puretalk|thrivehealth|fieldof\s*green|hometitle|"
    r"paleobal|nimi\s*skincare|tpusa\.com|800\d{7}|\.com/owens|net/owens|"
    r"call\s+(american|now)|start\s+saving|mortgage\s+rate|home\s*equity|"
    r"wireless\s+company|faithneimi|donation|matching\s+every)"
)
AD_START = re.compile(
    r"(?i)(before i get into.{0,60}comments|also.{0,40}(remind|tell you)|"
    r"head to puretalk|switch to my wireless|american\s*financ)"
)


def _sec_to_hms(sec: int) -> str:
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _load_yt_durations() -> dict[str, int]:
    path = CKA / "config" / "yt_durations.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): int(v) for k, v in doc["by_youtube_id"].items()}


def _parse_ledger_ids(body: str) -> list[str]:
    return [p.strip() for p in body.split(",") if p.strip()]


def _format_ledger_ids(ids: list[str]) -> str:
    def key(n: str) -> int:
        m = re.match(r"N-(\d+)", n)
        return int(m.group(1)) if m else 0

    persons = sorted([x for x in ids if key(x) < 1000], key=key)
    topics = sorted([x for x in ids if key(x) >= 1000], key=key)
    return ", ".join(persons + topics)


def _register_ids(text: str) -> list[str]:
    return [f"N-{m.group(1)}" for m in NODE_HEADER.finditer(text)]


def fix_ledger(draft_paths: list[Path]) -> int:
    first_ep: dict[str, int] = {}
    for path in draft_paths:
        m = re.search(r"episode_(\d+)", path.name)
        if not m:
            continue
        ep = int(m.group(1))
        for nid in _register_ids(path.read_text(encoding="utf-8")):
            first_ep.setdefault(nid, ep)

    n = 0
    for path in draft_paths:
        m = re.search(r"episode_(\d+)", path.name)
        if not m:
            continue
        ep = int(m.group(1))
        if ep == 0:
            continue
        text = path.read_text(encoding="utf-8")
        reg = _register_ids(text)
        if not reg:
            continue
        new_ids = [nid for nid in reg if first_ep.get(nid) == ep]
        reused = [nid for nid in reg if first_ep.get(nid, ep) < ep]
        new_line = f"  - New Nodes Introduced: {_format_ledger_ids(new_ids)}"
        reused_line = f"  - Reused Nodes Appearing: {_format_ledger_ids(reused)}"

        if NEW_NODES.search(text):
            text = NEW_NODES.sub(lambda m: new_line, text, count=1)
        else:
            text = text.replace(
                "- **Episode Ledger Summary**:",
                "- **Episode Ledger Summary**:\n" + new_line,
                1,
            )
        if REUSED_NODES.search(text):
            text = REUSED_NODES.sub(lambda m: reused_line, text, count=1)
        else:
            text = NEW_NODES.sub(
                lambda m: m.group(0) + "\n" + reused_line,
                text,
                count=1,
            )
        path.write_text(text, encoding="utf-8")
        n += 1
    return n


def fix_meta_and_names(draft_paths: list[Path], yt: dict[str, int]) -> int:
    n = 0
    for path in draft_paths:
        text = path.read_text(encoding="utf-8")
        orig = text
        text = text.replace(ERIKA_LONG, "Erika Kirk")
        m = YT_ID.search(text)
        if m:
            dur = yt.get(m.group(1))
            if dur is not None:
                end = _sec_to_hms(dur)
                text = VIDEO_RANGE.sub(
                    lambda m2: f"{m2.group(1)}00:00:00–{end}",
                    text,
                    count=1,
                )
        if "Source**: Unknown" in text or re.search(r"Source\*\*:\s*Unknown", text):
            text = SOURCE_LINE.sub(
                lambda m2: f"{m2.group(1)}Candace Owens YouTube",
                text,
                count=1,
            )
        # Normalize timestamp range separators in stamps (ep1 ASCII debt)
        text = re.sub(
            r"(?m)^((?:Claim Timestamp|Video Timestamp|Event Timestamp):\s*\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})\s*$",
            r"\1–\2",
            text,
        )
        if text != orig:
            path.write_text(text, encoding="utf-8")
            n += 1
    return n


def _strip_ads_text(text: str) -> tuple[str, int]:
    lines = text.splitlines()
    out: list[str] = []
    in_ad = False
    removed = 0
    for line in lines:
        if AD_TRIGGER.search(line) or AD_START.search(line):
            in_ad = True
        if in_ad:
            removed += 1
            if AD_CONTINUATION.search(line) or AD_TRIGGER.search(line) or AD_START.search(line):
                continue
            if re.search(r"(?i)(800\d{7}|\.com/|\.net/|promo\s*code|use\s+code\b)", line):
                continue
            in_ad = False
        if in_ad:
            continue
        if AD_TRIGGER.search(line):
            removed += 1
            continue
        out.append(line)
    collapsed: list[str] = []
    blank = False
    for line in out:
        if not line.strip():
            if not blank:
                collapsed.append("")
            blank = True
        else:
            collapsed.append(line)
            blank = False
    return "\n".join(collapsed).rstrip() + "\n", removed


def fix_transcripts() -> int:
    total = 0
    for path in sorted(CORR.glob("episode_*.txt")):
        raw = path.read_text(encoding="utf-8")
        updated, n = _strip_ads_text(raw)
        if updated != raw:
            path.write_text(updated, encoding="utf-8")
            total += n
        ins_name = path.name.replace("episode_", "episode_").replace(".txt", "_transcript.txt")
        ins_path = INS / ins_name
        if not ins_path.is_file():
            # episode_001_foo.txt -> episode_001_transcript.txt
            m = re.match(r"episode_(\d{3})_", path.name)
            if m:
                ins_path = INS / f"episode_{m.group(1)}_transcript.txt"
        if ins_path.is_file():
            ins_raw = ins_path.read_text(encoding="utf-8")
            ins_upd, n2 = _strip_ads_text(ins_raw)
            if ins_upd != ins_raw:
                ins_path.write_text(ins_upd, encoding="utf-8")
                total += n2
    return total


def patch_orphan_wiring() -> None:
    patches: list[tuple[Path, list[tuple[str, str]]]] = [
        (
            DRAFTS / "episode_001.md",
            [
                (
                    "Related Nodes: N-1, N-7, N-56, N-1069, N-60, N-61, N-62, N-63, N-42, N-64",
                    "Related Nodes: N-1, N-7, N-56, N-1069, N-60, N-61, N-62, N-63, N-42, N-64, N-1073",
                ),
                (
                    "*Related: C-1121, N-1, N-7, N-56*",
                    "*Related: C-1121, N-1, N-7, N-56, N-1073*",
                ),
                (
                    "**N-1073** YWLS Conference\n\nNode Type: Organization\nOrganization Kind: conference\nConference concurrent with the 'him too' / #MeToo press incident; reporters swooped in on Candace's statements.\n\n*Related: C-1118*",
                    "**N-1073** YWLS Conference\n\nNode Type: Organization\nOrganization Kind: conference\nConference concurrent with the 'him too' / #MeToo press incident; reporters swooped in on Candace's statements.\n\n*Related: C-1115, C-1121*",
                ),
            ],
        ),
        (
            DRAFTS / "episode_009.md",
            [
                (
                    "Related Nodes: N-1137, N-1175",
                    "Related Nodes: N-1137, N-1175, N-1191",
                ),
                (
                    "Related Nodes: N-7, N-100, N-1184",
                    "Related Nodes: N-7, N-100, N-1184, N-1192",
                ),
                (
                    "Related Nodes: N-7, N-1179",
                    "Related Nodes: N-7, N-1179, N-1194, N-1181",
                ),
                (
                    "Related Nodes: N-148, N-1177, N-1186",
                    "Related Nodes: N-148, N-1177, N-1186, N-1003, N-1182",
                ),
                (
                    "**N-1003** MK Ultra\n\nNode Type: Organization\nOrganization Kind: program_or_initiative\nCIA program (1950s-60s); host asserts it was never discontinued.\n\n*Related: *",
                    "**N-1003** MK Ultra\n\nNode Type: Organization\nOrganization Kind: program_or_initiative\nCIA program (1950s-60s); host asserts it was never discontinued.\n\n*Related: C-1270, C-1273*",
                ),
            ],
        ),
    ]
    for path, reps in patches:
        text = path.read_text(encoding="utf-8")
        for old, new in reps:
            if old in text:
                text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")


def _build_canonical_from_drafts() -> None:
    sys.path.insert(0, str(REPO / "projects" / "monuments" / "scripts"))
    from dia_preflight import (  # type: ignore
        collect_register_entries,
        first_introduction_meta,
        load_draft_episodes,
    )

    remap = json.loads((CKA / "config" / "batch1_remap_from_boc.json").read_text(encoding="utf-8"))
    boc_to_cka = {int(r["boc_monument_ep"]): int(r["cka_seq"]) for r in remap["rows"]}

    episodes = load_draft_episodes(DRAFTS)
    intro = first_introduction_meta(collect_register_entries(episodes))
    active = set(intro.keys())

    boc_canonical = json.loads((BOC / "canonical" / "nodes.json").read_text(encoding="utf-8"))
    out_nodes: dict[str, dict] = {}
    for key, meta in boc_canonical.get("nodes", {}).items():
        m = re.match(r"N-(\d+)$", key)
        if not m or int(m.group(1)) not in active:
            continue
        eps = meta.get("episodes") or []
        cka_eps = sorted({boc_to_cka[e] for e in eps if e in boc_to_cka})
        if not cka_eps and int(m.group(1)) in active:
            ent = intro.get(int(m.group(1)))
            cka_eps = [ent.episode] if ent else [1]
        out_nodes[key] = {**meta, "episodes": cka_eps}

    for nid, ent in intro.items():
        key = f"N-{nid}"
        if key not in out_nodes:
            continue
        out_nodes[key]["canonical_name"] = ent.name

    out = {
        "version": 1,
        "updated": boc_canonical.get("updated"),
        "monument": "cka",
        "remap_note": "Batch 1 from BoC monument eps 9–18; node ids unchanged.",
        "next_person_id": boc_canonical.get("next_person_id"),
        "next_investigation_id": boc_canonical.get("next_investigation_id"),
        "nodes": out_nodes,
    }
    canon_dir = CKA / "canonical"
    canon_dir.mkdir(parents=True, exist_ok=True)
    (canon_dir / "nodes.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


def _patch_inscription_meta() -> None:
    manifest = {
        int(row["seq"]): row
        for row in json.loads((CKA / "input" / "episode_manifest.json").read_text(encoding="utf-8"))[
            "episodes"
        ]
        if row.get("seq") is not None
    }
    for path in sorted(INS.glob("episode_*.json")):
        if path.name.startswith("episode_000"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        meta = data.setdefault("meta", {})
        meta["series"] = "Candace Kirk Archive"
        meta["monument"] = "cka"
        ep = meta.get("episode")
        if ep and ep in manifest:
            row = manifest[ep]
            meta["youtube_id"] = row["youtube_id"]
            meta["candace_ep_number"] = row.get("candace_ep_number")
            meta["kind"] = row.get("kind")
            meta["source"] = "Candace Owens YouTube"
            dur_path = CKA / "config" / "yt_durations.json"
            if dur_path.is_file():
                durs = json.loads(dur_path.read_text())["by_youtube_id"]
                sec = durs.get(row["youtube_id"])
                if sec:
                    meta["video_timestamp_range"] = f"00:00:00–{_sec_to_hms(sec)}"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rebuild_inscription_and_canonical() -> None:
    build = BOC / "scripts" / "build_inscription_from_drafts.py"
    build_cmd = [
        sys.executable,
        str(build),
        "--drafts",
        str(DRAFTS),
        "--inscription",
        str(INS),
    ]
    for ep in range(1, 11):
        build_cmd.extend(["--episode", str(ep)])
    subprocess.run(build_cmd, check=True, cwd=str(REPO))
    _patch_inscription_meta()
    _build_canonical_from_drafts()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.apply:
        print("Dry-run: pass --apply to mutate CKA monument files.")
        return 0

    draft_paths = sorted(DRAFTS.glob("episode_*.md"))
    yt = _load_yt_durations()
    print("ledger episodes:", fix_ledger(draft_paths))
    print("meta/name episodes:", fix_meta_and_names(draft_paths, yt))
    patch_orphan_wiring()
    print("ad lines stripped (approx):", fix_transcripts())
    rebuild_inscription_and_canonical()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
