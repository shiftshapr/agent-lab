#!/usr/bin/env python3
"""
Remap BoC monument episodes 9–18 → CKA seq 1–10 (Batch 1). Copy transcripts/artifacts; no re-extract.

Run from agent-lab root:
  python3 projects/monuments/cka/scripts/remap_boc_batch1.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BOC = REPO / "projects" / "monuments" / "bride_of_charlie"
CKA = REPO / "projects" / "monuments" / "cka"

# BoC monument ep → (CKA seq, youtube_id) — locked to episode_manifest.json
REMAP_ROWS: list[tuple[int, int, str]] = [
    (9, 1, "_dRaEO47-co"),
    (10, 2, "czVBmqZP6Ss"),
    (11, 3, "q7f8r-THr84"),
    (12, 4, "2WEHTk0Xewg"),
    (13, 5, "sreYYcID-QY"),
    (14, 6, "aDlhjfW6hz8"),
    (15, 7, "ja26iltROkM"),
    (16, 8, "UBkFkg4UNY8"),
    (17, 9, "QZWSsq8ZWzw"),
    (18, 10, "K5GjF53bfN4"),
]

NODE_HEADER_RE = re.compile(r"^\*\*N-(\d+)\*\*", re.MULTILINE)
MEME_HEADER_RE = re.compile(r"^\*\*M-(\d+)\*\*", re.MULTILINE)
CLAIM_LENS_KEYWORDS: dict[str, re.Pattern[str]] = {
    "calls_for_tips": re.compile(r"\btip\b|\btips\b|tip-line|tipped\b", re.I),
    "submissions_to_candace": re.compile(
        r"received a tip|via comment|listener who tipped|viewer tip|contact with the source",
        re.I,
    ),
    "open_source_investigation": re.compile(
        r"\bOSINT\b|open.?source|public records|metadata|frame-by-frame|cross-reference",
        re.I,
    ),
    "decentralized_investigation": re.compile(
        r"decentral|crowdsourc|audience.*investig|DIA-style|collaborative inquiry",
        re.I,
    ),
}


def _read(ep_path: Path) -> str:
    return ep_path.read_text(encoding="utf-8")


def _register_nids(text: str) -> set[int]:
    reg = text.split("## 4. Node Register", 1)[-1]
    if "## 5." in reg:
        reg = reg.split("## 5.", 1)[0]
    return {int(m.group(1)) for m in NODE_HEADER_RE.finditer(reg)}


def _meme_ids(text: str) -> set[int]:
    m = re.search(r"^## 6\. Meme Register\s*$", text, re.MULTILINE)
    if not m:
        return set()
    section = text[m.end() :]
    nxt = re.search(r"^## \d+\.", section, re.MULTILINE)
    if nxt:
        section = section[: nxt.start()]
    return {int(m.group(1)) for m in MEME_HEADER_RE.finditer(section)}


def _extract_node_block(text: str, nid: int) -> str | None:
    reg = text.split("## 4. Node Register", 1)[-1]
    if "## 5." in reg:
        reg = reg.split("## 5.", 1)[0]
    pat = re.compile(rf"^\*\*N-{nid}\*\*.*?(?=^\*\*N-\d+\*\*|\Z)", re.MULTILINE | re.DOTALL)
    m = pat.search(reg)
    return m.group(0).rstrip() + "\n\n" if m else None


def _extract_meme_block(text: str, mid: int) -> str | None:
    msec = re.search(r"^## 6\. Meme Register\s*$", text, re.MULTILINE)
    if not msec:
        return None
    section = text[msec.end() :]
    nxt = re.search(r"^## \d+\.", section, re.MULTILINE)
    if nxt:
        section = section[: nxt.start()]
    pat = re.compile(rf"^\*\*M-{mid}\*\*.*?(?=^\*\*M-\d+\*\*|\Z)", re.MULTILINE | re.DOTALL)
    m = pat.search(section)
    return m.group(0).rstrip() + "\n\n" if m else None


def _first_boc_ep_with_node(nid: int) -> int | None:
    for ep in range(1, 19):
        p = BOC / "drafts" / f"episode_{ep:03d}.md"
        if nid in _register_nids(_read(p)):
            return ep
    return None


def _adapt_draft(text: str, boc_ep: int, cka_seq: int, yt: str, candace_ep: int | None) -> str:
    text = re.sub(
        r"- \*\*Episode\*\*:\s*\d+",
        f"- **Episode**: {cka_seq}",
        text,
        count=1,
    )
    if "- **Monument**:" not in text:
        text = text.replace(
            "- **Source**:",
            f"- **Monument**: cka\n- **CKA seq**: {cka_seq}\n- **YouTube id**: {yt}\n"
            + (f"- **Candace Ep**: {candace_ep}\n" if candace_ep else "")
            + "- **Remap source**: bride_of_charlie "
            + f"monument ep {boc_ep} (no re-extract)\n- **Source**:",
            1,
        )
    text = text.replace("Bride of Charlie", "Candace Kirk Archive")
    text = text.replace(f"Episode {boc_ep}", f"CKA seq {cka_seq}")
    return text


def _apply_claim_lens_tags_to_drafts() -> None:
    """Add CKA claim lens tags on existing Tags: lines when claim text matches (safe line-wise)."""
    for _boc, cka_seq, _yt in REMAP_ROWS:
        path = CKA / "drafts" / f"episode_{cka_seq:03d}.md"
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        out: list[str] = []
        in_claim = False
        buf: list[str] = []
        for line in lines:
            if re.match(r"^\*\*C-\d+\*\*", line):
                if in_claim and buf:
                    out.extend(_maybe_add_lens_tags(buf))
                    buf = []
                in_claim = True
                buf = [line]
                continue
            if in_claim:
                if line.startswith("---") or re.match(r"^\*\*C-\d+\*\*", line) or line.startswith("## "):
                    out.extend(_maybe_add_lens_tags(buf))
                    buf = []
                    in_claim = line.startswith("**C-") is False or not re.match(r"^\*\*C-\d+\*\*", line)
                    if re.match(r"^\*\*C-\d+\*\*", line):
                        in_claim = True
                        buf = [line]
                        continue
                    out.append(line)
                    continue
                buf.append(line)
                continue
            out.append(line)
        if buf:
            out.extend(_maybe_add_lens_tags(buf))
        path.write_text("".join(out), encoding="utf-8")


def _maybe_add_lens_tags(block_lines: list[str]) -> list[str]:
    text = "".join(block_lines)
    extra: list[str] = []
    for lens_id, pat in CLAIM_LENS_KEYWORDS.items():
        if pat.search(text):
            extra.append(lens_id)
    if not extra:
        return block_lines
    out = list(block_lines)
    for i, line in enumerate(out):
        if line.startswith("Tags:"):
            existing = [t.strip() for t in line.split(":", 1)[1].split(",")]
            merged = ", ".join(dict.fromkeys(existing + extra))
            out[i] = f"Tags: {merged}\n"
            return out
    if out and not out[-1].endswith("\n"):
        out[-1] = out[-1] + "\n"
    out.append("Tags: " + ", ".join(extra) + "\n")
    return out


def _boc_intro_order_through_ep8() -> list[int]:
    sys.path.insert(0, str(REPO / "projects" / "monuments" / "scripts"))
    import dia_preflight as dp  # noqa: WPS433

    episodes8 = [e for e in dp.load_draft_episodes(BOC / "drafts") if 1 <= e[0] <= 8]
    ledger = dp.collect_intro_order_from_ledger(episodes8)
    return [nid for _ep, _idx, nid in ledger]


def _write_ledger_baseline_artifacts(intro_ids: list[int]) -> None:
    """episode_000 ledger + density baseline (no register rows → no register_orphan)."""
    person = sorted(n for n in intro_ids if n < 1000)
    topic = sorted(n for n in intro_ids if n >= 1000)
    baseline = {
        "version": 1,
        "description": (
            "N-ids first introduced in BoC monument eps 1–8; used for CKA Batch 1 "
            "dia_preflight band density only (see drafts/episode_000_ledger_baseline.md)."
        ),
        "person_node_ids": person,
        "topic_node_ids": topic,
    }
    (CKA / "config" / "preflight_ledger_baseline.json").write_text(
        json.dumps(baseline, indent=2) + "\n", encoding="utf-8"
    )

    intro_line = ", ".join(f"N-{n}" for n in intro_ids)
    meme_block = ""
    m4 = _extract_meme_block(_read(BOC / "drafts" / "episode_006.md"), 4)
    if m4:
        meme_block = f"\n## 6. Meme Register\n\n<!-- BoC ep 6 M-4 for global meme density -->\n\n{m4}"

    ep0 = f"""# CKA ledger baseline (BoC monument eps 1–8)

## 1. Meta-Data

- **Episode**: 0
- **Monument**: cka
- **Kind**: ledger_baseline
- **Notes**: Preflight-only carryover of BoC eps 1–8 **New Nodes Introduced** order. Not a CKA ingest episode; no claims or register rows.

- **Episode Ledger Summary**:
  - New Nodes Introduced: {intro_line}

## 2. Executive Summary

Ledger baseline for CKA Batch 1 remap (BoC monument eps 9–18 → CKA seq 1–10). Preserves first-introduction order from the Bride of Charlie demo corpus without re-ingesting series eps 1–8.

## 3. Artifact Register

_(none)_

## 4. Node Register

_(none — density via config/preflight_ledger_baseline.json)_

## 5. Claim Register

_(none)_
{meme_block}
"""
    (CKA / "drafts" / "episode_000.md").write_text(ep0, encoding="utf-8")
    legacy = CKA / "drafts" / "episode_000_ledger_baseline.md"
    if legacy.is_file():
        legacy.unlink()


def _strip_register_carryover(draft_path: Path) -> None:
    text = _read(draft_path)
    if "register carryover" not in text:
        return
    text = re.sub(
        r"\n<!-- register carryover:.*?-->\n\n(?:\*\*N-\d+\*\*.*?\n\n)+",
        "\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\n<!-- meme carryover from BoC eps 1–8.*?\n\n(?:\*\*M-\d+\*\*.*?\n\n)+",
        "\n",
        text,
        count=1,
        flags=re.DOTALL,
    )
    draft_path.write_text(text, encoding="utf-8")


def _load_manifest_rows() -> dict[int, dict]:
    manifest = json.loads((CKA / "input" / "episode_manifest.json").read_text(encoding="utf-8"))
    return {row["seq"]: row for row in manifest["episodes"] if row["seq"] <= 10}


def _verify_youtube_ids() -> None:
    manifest = _load_manifest_rows()
    for boc_ep, cka_seq, yt in REMAP_ROWS:
        row = manifest.get(cka_seq)
        if not row or row["youtube_id"] != yt:
            raise SystemExit(f"manifest mismatch seq {cka_seq}: expected {yt}, got {row}")


def _copy_tree_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _build_canonical() -> None:
    sys.path.insert(0, str(REPO / "projects" / "monuments" / "scripts"))
    from dia_preflight import (  # type: ignore
        collect_register_entries,
        first_introduction_meta,
        load_draft_episodes,
    )
    episodes = load_draft_episodes(CKA / "drafts")
    intro = first_introduction_meta(collect_register_entries(episodes))
    active = set(intro.keys())

    boc_canonical = json.loads((BOC / "canonical" / "nodes.json").read_text(encoding="utf-8"))
    boc_to_cka = {b: c for b, c, _ in REMAP_ROWS}

    out_nodes: dict[str, dict] = {}
    for key, meta in boc_canonical.get("nodes", {}).items():
        m = re.match(r"N-(\d+)$", key)
        if not m or int(m.group(1)) not in active:
            continue
        eps = meta.get("episodes") or []
        cka_eps = sorted({boc_to_cka[e] for e in eps if e in boc_to_cka})
        if not cka_eps and int(m.group(1)) in active:
            cka_eps = [1]
        out_nodes[key] = {
            **meta,
            "episodes": cka_eps,
        }

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
    if (BOC / "canonical" / "memes.json").is_file():
        shutil.copy2(BOC / "canonical" / "memes.json", canon_dir / "memes.json")


def main() -> int:
    _verify_youtube_ids()

    for sub in ("transcripts", "transcripts_corrected", "drafts", "inscription", "drafts/.transcript_sha"):
        (CKA / sub).mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest_rows()

    for boc_ep, cka_seq, yt in REMAP_ROWS:
        base = f"episode_{cka_seq:03d}_{yt}"
        boc_base = None
        for pat in BOC.glob(f"transcripts/episode_{boc_ep:03d}_*.txt"):
            if yt in pat.name:
                boc_base = pat
                break
        if not boc_base:
            raise SystemExit(f"Missing BoC transcript for ep {boc_ep} / {yt}")
        _copy_tree_file(boc_base, CKA / "transcripts" / f"{base}.txt")

        corr = BOC / "transcripts_corrected" / boc_base.name
        if corr.is_file():
            _copy_tree_file(corr, CKA / "transcripts_corrected" / f"{base}.txt")

        sha_src = BOC / "drafts" / ".transcript_sha" / f"episode_{boc_ep:03d}.sha256"
        if sha_src.is_file():
            _copy_tree_file(sha_src, CKA / "drafts" / ".transcript_sha" / f"episode_{cka_seq:03d}.sha256")

        draft_src = BOC / "drafts" / f"episode_{boc_ep:03d}.md"
        candace = manifest[cka_seq].get("candace_ep_number")
        draft_text = _adapt_draft(_read(draft_src), boc_ep, cka_seq, yt, candace)
        (CKA / "drafts" / f"episode_{cka_seq:03d}.md").write_text(draft_text, encoding="utf-8")

        for suffix in ("_transcript.txt", "_transcript_verbatim.txt"):
            ins_t = BOC / "inscription" / f"episode_{boc_ep:03d}{suffix}"
            if ins_t.is_file():
                _copy_tree_file(ins_t, CKA / "inscription" / f"episode_{cka_seq:03d}{suffix}")

    _strip_register_carryover(CKA / "drafts" / "episode_001.md")
    _apply_claim_lens_tags_to_drafts()
    intro_ids = _boc_intro_order_through_ep8()
    _write_ledger_baseline_artifacts(intro_ids)

    build_script = BOC / "scripts" / "build_inscription_from_drafts.py"
    build_cmd = [
        sys.executable,
        str(build_script),
        "--drafts",
        str(CKA / "drafts"),
        "--inscription",
        str(CKA / "inscription"),
    ]
    for _boc, cka_seq, _yt in REMAP_ROWS:
        build_cmd.extend(["--episode", str(cka_seq)])
    subprocess.run(build_cmd, check=True, cwd=str(REPO))
    ep0_json = CKA / "inscription" / "episode_000.json"
    if ep0_json.is_file():
        ep0_json.unlink()

    for path in sorted((CKA / "inscription").glob("episode_*.json")):
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
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    shutil.copy2(BOC / "config" / "retired_node_ids.json", CKA / "config" / "retired_node_ids.json")
    _build_canonical()

    scaffold = CKA / "config" / "scaffold_only.json"
    if scaffold.is_file():
        scaffold.unlink()

    urls = [manifest[s]["url"] for s in range(1, 11)]
    (CKA / "input" / "youtube_links.txt").write_text(
        "# CKA seq 1–10 (Batch 1 remap from BoC eps 9–18)\n" + "\n".join(urls) + "\n",
        encoding="utf-8",
    )

    remap_cfg = {
        "batch": 1,
        "membership_tags": ["cka_core", "remapped_from_boc"],
        "rows": [
            {
                "cka_seq": cka,
                "boc_monument_ep": boc,
                "youtube_id": yt,
                "candace_ep_number": manifest[cka].get("candace_ep_number"),
            }
            for boc, cka, yt in REMAP_ROWS
        ],
    }
    (CKA / "config" / "batch1_remap_from_boc.json").write_text(
        json.dumps(remap_cfg, indent=2) + "\n", encoding="utf-8"
    )

    print("[remap] CKA Batch 1 complete (seq 1–10)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
