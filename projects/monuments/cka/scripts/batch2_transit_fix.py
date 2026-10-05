#!/usr/bin/env python3
"""Transit re-audit fix-all for CKA Batch 2 (seq 11–20) on PR 42."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CORR = CKA / "transcripts_corrected"
INS = CKA / "inscription"
REPO = Path(__file__).resolve().parents[4]
BOC_BUILD = REPO / "projects" / "monuments" / "bride_of_charlie" / "scripts" / "build_inscription_from_drafts.py"

NODE_BLOCK = re.compile(
    r"\n\*\*N-1\*\* Charlie Kirk\n.*?\n\*\*N-2\*\* Erika Kirk\n.*?\n(?=\*\*N-42\*\*)",
    re.DOTALL,
)


def _load_hostile_strip():
    spec = importlib.util.spec_from_file_location(
        "hostile_fix_batch1", CKA / "scripts" / "hostile_fix_batch1.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return mod._strip_ads_text, mod.fix_ledger


def _shift_claim_ids(text: str, lo: int, hi: int, delta: int) -> str:
    ids = list(range(hi, lo - 1, -1))
    for cid in ids:
        old = f"C-{cid}"
        new = f"C-{cid + delta}"
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return text


def fix_ep15_false_new() -> None:
    path = DRAFTS / "episode_015.md"
    text = path.read_text(encoding="utf-8")
    text = NODE_BLOCK.sub("\n", text)
    text = re.sub(
        r"(- New Nodes Introduced:\s*)N-1, N-2, ",
        r"\1",
        text,
        count=1,
    )
    if "Reused Nodes Appearing:" in text:
        text = re.sub(
            r"(- Reused Nodes Appearing:\s*)\s*$",
            r"\1N-1, N-2",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    path.write_text(text, encoding="utf-8")


def fix_claim_forks() -> None:
    p18 = DRAFTS / "episode_018.md"
    t18 = p18.read_text(encoding="utf-8")
    if re.search(r"\*\*C-1424\*\*", t18):
        p18.write_text(_shift_claim_ids(t18, 1424, 1459, 1), encoding="utf-8")
    p20 = DRAFTS / "episode_020.md"
    t20 = p20.read_text(encoding="utf-8")
    if re.search(r"\*\*C-1487\*\*", t20):
        p20.write_text(_shift_claim_ids(t20, 1487, 1510, 3), encoding="utf-8")


def scrub_transcripts_11_20(strip_fn) -> int:
    removed = 0
    for ep in range(11, 21):
        for path in sorted(CORR.glob(f"episode_{ep:03d}_*")):
            if path.suffix not in (".md", ".txt"):
                continue
            raw = path.read_text(encoding="utf-8")
            if path.suffix == ".md" and raw.startswith("---"):
                parts = raw.split("---", 2)
                if len(parts) >= 3:
                    body = parts[2]
                    new_body, n = strip_fn(body)
                    removed += n
                    updated = f"---{parts[1]}---{new_body}"
                    if not updated.endswith("\n"):
                        updated += "\n"
                else:
                    updated, n = strip_fn(raw)
                    removed += n
            else:
                updated, n = strip_fn(raw)
                removed += n
            if updated != raw:
                path.write_text(updated, encoding="utf-8")
        ins_path = INS / f"episode_{ep:03d}_transcript.txt"
        if ins_path.is_file():
            raw = ins_path.read_text(encoding="utf-8")
            updated, n = strip_fn(raw)
            removed += n
            if updated != raw:
                ins_path.write_text(updated, encoding="utf-8")
    return removed


def update_transcript_sha(ep: int) -> None:
    draft = DRAFTS / f"episode_{ep:03d}.md"
    if not draft.is_file():
        return
    text = draft.read_text(encoding="utf-8")
    m = re.search(r"- \*\*YouTube id\*\*:\s*(\S+)", text, re.I)
    if not m:
        return
    yt = m.group(1)
    tr = None
    for p in CORR.glob(f"episode_{ep:03d}_{yt}.*"):
        tr = p
        break
    if tr is None:
        hits = list(CORR.glob(f"episode_{ep:03d}_*"))
        tr = hits[0] if hits else None
    if tr is None:
        return
    digest = hashlib.sha256(tr.read_bytes()).hexdigest()
    text = re.sub(
        r"(- \*\*Transcript SHA-256\*\*:\s*)\S+",
        lambda m: f"{m.group(1)}{digest}",
        text,
        count=1,
    )
    draft.write_text(text, encoding="utf-8")
    sha_dir = DRAFTS / ".transcript_sha"
    sha_dir.mkdir(parents=True, exist_ok=True)
    (sha_dir / f"episode_{ep:03d}.sha256").write_text(digest + "\n", encoding="utf-8")


def scan_residual() -> list[str]:
    issues: list[str] = []
    first_claim: dict[str, int] = {}
    first_intro: dict[str, int] = {}
    for path in sorted(DRAFTS.glob("episode_*.md")):
        m = re.search(r"episode_(\d+)", path.name)
        if not m:
            continue
        ep = int(m.group(1))
        if ep < 11 or ep > 20:
            continue
        text = path.read_text(encoding="utf-8")
        for hm in re.finditer(r"^\*\*N-(\d+)\*\*", text, re.MULTILINE):
            nid = f"N-{hm.group(1)}"
            first_intro.setdefault(nid, ep)
        for cm in re.finditer(r"\*\*C-(\d+)\*\*", text):
            cid = f"C-{cm.group(1)}"
            first_claim.setdefault(cid, ep)
        new_line = re.search(r"New Nodes Introduced:\s*(.+)$", text, re.MULTILINE)
        if new_line:
            for nid in [x.strip() for x in new_line.group(1).split(",") if x.strip()]:
                if nid in ("N-1", "N-2") and first_intro.get(nid, ep) < ep:
                    issues.append(f"FALSE_NEW {nid} still New in ep{ep}")
    for cid, ep in sorted(first_claim.items(), key=lambda x: int(x[0][2:])):
        pass
    seen: dict[str, int] = {}
    for path in sorted(DRAFTS.glob("episode_*.md")):
        m = re.search(r"episode_(\d+)", path.name)
        if not m:
            continue
        ep = int(m.group(1))
        if ep < 11:
            continue
        for cm in re.finditer(r"\*\*C-(\d+)\*\*", path.read_text(encoding="utf-8")):
            cid = f"C-{cm.group(1)}"
            if cid in seen and seen[cid] != ep:
                issues.append(f"CLAIM_ID_FORK {cid} ep{seen[cid]} and ep{ep}")
            seen.setdefault(cid, ep)
    return issues


def main() -> int:
    strip_fn, fix_ledger = _load_hostile_strip()
    fix_ep15_false_new()
    fix_claim_forks()
    paths = sorted(DRAFTS.glob("episode_*.md"))
    paths = [p for p in paths if re.match(r"episode_\d{3}\.md$", p.name)]
    fix_ledger(paths)
    scrub_transcripts_11_20(strip_fn)
    for ep in range(11, 21):
        update_transcript_sha(ep)
    subprocess.run(
        [sys.executable, str(CKA / "scripts" / "batch2_rebuild_canonical.py")],
        check=True,
    )
    eps = list(range(11, 21))
    cmd = [
        sys.executable,
        str(BOC_BUILD),
        "--drafts",
        str(DRAFTS),
        "--inscription",
        str(INS),
    ]
    for ep in eps:
        cmd.extend(["--episode", str(ep)])
    subprocess.run(cmd, check=True, cwd=str(REPO))
    issues = scan_residual()
    if issues:
        print("RESIDUAL ISSUES:")
        for i in issues:
            print(" ", i)
        return 1
    print("Transit fix-all OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
