#!/usr/bin/env python3
"""
Episode Quality Scoring — Bride of Charlie

Scores each episode on five dimensions:
  1. Artifact coverage     — fraction of claims with anchored artifacts
  2. Claim grounding      — average evidence per claim
  3. Cross-reference density — node references per claim
  4. Timestamp completeness — claims/artifacts with video timestamps
  5. Node connectivity    — avg related_nodes / related_claims per node

Outputs:
  drafts/quality_scores.json   — full per-episode scores
  stdout summary table

Usage:
    python3 scripts/quality_score.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
INSCRIPTION_DIR = PROJECT_DIR / "inscription"
DRAFTS_DIR = PROJECT_DIR / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)


def load_inscription(ep: int) -> dict | None:
    fp = INSCRIPTION_DIR / f"episode_{ep:03d}.json"
    if not fp.exists():
        return None
    with open(fp) as f:
        return json.load(f)


def score_artifact_coverage(data: dict) -> float:
    """
    Fraction of claims that have at least one anchored artifact.
    Score 0–1.
    """
    claims = data.get("claims", [])
    if not claims:
        return 0.0
    anchored = sum(1 for c in claims if c.get("anchored_artifacts"))
    return anchored / len(claims)


def score_claim_grounding(data: dict) -> float:
    """
    Average number of anchored artifacts per claim.
    Normalized: score = min(avg / 2.0, 1.0) — 2 artifacts/claim is full score.
    """
    claims = data.get("claims", [])
    if not claims:
        return 0.0
    total = sum(len(c.get("anchored_artifacts", [])) for c in claims)
    avg = total / len(claims)
    return min(avg / 2.0, 1.0)


def score_cross_reference_density(data: dict) -> float:
    """
    Average number of related_nodes per claim.
    Normalized: score = min(avg / 3.0, 1.0) — 3 nodes/claim is full score.
    """
    claims = data.get("claims", [])
    if not claims:
        return 0.0
    total = sum(len(c.get("related_nodes", [])) for c in claims)
    avg = total / len(claims)
    return min(avg / 3.0, 1.0)


def score_timestamp_completeness(data: dict) -> float:
    """
    Fraction of claims + artifact sub-items that have a video_timestamp.
    Weighted: claims count 1x, artifact sub-items count 0.5x.
    """
    claims = data.get("claims", [])
    artifacts = data.get("artifacts", [])

    total_weight = len(claims) + 0.5 * sum(len(a.get("sub_items", [])) for a in artifacts)
    if total_weight == 0:
        return 0.0

    ts_weight = 0.0
    for c in claims:
        if c.get("claim_timestamp") or c.get("transcript_snippet"):
            ts_weight += 1.0
    for a in artifacts:
        for sub in a.get("sub_items", []):
            if sub.get("video_timestamp"):
                ts_weight += 0.5

    return ts_weight / total_weight


def score_node_connectivity(data: dict) -> float:
    """
    Average (related_nodes + related_claims) per node.
    Normalized: score = min(avg / 4.0, 1.0) — 4 connections/node is full score.
    """
    nodes = data.get("nodes", [])
    if not nodes:
        return 0.0
    total = sum(
        len(n.get("related_nodes", [])) + len(n.get("related_claims", []))
        for n in nodes
    )
    avg = total / len(nodes)
    return min(avg / 4.0, 1.0)


def score_episode(ep: int) -> dict[str, Any]:
    """Compute all five scores for a single episode."""
    data = load_inscription(ep)
    if data is None:
        return {"episode": ep, "error": "not_found"}

    n_claims = len(data.get("claims", []))
    n_artifacts = sum(len(a.get("sub_items", [])) for a in data.get("artifacts", []))
    n_nodes = len(data.get("nodes", []))

    ac = score_artifact_coverage(data)
    cg = score_claim_grounding(data)
    crd = score_cross_reference_density(data)
    ts = score_timestamp_completeness(data)
    nc = score_node_connectivity(data)

    overall = (ac * 0.25 + cg * 0.25 + crd * 0.20 + ts * 0.15 + nc * 0.15) * 100

    return {
        "episode": ep,
        "n_claims": n_claims,
        "n_artifacts": n_artifacts,
        "n_nodes": n_nodes,
        "artifact_coverage": round(ac, 3),
        "claim_grounding": round(cg, 3),
        "cross_ref_density": round(crd, 3),
        "timestamp_completeness": round(ts, 3),
        "node_connectivity": round(nc, 3),
        "overall_score": round(overall, 1),
        "grades": {
            "artifact_coverage": _letter(ac),
            "claim_grounding": _letter(cg),
            "cross_ref_density": _letter(crd),
            "timestamp_completeness": _letter(ts),
            "node_connectivity": _letter(nc),
        },
    }


def _letter(score: float) -> str:
    if score >= 0.9:
        return "A"
    elif score >= 0.8:
        return "B"
    elif score >= 0.6:
        return "C"
    elif score >= 0.4:
        return "D"
    else:
        return "F"


def find_episodes() -> list[int]:
    """Discover all episode numbers in inscription/.py"""
    episodes = []
    for fp in sorted(INSCRIPTION_DIR.glob("episode_*.json")):
        import re
        m = re.search(r"episode_(\d+)", fp.stem)
        if m:
            episodes.append(int(m.group(1)))
    return episodes


def main() -> None:
    episodes = find_episodes()
    if not episodes:
        print("[quality_score] No inscription JSONs found.")
        return

    results = []
    for ep in episodes:
        results.append(score_episode(ep))

    results.sort(key=lambda x: x["episode"])

    # Write JSON
    json_path = DRAFTS_DIR / "quality_scores.json"
    with open(json_path, "w") as f:
        json.dump({"episodes": results}, f, indent=2)
    print(f"[quality_score] Wrote {json_path}")

    # Print summary table
    print()
    print("Episode Quality Scores")
    print("=" * 100)
    header = (
        f"{'Ep':<5} {'Artifacts':>9} {'Claims':>6} {'Nodes':>5} "
        f"{'AC':>5} {'CG':>5} {'CRD':>5} {'TS':>5} {'NC':>5} "
        f"{'Overall':>8}  Grades (AC/CG/CRD/TS/NC)"
    )
    print(header)
    print("-" * 100)
    for r in results:
        if "error" in r:
            print(f"  {r['episode']:<3}  ERROR: {r['error']}")
            continue
        ac = r["grades"]["artifact_coverage"]
        cg = r["grades"]["claim_grounding"]
        crd = r["grades"]["cross_ref_density"]
        ts = r["grades"]["timestamp_completeness"]
        nc = r["grades"]["node_connectivity"]
        g = f"{ac} {cg} {crd} {ts} {nc}"
        print(
            f"  {r['episode']:<3}  "
            f"{r['n_artifacts']:>9} {r['n_claims']:>6} {r['n_nodes']:>5} "
            f"{r['artifact_coverage']:>5.3f} {r['claim_grounding']:>5.3f} "
            f"{r['cross_ref_density']:>5.3f} {r['timestamp_completeness']:>5.3f} "
            f"{r['node_connectivity']:>5.3f} "
            f"{r['overall_score']:>7.1f}%  {g}"
        )

    print("-" * 100)
    avg_overall = sum(r["overall_score"] for r in results if "error" not in r) / len(results)
    print(f"  {'Average overall':<60} {avg_overall:>7.1f}%")
    print()
    print("Dimensions: AC=Artifact Coverage | CG=Claim Grounding | CRD=Cross-Ref Density | TS=Timestamp | NC=Node Connectivity")

    # Write markdown table too
    md_path = DRAFTS_DIR / "quality_scores.md"
    lines = [
        "# Episode Quality Scores",
        "",
        "| Ep | Artifacts | Claims | Nodes | AC | CG | CRD | TS | NC | Overall |",
        "|------|-----------|--------|-------|----|----|------|----|----|--------|",
    ]
    for r in results:
        if "error" in r:
            continue
        lines.append(
            f"| {r['episode']} | {r['n_artifacts']} | {r['n_claims']} | {r['n_nodes']} |"
            f" {r['artifact_coverage']:.3f} | {r['claim_grounding']:.3f} |"
            f" {r['cross_ref_density']:.3f} | {r['timestamp_completeness']:.3f} |"
            f" {r['node_connectivity']:.3f} | {r['overall_score']:.1f}% |"
        )
    lines.append("")
    lines.append("*AC=Artifact Coverage | CG=Claim Grounding | CRD=Cross-Ref Density | TS=Timestamp Completeness | NC=Node Connectivity*")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[quality_score] Wrote {md_path}")


if __name__ == "__main__":
    main()
