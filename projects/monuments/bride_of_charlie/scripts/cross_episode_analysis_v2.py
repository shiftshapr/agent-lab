#!/usr/bin/env python3
"""
Cross-Episode Synthesis Analysis v2 — Bride of Charlie

Reads ALL inscription JSONs from inscription/, performs:
  1. Evidence convergence — nodes appearing across multiple episodes (ranked by claim_count)
  2. Rhetorical fingerprints — repeated deflection phrases with timestamps
  3. Investigation pressure map — per-episode pressure scores per node

Outputs: drafts/cross_episode_analysis_v2.md

Usage:
    python3 scripts/cross_episode_analysis_v2.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
INSCRIPTION_DIR = PROJECT_DIR / "inscription"
DRAFTS_DIR = PROJECT_DIR / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Deflection / rhetorical phrases to scan for (case-insensitive)
# ---------------------------------------------------------------------------
DEFLECTION_PATTERNS = [
    re.compile(r"\bi don't recall\b", re.I),
    re.compile(r"\bi don't remember\b", re.I),
    re.compile(r"\bto the best of my knowledge\b", re.I),
    re.compile(r"\bas far as i know\b", re.I),
    re.compile(r"\bi believe\b", re.I),
    re.compile(r"\bmy understanding is\b", re.I),
    re.compile(r"\bthat's my recollection\b", re.I),
    re.compile(r"\bif i recall correctly\b", re.I),
    re.compile(r"\bi'm not sure\b", re.I),
    re.compile(r"\bnot to my knowledge\b", re.I),
    re.compile(r"\bthat i know of\b", re.I),
    re.compile(r"\bmy sources say\b", re.I),
    re.compile(r"\bmy sources tell me\b", re.I),
    re.compile(r"\bfrom what i understand\b", re.I),
    re.compile(r"\bmy impression is\b", re.I),
    re.compile(r"\bjust trust me\b", re.I),
    re.compile(r"\byou'll have to ask\b", re.I),
    re.compile(r"\bthat'll be revealed\b", re.I),
    re.compile(r"\bgoing to get into that\b", re.I),
    re.compile(r"\bwe're going to cover\b", re.I),
    re.compile(r"\bwe'll get to that\b", re.I),
    re.compile(r"\bgoing to show you\b", re.I),
    re.compile(r"\bwhat i can tell you\b", re.I),
    re.compile(r"\bwhat i will say is\b", re.I),
    re.compile(r"\bi'm not going to speculate\b", re.I),
    re.compile(r"\bno reason to doubt\b", re.I),
    re.compile(r"\bthe record shows\b", re.I),
    re.compile(r"\bon the record\b", re.I),
    re.compile(r"\bthis is a matter of\b", re.I),
    re.compile(r"\bgoing to let the evidence speak\b", re.I),
    re.compile(r"\bweigh the evidence\b", re.I),
    re.compile(r"\bdraw your own conclusions\b", re.I),
]


def load_all_inscriptions() -> list[tuple[int, dict]]:
    """Return list of (episode_number, data) sorted by episode."""
    results = []
    for fp in sorted(INSCRIPTION_DIR.glob("episode_*.json")):
        m = re.search(r"episode_(\d+)", fp.stem)
        if not m:
            continue
        ep = int(m.group(1))
        with open(fp) as f:
            results.append((ep, json.load(f)))
    return results


def extract_node_stats(inscriptions: list[tuple[int, dict]]) -> dict[str, dict]:
    """
    For each node ref, aggregate claim_count, evidence_count, episode_count,
    and investigative_pressure across all episodes.
    """
    node_data: dict[str, dict] = defaultdict(lambda: {
        "ref": "",
        "name": "",
        "type": "",
        "claim_count": 0,
        "evidence_count": 0,
        "episode_count": 0,
        "episodes": [],
        "pressure": "",
        "description": "",
        "tags": [],
    })

    for ep, data in inscriptions:
        for node in data.get("nodes", []):
            ref = node.get("@id", node.get("ref", ""))
            if not ref:
                continue
            nd = node_data[ref]
            nd["ref"] = ref
            nd["name"] = node.get("name", "")
            nd["type"] = node.get("type", "")
            nd["description"] = node.get("description", "")
            nd["tags"] = node.get("tags", [])
            nd["claim_count"] += node.get("claim_count", 0)
            nd["evidence_count"] += node.get("evidence_count", 0)
            nd["episodes"].append(ep)
            nd["episode_count"] = len(nd["episodes"])
            # Track the highest pressure level seen
            pressure = node.get("investigative_pressure", "low")
            pressure_rank = {"high": 3, "medium": 2, "low": 1}.get(pressure, 0)
            best_pressure_rank = {"high": 3, "medium": 2, "low": 1}.get(nd["pressure"], 0)
            if pressure_rank >= best_pressure_rank:
                nd["pressure"] = pressure

    return node_data


def find_convergence(node_data: dict[str, dict], min_episodes: int = 2) -> list[dict]:
    """Return nodes sorted by evidence weight (claim_count * episode_count)."""
    candidates = [
        nd for nd in node_data.values() if nd["episode_count"] >= min_episodes
    ]
    candidates.sort(key=lambda x: x["claim_count"] * x["episode_count"], reverse=True)
    return candidates


def extract_memes(inscriptions: list[tuple[int, dict]]) -> list[dict]:
    """Aggregate meme occurrences across episodes."""
    meme_map: dict[str, dict] = {}
    for ep, data in inscriptions:
        for meme in data.get("memes", []):
            ref = meme.get("@id", meme.get("ref", ""))
            if not ref:
                continue
            if ref not in meme_map:
                meme_map[ref] = {
                    "ref": ref,
                    "canonical_term": meme.get("canonical_term", ""),
                    "type": meme.get("type", ""),
                    "occurrences": [],
                    "episode_count": 0,
                    "episodes": [],
                }
            for occ in meme.get("occurrences", []):
                meme_map[ref]["occurrences"].append({**occ, "episode": ep})
                meme_map[ref]["episodes"].append(ep)
    # Convert episode sets to sorted lists for JSON safety
    for meme in meme_map.values():
        meme["episodes"] = sorted(meme["episodes"])
        meme["episode_count"] = len(meme["episodes"])
    return list(meme_map.values())


def extract_rhetorical_fingerprints(inscriptions: list[tuple[int, dict]]) -> list[dict]:
    """
    Scan transcript snippets across all inscriptions for deflection patterns.
    Returns phrases with timestamps and episode context.
    """
    results = []
    for ep, data in inscriptions:
        all_snippets: list[str] = []
        for artifact in data.get("artifacts", []):
            for sub in artifact.get("sub_items", []):
                snip = sub.get("transcript_snippet", "")
                if snip:
                    all_snippets.append(snip)
        for claim in data.get("claims", []):
            snip = claim.get("transcript_snippet", "")
            if snip:
                all_snippets.append(snip)

        for pattern in DEFLECTION_PATTERNS:
            for snip in all_snippets:
                if pattern.search(snip):
                    # Extract the matching phrase and surrounding context
                    match = pattern.search(snip)
                    start = max(0, match.start() - 40)
                    end = min(len(snip), match.end() + 40)
                    ctx = snip[start:end]
                    results.append({
                        "pattern": pattern.pattern.replace("\\b", ""),
                        "episode": ep,
                        "snippet_context": ctx.strip(),
                        "full_snippet": snip.strip(),
                    })

    # Deduplicate by (pattern, episode, snippet)
    seen = set()
    unique = []
    for r in results:
        key = (r["pattern"], r["episode"], r["full_snippet"][:60])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def build_pressure_map(
    inscriptions: list[tuple[int, dict]],
    node_data: dict[str, dict],
) -> list[dict]:
    """
    Per-episode pressure for each node that appears in multiple episodes
    or has high pressure.
    """
    pressure_map: dict[str, dict] = {}
    for ep, data in inscriptions:
        for node in data.get("nodes", []):
            ref = node.get("@id", node.get("ref", ""))
            if not ref:
                continue
            pressure = node.get("investigative_pressure", "low")
            nd = node_data.get(ref, {})
            if nd.get("episode_count", 1) >= 1:
                entry = pressure_map.setdefault(ref, {
                    "ref": ref,
                    "name": nd.get("name", node.get("name", "")),
                    "type": nd.get("type", node.get("type", "")),
                    "episode_pressure": {},
                    "max_pressure": "low",
                })
                entry["episode_pressure"][ep] = pressure
                if {"high": 3, "medium": 2, "low": 1}.get(pressure, 0) > \
                   {"high": 3, "medium": 2, "low": 1}.get(entry["max_pressure"], 0):
                    entry["max_pressure"] = pressure
    return [v for v in pressure_map.values() if len(v["episode_pressure"]) > 1 or v["max_pressure"] == "high"]


def write_markdown(
    inscriptions: list[tuple[int, dict]],
    node_data: dict[str, dict],
    convergence: list[dict],
    memes: list[dict],
    fingerprints: list[dict],
    pressure_map: list[dict],
    outpath: Path,
) -> None:
    total_eps = len(inscriptions)
    total_claims = sum(len(d.get("claims", [])) for _, d in inscriptions)
    total_artifacts = sum(
        sum(len(a.get("sub_items", [])) for a in d.get("artifacts", []))
        for _, d in inscriptions
    )

    lines = [
        "# Cross-Episode Synthesis Analysis v2",
        f"*Generated from {total_eps} episodes | {total_artifacts} artifacts | {total_claims} claims*",
        "",
    ]

    # ── 1. Evidence Convergence ─────────────────────────────────────────────
    lines.append("## 1. Evidence Convergence (Top Nodes by Claim Count)")
    lines.append("")
    lines.append("Nodes ranked by `claim_count × episode_count` — higher = more cross-episode investigative weight.")
    lines.append("")
    lines.append("| Rank | Node | Type | Episodes | Claims | Evidence | Pressure |")
    lines.append("|------|------|------|----------|--------|----------|----------|")

    for i, nd in enumerate(convergence[:20], 1):
        eps = ", ".join(str(e) for e in sorted(nd["episodes"]))
        lines.append(
            f"| {i} | **{nd['name']}** ({nd['ref']}) | {nd['type']} | "
            f"{eps} | {nd['claim_count']} | {nd['evidence_count']} | {nd['pressure']} |"
        )

    lines.append("")
    lines.append("*Only nodes appearing in 2+ episodes shown. Nodes appearing in 1 episode are omitted.*")
    lines.append("")

    # Nodes unique to single episodes that have high pressure
    single_ep_high = [
        nd for nd in node_data.values()
        if nd["episode_count"] == 1 and nd["pressure"] == "high"
    ]
    if single_ep_high:
        lines.append("### High-Pressure Single-Episode Nodes")
        lines.append("")
        for nd in sorted(single_ep_high, key=lambda x: x["claim_count"], reverse=True):
            lines.append(f"- **{nd['name']}** ({nd['ref']}) — {nd['claim_count']} claims, pressure: {nd['pressure']}")
        lines.append("")

    # ── 2. Rhetorical Fingerprints ────────────────────────────────────────────
    lines.append("## 2. Rhetorical Fingerprints")
    lines.append("")
    lines.append(f"Found {len(fingerprints)} deflection-pattern occurrences across all episodes.")
    lines.append("")

    if fingerprints:
        # Group by pattern
        by_pattern: dict[str, list] = defaultdict(list)
        for fp in fingerprints:
            by_pattern[fp["pattern"]].append(fp)

        for pattern, occurrences in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
            lines.append(f"### \"{pattern}\" ({len(occurrences)} occurrences)")
            lines.append("")
            for occ in sorted(occurrences, key=lambda x: (x["episode"], x["snippet_context"][:30])):
                ep = occ["episode"]
                snippet = occ["snippet_context"]
                lines.append(f"- **Ep {ep}**: *\"...{snippet}...\"*")
            lines.append("")
    else:
        lines.append("*No deflection patterns detected in current episode set.*")
        lines.append("")

    # ── 3. Meme Frequency ────────────────────────────────────────────────────
    memes.sort(key=lambda x: (-x["episode_count"], -len(x["occurrences"])))
    lines.append("## 3. Meme Frequency Across Episodes")
    lines.append("")
    lines.append("| Meme | Type | Episodes | Occurrences |")
    lines.append("|------|------|----------|-------------|")
    for meme in memes[:15]:
        lines.append(
            f"| **{meme['canonical_term']}** ({meme['ref']}) | {meme['type']} | "
            f"{meme['episode_count']} | {len(meme['occurrences'])} |"
        )
    lines.append("")

    # ── 4. Investigation Pressure Map ────────────────────────────────────────
    lines.append("## 4. Investigation Pressure Map")
    lines.append("")
    lines.append("Cross-episode pressure for nodes with multi-episode presence or high pressure.")
    lines.append("")
    lines.append("| Node | Type | Max Pressure | Pressure by Episode |")
    lines.append("|------|------|--------------|----------------------|")

    for entry in sorted(pressure_map, key=lambda x: (
        -{"high": 3, "medium": 2, "low": 1}.get(x["max_pressure"], 0),
        x["name"],
    )):
        ep_pressure = ", ".join(
            f"Ep{ep}={p[:1].upper()}" for ep, p in sorted(entry["episode_pressure"].items())
        )
        lines.append(
            f"| **{entry['name']}** ({entry['ref']}) | {entry['type']} | "
            f"{entry['max_pressure'].upper()} | {ep_pressure} |"
        )
    lines.append("")

    # ── 5. Per-Episode Summary ──────────────────────────────────────────────
    lines.append("## 5. Per-Episode Summary")
    lines.append("")
    for ep, data in sorted(inscriptions):
        n_nodes = len(data.get("nodes", []))
        n_claims = len(data.get("claims", []))
        n_artifacts = sum(len(a.get("sub_items", [])) for a in data.get("artifacts", []))
        n_memes = len(data.get("memes", []))
        summary_text = data.get("executive_summary", "")[:120].replace("\n", " ")
        lines.append(f"### Episode {ep}")
        lines.append(f"- Nodes: {n_nodes} | Claims: {n_claims} | Artifacts: {n_artifacts} | Memes: {n_memes}")
        if summary_text:
            lines.append(f"- *{summary_text}...*")
        lines.append("")

    outpath.write_text("\n".join(lines), encoding="utf-8")
    print(f"[cross_episode_analysis_v2] Wrote {outpath}")


def main() -> None:
    inscriptions = load_all_inscriptions()
    if not inscriptions:
        print("[cross_episode_analysis_v2] No inscription JSONs found in inscription/")
        return

    node_data = extract_node_stats(inscriptions)
    convergence = find_convergence(node_data, min_episodes=2)
    memes = extract_memes(inscriptions)
    fingerprints = extract_rhetorical_fingerprints(inscriptions)
    pressure_map = build_pressure_map(inscriptions, node_data)

    outpath = DRAFTS_DIR / "cross_episode_analysis_v2.md"
    write_markdown(
        inscriptions,
        node_data,
        convergence,
        memes,
        fingerprints,
        pressure_map,
        outpath,
    )

    # Also dump structured data
    import json
    structured_path = DRAFTS_DIR / "cross_episode_analysis_v2.json"
    structured = {
        "convergence": [
            {**nd, "episodes": sorted(list(nd["episodes"]))} for nd in convergence
        ],
        "memes": memes,
        "fingerprints": fingerprints,
        "pressure_map": [
            {**e, "episodes_list": list(e["episode_pressure"].keys())}
            for e in pressure_map
        ],
    }
    structured_path.write_text(json.dumps(structured, indent=2), encoding="utf-8")
    print(f"[cross_episode_analysis_v2] Wrote {structured_path}")


if __name__ == "__main__":
    main()
