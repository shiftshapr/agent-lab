#!/usr/bin/env python3
"""
Dense intro-order renumber for global C-* and A-* IDs (ep1→ep8).

Builds old→new maps from draft Artifact/Claim Register first-appearance order,
applies across drafts, inscription JSON, output JSON, and cross-episode docs.
Writes config/retired_claim_ids.json, config/retired_artifact_ids.json, and
docs/boc-PR*-claim-artifact-nid-maps.md.

Usage (dry-run):
  python scripts/renumber_claims_artifacts.py --dry-run

Apply:
  python scripts/renumber_claims_artifacts.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_DIR / "drafts"
CONFIG_DIR = PROJECT_DIR / "config"
DOCS_DIR = PROJECT_DIR / "docs"

ART_FAMILY = re.compile(r"^\*\*A-(\d+)\*\*\s")
ART_SUB = re.compile(r"^\*\*A-(\d+)\.(\d+)\*\*")
CLAIM_DEF = re.compile(r"^\*\*C-(\d+)\*\*")

# Match C-/A- IDs in text (sub-items before bare families)
_ID_TOKEN = re.compile(r"\b(A-\d+(?:\.\d+)?|C-\d+)\b")


def _build_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str], list[int], list[int]]:
    """Return (claim_map, art_family_map, art_sub_map, claims_order, art_families_order)."""
    episodes = [DRAFTS_DIR / f"episode_{i:03d}.md" for i in range(1, 9)]

    claims_order: list[int] = []
    art_families_order: list[int] = []
    art_subs: dict[int, list[int]] = {}

    for ep in episodes:
        if not ep.exists():
            raise FileNotFoundError(f"Missing draft: {ep}")
        text = ep.read_text(encoding="utf-8")

        art_match = re.search(r"## 3\. Artifact Register\n(.*?)(?=\n## 4\.|\Z)", text, re.DOTALL)
        if art_match:
            for line in art_match.group(1).splitlines():
                line = line.strip()
                fm = ART_FAMILY.match(line)
                if fm:
                    fid = int(fm.group(1))
                    if fid not in art_families_order:
                        art_families_order.append(fid)
                sm = ART_SUB.match(line)
                if sm:
                    fam, sub = int(sm.group(1)), int(sm.group(2))
                    art_subs.setdefault(fam, [])
                    if sub not in art_subs[fam]:
                        art_subs[fam].append(sub)

        claim_match = re.search(r"## 5\. Claim Register\n(.*?)(?=\n## 6\.|\Z)", text, re.DOTALL)
        if claim_match:
            for line in claim_match.group(1).splitlines():
                cm = CLAIM_DEF.match(line.strip())
                if cm:
                    cid = int(cm.group(1))
                    if cid not in claims_order:
                        claims_order.append(cid)

    claim_map = {f"C-{old}": f"C-{1000 + i}" for i, old in enumerate(claims_order)}
    art_family_map = {f"A-{old}": f"A-{1000 + i}" for i, old in enumerate(art_families_order)}

    art_sub_map: dict[str, str] = {}
    for old_fam, subs in art_subs.items():
        new_fam = art_family_map.get(f"A-{old_fam}", f"A-{old_fam}")
        new_num = int(new_fam.split("-")[1])
        for i, sub in enumerate(subs):
            art_sub_map[f"A-{old_fam}.{sub}"] = f"A-{new_num}.{i + 1}"

    return claim_map, art_family_map, art_sub_map, claims_order, art_families_order


def _combined_replace_map(
    claim_map: dict[str, str],
    art_family_map: dict[str, str],
    art_sub_map: dict[str, str],
) -> dict[str, str]:
    """Single map: sub-items + families + claims. Identity entries omitted."""
    combined: dict[str, str] = {}
    combined.update(art_sub_map)
    combined.update(art_family_map)
    combined.update(claim_map)
    return {k: v for k, v in combined.items() if k != v}


def _apply_map(text: str, replace_map: dict[str, str]) -> str:
    """Two-phase replace via placeholders to avoid chain collisions."""
    if not replace_map:
        return text
    # Longest keys first when assigning placeholders
    keys = sorted(replace_map.keys(), key=len, reverse=True)
    placeholder: dict[str, str] = {}
    out = text
    for i, old in enumerate(keys):
        token = f"__REN_{i:04d}__"
        placeholder[token] = replace_map[old]
        out = re.sub(rf"\b{re.escape(old)}\b", token, out)
    for token, new in placeholder.items():
        out = out.replace(token, new)
    return out


def _collect_target_files() -> list[Path]:
    paths: list[Path] = []
    for i in range(1, 9):
        paths.append(DRAFTS_DIR / f"episode_{i:03d}.md")
    for name in ("cross_episode_analysis_draft.md", "cross_episode_analysis_v2.md", "patterns_report.md"):
        p = DRAFTS_DIR / name
        if p.exists():
            paths.append(p)
    paths.extend(sorted((PROJECT_DIR / "inscription").glob("episode_*.json")))
    review_state = PROJECT_DIR / "inscription" / ".review_state.json"
    if review_state.exists():
        paths.append(review_state)
    paths.extend(sorted((PROJECT_DIR / "output").glob("episode_*.json")))
    for script in (
        "repair_grounding_snippets.py",
        "apply_audit_grounding_fixes.py",
    ):
        p = PROJECT_DIR / "scripts" / script
        if p.exists():
            paths.append(p)
    return [p for p in paths if p.exists()]


def _write_retired_json(
    claim_map: dict[str, str],
    art_family_map: dict[str, str],
    art_sub_map: dict[str, str],
    claims_order: list[int],
    art_families_order: list[int],
) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    claim_retired: dict[str, dict] = {}
    for old in claims_order:
        old_s, new_s = f"C-{old}", claim_map[f"C-{old}"]
        if old_s != new_s:
            claim_retired[old_s] = {
                "survives_as": new_s,
                "reason": f"Intro-order dense renumber ep1→ep8; was {old_s}.",
            }

    art_retired: dict[str, dict] = {}
    for old in art_families_order:
        old_s, new_s = f"A-{old}", art_family_map[f"A-{old}"]
        if old_s != new_s:
            art_retired[old_s] = {
                "survives_as": new_s,
                "reason": f"Intro-order dense renumber ep1→ep8; artifact family was {old_s}.",
            }
    for old_sub, new_sub in sorted(art_sub_map.items()):
        if old_sub != new_sub:
            art_retired[old_sub] = {
                "survives_as": new_sub,
                "reason": f"Sub-item renumbered under new family ID.",
            }

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "retired_claim_ids.json").write_text(
        json.dumps(
            {
                "version": 1,
                "updated": now,
                "description": "Tombstone ledger for legacy C-* slots after intro-order dense renumber (C-1000+).",
                "retired": claim_retired,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (CONFIG_DIR / "retired_artifact_ids.json").write_text(
        json.dumps(
            {
                "version": 1,
                "updated": now,
                "description": "Tombstone ledger for legacy A-* family/sub-item slots after intro-order dense renumber (A-1000+).",
                "retired": art_retired,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_maps_md(
    pr_num: str,
    claim_map: dict[str, str],
    art_family_map: dict[str, str],
    art_sub_map: dict[str, str],
    claims_order: list[int],
    art_families_order: list[int],
    files_touched: list[str],
) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out = DOCS_DIR / f"boc-{pr_num}-claim-artifact-nid-maps.md"

    lines = [
        f"# Bride of Charlie — Claim & Artifact ID maps ({pr_num})",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "## Summary",
        "",
        f"- Claims: {len(claims_order)} dense C-1000..C-{1000 + len(claims_order) - 1}",
        f"- Artifact families: {len(art_families_order)} dense A-1000..A-{1000 + len(art_families_order) - 1}",
        f"- Artifact sub-items remapped: {len(art_sub_map)}",
        "",
        "## Claim map (old → new)",
        "",
        "| Old | New |",
        "|-----|-----|",
    ]
    for old in claims_order:
        old_s, new_s = f"C-{old}", claim_map[f"C-{old}"]
        mark = "" if old_s == new_s else " ← moved"
        lines.append(f"| {old_s} | {new_s}{mark} |")

    lines.extend(["", "## Artifact family map (old → new)", "", "| Old | New |", "|-----|-----|"])
    for old in art_families_order:
        old_s, new_s = f"A-{old}", art_family_map[f"A-{old}"]
        mark = "" if old_s == new_s else " ← moved"
        lines.append(f"| {old_s} | {new_s}{mark} |")

    moved_subs = [(k, v) for k, v in sorted(art_sub_map.items()) if k != v]
    if moved_subs:
        lines.extend(["", "## Artifact sub-item map (old → new)", "", "| Old | New |", "|-----|-----|"])
        for old_s, new_s in moved_subs:
            lines.append(f"| {old_s} | {new_s} |")

    lines.extend(["", "## Files touched", ""])
    for f in sorted(files_touched):
        lines.append(f"- `{f}`")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Dense intro-order C/A renumber")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run stats only)")
    parser.add_argument("--pr-label", default="PR25", help="Label for maps markdown filename")
    args = parser.parse_args()

    claim_map, art_family_map, art_sub_map, claims_order, art_families_order = _build_maps()
    replace_map = _combined_replace_map(claim_map, art_family_map, art_sub_map)

    print(f"Claims: {len(claims_order)} → C-1000..C-{1000 + len(claims_order) - 1}")
    print(f"Artifact families: {len(art_families_order)} → A-1000..A-{1000 + len(art_families_order) - 1}")
    print(f"IDs requiring remap: {len(replace_map)}")
    moved_claims = sum(1 for o in claims_order if claim_map[f"C-{o}"] != f"C-{o}")
    moved_fams = sum(1 for o in art_families_order if art_family_map[f"A-{o}"] != f"A-{o}")
    moved_subs = sum(1 for k, v in art_sub_map.items() if k != v)
    print(f"  Claims moved: {moved_claims}, families moved: {moved_fams}, sub-items moved: {moved_subs}")

    if not args.apply:
        print("\nDry-run only. Pass --apply to write.")
        return 0

    files = _collect_target_files()
    touched: list[str] = []
    for path in files:
        original = path.read_text(encoding="utf-8")
        updated = _apply_map(original, replace_map)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            touched.append(str(path.relative_to(PROJECT_DIR)))

    _write_retired_json(claim_map, art_family_map, art_sub_map, claims_order, art_families_order)
    touched.extend(
        [
            "config/retired_claim_ids.json",
            "config/retired_artifact_ids.json",
        ]
    )
    maps_path = _write_maps_md(
        args.pr_label, claim_map, art_family_map, art_sub_map, claims_order, art_families_order, touched
    )
    touched.append(str(maps_path.relative_to(PROJECT_DIR)))

    print(f"\nApplied renumber to {len(files)} candidate files ({len(touched)} touched).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
