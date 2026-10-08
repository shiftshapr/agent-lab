#!/usr/bin/env python3
"""
CKA -> BRC-222 2.0.0 companion package builder.

Reads CKA drafts (and inscription JSON when present), resolves every emitted
relationship name from the vendored vocabulary.json, and stages a bridge /
companion package. Does not deploy, inscribe, or write Neo4j.

Usage (from agent-lab root):
  python3 projects/monuments/scripts/cka_brc222_companion.py
  python3 projects/monuments/scripts/cka_brc222_companion.py --cka-root projects/monuments/cka \\
      --out projects/monuments/cka/companion/brc222-2.0.0
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CKA_ROOT = REPO_ROOT / "projects" / "monuments" / "cka"
DEFAULT_VOCAB = DEFAULT_CKA_ROOT / "vendor" / "brc222" / "vocabulary.json"
DEFAULT_OUT = DEFAULT_CKA_ROOT / "companion" / "brc222-2.0.0"

# Retired BRC-222 terms (reject on emit / lookup). Kept here as a deny-list only.
RETIRED_TERMS = frozenset(
    {
        "amplifies",
        "contextualizes",
        "timeline",
        "related",
        "isContradictedBy",
    }
)

# Ledger concept keys -> vocabulary term names used ONLY as lookup keys into
# Vocabulary.require(). Emitted relationship strings always come from the
# loaded vocabulary entry's "name" field, never from these literals directly.
LEDGER_LOOKUP_KEYS = {
    "artifact_backs_claim": "isSupportedBy",
    "independent_or_later_confirms": "isCorroboratedBy",
    "airing_opposes": "contradicts",
    "evidence_shows_false": "isRefutedBy",
    "revises_softening": "isQualifiedBy",
    "revises_builds_on": "extends",
    "belongs_to_collection": "isMemberOf",
}

CLAIM_HEADER_RE = re.compile(r"^\*\*(C-\d+)\*\*\s+(.+)$", re.MULTILINE)
ARTIFACT_HEADER_RE = re.compile(r"^\*\*(A-\d+(?:\.\d+)?)\*\*\s+(.+)$", re.MULTILINE)
EPISODE_DRAFT_RE = re.compile(r"episode_(\d+)\.md$", re.I)
EPISODE_JSON_RE = re.compile(r"episode_(\d+)\.json$", re.I)
ID_TOKEN_RE = re.compile(r"\b([CAM]-\d+(?:\.\d+)?)\b")
META_EPISODE_RE = re.compile(r"^\s*-\s*\*\*Episode\*\*:\s*(\d+)", re.MULTILINE)
META_CKA_SEQ_RE = re.compile(r"^\s*-\s*\*\*CKA seq\*\*:\s*(\d+)", re.MULTILINE)
META_CANDACE_EP_RE = re.compile(r"^\s*-\s*\*\*Candace Ep\*\*:\s*(.+)$", re.MULTILINE)

# REVISES split heuristic cues (document in package README).
QUALIFY_CUES = (
    "softens",
    "soften",
    "caveat",
    "however",
    "narrows",
    "narrow",
    "qualifies",
    "qualify",
    "limits",
    "limited to",
    "walks back",
    "walk-back",
    "walksback",
    "corrects earlier",
    "partially",
    "with the caveat",
    "not as",
    "except that",
    "but only",
)
EXTEND_CUES = (
    "builds on",
    "build on",
    "adds detail",
    "adds that",
    "further",
    "expands",
    "in addition",
    "additionally",
    "restates",
    "updates with",
    "new detail",
    "goes further",
    "elaborates",
    "follows up",
)


@dataclass
class VocabEntry:
    name: str
    raw: dict[str, Any]


class Vocabulary:
    """Load BRC-222 vocabulary.json; resolve terms by name; reject retired."""

    def __init__(self, path: Path):
        self.path = path
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"vocabulary root must be object: {path}")
        self.version = str(data.get("version") or "")
        self.date_modified = str(data.get("dateModified") or "")
        self.namespace = str(data.get("namespace") or "")
        self._by_name: dict[str, VocabEntry] = {}
        for row in data.get("relationships") or []:
            if not isinstance(row, dict):
                continue
            name = row.get("name")
            if not name or not isinstance(name, str):
                continue
            self._by_name[name] = VocabEntry(name=name, raw=row)
            # Index inverse as lookup alias for require() of inverse form? No:
            # only canonical entry names are require()-able for emit. Inverse
            # names are accepted only via alias map for input matching.
            inv = row.get("inverse")
            if isinstance(inv, str) and inv and inv not in self._by_name:
                # Do not register inverse as a separate emitable entry.
                pass
        if not self._by_name:
            raise ValueError(f"vocabulary has no relationships: {path}")

    def require(self, name: str) -> str:
        """Return canonical term name from the vendored file. Fail loudly."""
        if name in RETIRED_TERMS:
            raise ValueError(f"retired BRC-222 term rejected: {name}")
        entry = self._by_name.get(name)
        if entry is None:
            raise KeyError(f"BRC-222 term missing from vocabulary.json: {name!r}")
        # Always return the name field from the loaded entry (not the argument).
        return entry.name

    def has(self, name: str) -> bool:
        return name in self._by_name

    def names(self) -> frozenset[str]:
        return frozenset(self._by_name)


@dataclass
class ClaimRec:
    claim_id: str
    label: str = ""
    body: str = ""
    episode: int | None = None
    anchored_artifacts: list[str] = field(default_factory=list)
    revises: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    supports: list[str] = field(default_factory=list)
    qualifies: list[str] = field(default_factory=list)
    refutes: list[str] = field(default_factory=list)
    source: str = ""


@dataclass
class ArtifactRec:
    artifact_id: str
    label: str = ""
    episode: int | None = None
    source: str = ""


@dataclass
class Edge:
    source: str
    target: str
    relationship: str
    episode: int | None = None
    explanation: str = ""
    review_status: str = "accepted"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_bridge(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "@type": "OrdinalBridge",
            "from": self.source,
            "to": self.target,
            "relationship": self.relationship,
        }
        if self.explanation:
            row["explanation"] = _prose_dashes(self.explanation)
        if self.episode is not None:
            row["episode"] = self.episode
        if self.review_status != "accepted":
            row["review_status"] = self.review_status
        if self.extra:
            row["metadata"] = self.extra
        # Intentionally no "direction" field (inverse pair carries direction).
        return row


def _prose_dashes(s: str) -> str:
    """Dash rule (Daveed, 8 Oct 2026) for builder-authored prose only.

    An em dash (U+2014) becomes an en dash (U+2013). No dash is ever turned
    into a hyphen or other punctuation. Quote-derived and claim-derived text
    (labels, evidence snippets) is NOT passed through here: it is emitted
    exactly as stored in the drafts / inscription.
    """
    if not s:
        return s
    return s.replace("\u2014", "\u2013")


def _split_id_list(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    return ID_TOKEN_RE.findall(raw)


def _parse_claim_block(block: str, claim_id: str, label: str, episode: int, source: str) -> ClaimRec:
    rec = ClaimRec(claim_id=claim_id, label=label.strip(), episode=episode, source=source)
    for line in block.splitlines():
        s = line.strip()
        low = s.lower()
        if low.startswith("claim:") and not low.startswith("claim timestamp"):
            rec.body = s.split(":", 1)[1].strip()
        elif low.startswith("anchored artifacts:"):
            rec.anchored_artifacts = _split_id_list(s.split(":", 1)[1])
        elif low.startswith("revises:"):
            rec.revises = _split_id_list(s.split(":", 1)[1])
        elif low.startswith("contradicts:"):
            rec.contradicts = _split_id_list(s.split(":", 1)[1])
        elif low.startswith("supports:"):
            rec.supports = _split_id_list(s.split(":", 1)[1])
        elif low.startswith("qualifies:"):
            rec.qualifies = _split_id_list(s.split(":", 1)[1])
        elif low.startswith("refutes:"):
            rec.refutes = _split_id_list(s.split(":", 1)[1])
    return rec


def parse_draft(path: Path) -> tuple[int, list[ClaimRec], list[ArtifactRec]]:
    text = path.read_text(encoding="utf-8")
    m = EPISODE_DRAFT_RE.search(path.name)
    episode = int(m.group(1)) if m else -1
    m2 = META_EPISODE_RE.search(text) or META_CKA_SEQ_RE.search(text)
    if m2:
        episode = int(m2.group(1))

    claims: list[ClaimRec] = []
    # Split on claim headers
    matches = list(CLAIM_HEADER_RE.finditer(text))
    for i, m in enumerate(matches):
        claim_id = m.group(1)
        label = m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # Stop at next major section if no next claim
        block = text[start:end]
        # Truncate at ## headers
        cut = re.search(r"\n##\s+", block)
        if cut:
            block = block[: cut.start()]
        claims.append(_parse_claim_block(block, claim_id, label, episode, str(path)))

    artifacts: list[ArtifactRec] = []
    for m in ARTIFACT_HEADER_RE.finditer(text):
        artifacts.append(
            ArtifactRec(
                artifact_id=m.group(1),
                label=m.group(2).strip(),
                episode=episode,
                source=str(path),
            )
        )
    return episode, claims, artifacts


def parse_inscription(path: Path) -> tuple[int, list[ClaimRec], list[ArtifactRec]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    m = EPISODE_JSON_RE.search(path.name)
    episode = int(m.group(1)) if m else -1
    meta = data.get("meta") or {}
    if isinstance(meta, dict) and meta.get("episode") is not None:
        try:
            episode = int(meta["episode"])
        except (TypeError, ValueError):
            pass

    claims: list[ClaimRec] = []
    for cl in data.get("claims") or []:
        if not isinstance(cl, dict):
            continue
        cid = cl.get("ref") or cl.get("@id") or ""
        if not cid:
            continue
        claims.append(
            ClaimRec(
                claim_id=str(cid),
                label=str(cl.get("label") or ""),
                body=str(cl.get("claim") or ""),
                episode=episode,
                anchored_artifacts=[str(x) for x in (cl.get("anchored_artifacts") or [])],
                revises=[str(x) for x in (cl.get("revises_claim_refs") or [])],
                contradicts=[str(x) for x in (cl.get("contradicts_claim_refs") or [])],
                supports=[str(x) for x in (cl.get("supports_claim_refs") or [])],
                qualifies=[str(x) for x in (cl.get("qualifies_claim_refs") or [])],
                refutes=[str(x) for x in (cl.get("refutes_claim_refs") or [])],
                source=str(path),
            )
        )

    artifacts: list[ArtifactRec] = []
    for fam in data.get("artifacts") or []:
        if not isinstance(fam, dict):
            continue
        fam_id = fam.get("ref") or fam.get("@id") or ""
        if fam_id:
            artifacts.append(
                ArtifactRec(
                    artifact_id=str(fam_id),
                    label=str(fam.get("bundle_name") or fam.get("label") or ""),
                    episode=episode,
                    source=str(path),
                )
            )
        for sub in fam.get("sub_items") or fam.get("subItems") or []:
            if not isinstance(sub, dict):
                continue
            sid = sub.get("ref") or sub.get("@id") or ""
            if not sid:
                continue
            artifacts.append(
                ArtifactRec(
                    artifact_id=str(sid),
                    label=str(sub.get("label") or sub.get("description") or "")[:200],
                    episode=episode,
                    source=str(path),
                )
            )
    return episode, claims, artifacts


def merge_claims(primary: ClaimRec, secondary: ClaimRec) -> ClaimRec:
    """Prefer non-empty edge lists; drafts win for typed edges when present."""

    def prefer(a: list[str], b: list[str]) -> list[str]:
        return a if a else b

    return ClaimRec(
        claim_id=primary.claim_id,
        label=primary.label or secondary.label,
        body=primary.body or secondary.body,
        episode=primary.episode if primary.episode is not None else secondary.episode,
        anchored_artifacts=prefer(primary.anchored_artifacts, secondary.anchored_artifacts),
        revises=prefer(primary.revises, secondary.revises),
        contradicts=prefer(primary.contradicts, secondary.contradicts),
        supports=prefer(primary.supports, secondary.supports),
        qualifies=prefer(primary.qualifies, secondary.qualifies),
        refutes=prefer(primary.refutes, secondary.refutes),
        source=primary.source or secondary.source,
    )


def load_cka_corpus(cka_root: Path) -> tuple[dict[str, ClaimRec], dict[str, ArtifactRec], dict[int, str]]:
    """Load drafts + inscriptions. Drafts overlay typed edges onto inscription."""
    claims: dict[str, ClaimRec] = {}
    artifacts: dict[str, ArtifactRec] = {}
    episode_ids: dict[int, str] = {}

    inscription_dir = cka_root / "inscription"
    drafts_dir = cka_root / "drafts"

    if inscription_dir.is_dir():
        for path in sorted(inscription_dir.glob("episode_*.json")):
            ep, cl_list, art_list = parse_inscription(path)
            episode_ids[ep] = f"cka:episode:{ep}"
            for c in cl_list:
                claims[c.claim_id] = c
            for a in art_list:
                artifacts[a.artifact_id] = a

    if drafts_dir.is_dir():
        for path in sorted(drafts_dir.glob("episode_*.md")):
            ep, cl_list, art_list = parse_draft(path)
            episode_ids.setdefault(ep, f"cka:episode:{ep}")
            for c in cl_list:
                if c.claim_id in claims:
                    # Draft typed edges overlay inscription.
                    base = claims[c.claim_id]
                    # Prefer draft edge lists when draft has them; else keep inscription.
                    claims[c.claim_id] = ClaimRec(
                        claim_id=c.claim_id,
                        label=c.label or base.label,
                        body=c.body or base.body,
                        episode=c.episode if c.episode is not None else base.episode,
                        anchored_artifacts=c.anchored_artifacts or base.anchored_artifacts,
                        revises=c.revises or base.revises,
                        contradicts=c.contradicts or base.contradicts,
                        supports=c.supports or base.supports,
                        qualifies=c.qualifies or base.qualifies,
                        refutes=c.refutes or base.refutes,
                        source=c.source,
                    )
                else:
                    claims[c.claim_id] = c
            for a in art_list:
                artifacts.setdefault(a.artifact_id, a)

    return claims, artifacts, episode_ids


def _cue_score(text: str, cues: Iterable[str]) -> int:
    low = text.lower()
    return sum(1 for c in cues if c in low)


def classify_revises(
    newer: ClaimRec, prior_id: str
) -> tuple[str, str, float, str]:
    """
    Heuristic: REVISES -> softening/caveat term vs builds-on term (resolved from vocab).

    Rule (documented for Transit):
    1. Count QUALIFY_CUES vs EXTEND_CUES in label+body.
    2. If qualify_score > extend_score -> propose softening term.
    3. If extend_score > qualify_score -> propose builds-on term.
    4. Tie / no cues -> default to the softening term at low confidence
       (Transit ruling, PR 60 Wave 2.1: a Revises correction qualifies the prior
       claim; there is no builds-on default). Transit must confirm.

    Returns (primary_lookup_key, evidence_snippet, confidence, rationale).
    """
    blob = f"{newer.label}\n{newer.body}"
    q = _cue_score(blob, QUALIFY_CUES)
    e = _cue_score(blob, EXTEND_CUES)
    snippet = (newer.body or newer.label or "")[:240]
    if q > e:
        return (
            "revises_softening",
            snippet,
            min(0.9, 0.55 + 0.1 * (q - e)),
            f"qualify_cues={q} extend_cues={e}",
        )
    if e > q:
        return (
            "revises_builds_on",
            snippet,
            min(0.9, 0.55 + 0.1 * (e - q)),
            f"qualify_cues={q} extend_cues={e}",
        )
    return (
        "revises_softening",
        snippet,
        0.35,
        f"qualify_cues={q} extend_cues={e}; default softening pending Transit",
    )


@dataclass
class BuildResult:
    edges: list[Edge]
    revises_candidates: list[dict[str, Any]]
    nodes: list[dict[str, Any]]
    counts: Counter
    vocab_version: str
    vocab_date: str


def build_package(
    vocab: Vocabulary,
    claims: dict[str, ClaimRec],
    artifacts: dict[str, ArtifactRec],
    episode_ids: dict[int, str],
    show_id: str = "cka:show:candace",
    revises_rulings: dict[str, str] | None = None,
) -> BuildResult:
    """revises_rulings: claim id -> ledger lookup key ('revises_softening' or 'revises_builds_on')
    fixed by Transit for that claim's Revises edges (config/companion_revises_rulings.json)."""
    revises_rulings = revises_rulings or {}
    # Resolve all ledger lookup keys once; emitted strings come from vocab.
    terms = {k: vocab.require(v) for k, v in LEDGER_LOOKUP_KEYS.items()}

    edges: list[Edge] = []
    revises_candidates: list[dict[str, Any]] = []
    seen_edge: set[tuple[str, str, str]] = set()

    def add_edge(edge: Edge) -> None:
        key = (edge.source, edge.target, edge.relationship)
        if key in seen_edge:
            return
        # Symmetric contradicts: also skip reverse duplicate.
        if edge.relationship == terms["airing_opposes"]:
            rev = (edge.target, edge.source, edge.relationship)
            if rev in seen_edge:
                return
        seen_edge.add(key)
        edges.append(edge)

    # Show membership for episodes
    for ep, ep_id in sorted(episode_ids.items()):
        if ep < 0:
            continue
        add_edge(
            Edge(
                source=ep_id,
                target=show_id,
                relationship=terms["belongs_to_collection"],
                episode=ep,
                explanation="Episode belongs to CKA / Candace show collection",
            )
        )

    for c in claims.values():
        ep = c.episode
        ep_id = episode_ids.get(ep or -1, f"cka:episode:{ep}" if ep is not None else None)

        if ep_id:
            add_edge(
                Edge(
                    source=c.claim_id,
                    target=ep_id,
                    relationship=terms["belongs_to_collection"],
                    episode=ep,
                    explanation="Claim aired in episode",
                )
            )

        # Artifact backs claim: claim isSupportedBy artifact
        for aid in c.anchored_artifacts:
            add_edge(
                Edge(
                    source=c.claim_id,
                    target=aid,
                    relationship=terms["artifact_backs_claim"],
                    episode=ep,
                    explanation="Anchored artifact backs claim",
                )
            )

        # Supports: later/independent confirms -> prior isCorroboratedBy newer
        for prior in c.supports:
            add_edge(
                Edge(
                    source=prior,
                    target=c.claim_id,
                    relationship=terms["independent_or_later_confirms"],
                    episode=ep,
                    explanation="Later or reinforcing claim corroborates prior",
                )
            )

        # Contradicts (symmetric)
        for other in c.contradicts:
            add_edge(
                Edge(
                    source=c.claim_id,
                    target=other,
                    relationship=terms["airing_opposes"],
                    episode=ep,
                    explanation="Airing opposes or is inconsistent with other claim",
                )
            )

        # Qualifies: host narrows prior -> prior isQualifiedBy newer
        for prior in c.qualifies:
            add_edge(
                Edge(
                    source=prior,
                    target=c.claim_id,
                    relationship=terms["revises_softening"],
                    episode=ep,
                    explanation="Host narrows or conditions prior claim",
                )
            )

        # Refutes: evidence shows false -> claim isRefutedBy target
        for target in c.refutes:
            add_edge(
                Edge(
                    source=c.claim_id,
                    target=target,
                    relationship=terms["evidence_shows_false"],
                    episode=ep,
                    explanation="Evidence shows claim false",
                )
            )

        # REVISES: one bridge per edge. A Transit ruling fixes the term; otherwise the
        # heuristic primary is emitted pending review. The CSV keeps both candidates.
        for prior in c.revises:
            primary_key, snippet, confidence, rationale = classify_revises(c, prior)
            soft = terms["revises_softening"]
            ext = terms["revises_builds_on"]
            ruled = revises_rulings.get(c.claim_id)
            if ruled:
                primary_key, confidence, rationale = ruled, 1.0, "transit_ruling"
            for lookup_key, term in (
                ("revises_softening", soft),
                ("revises_builds_on", ext),
            ):
                if lookup_key != primary_key:
                    continue
                add_edge(
                    Edge(
                        source=c.claim_id if lookup_key == "revises_builds_on" else prior,
                        target=prior if lookup_key == "revises_builds_on" else c.claim_id,
                        relationship=term,
                        episode=ep,
                        explanation=f"REVISES ({rationale})",
                        review_status="transit_ruled" if ruled else "pending_transit",
                        extra={
                            "ledger": "REVISES",
                            "candidate_of": "revises_split",
                            "heuristic_primary": terms[primary_key],
                            "confidence": confidence,
                        },
                    )
                )
            # CSV rows: both candidates; higher confidence on heuristic primary
            for lookup_key, term in (
                ("revises_softening", soft),
                ("revises_builds_on", ext),
            ):
                is_primary = lookup_key == primary_key
                revises_candidates.append(
                    {
                        "claim_id": c.claim_id,
                        "prior_claim_id": prior,
                        "episode": ep if ep is not None else "",
                        "proposed_term": term,
                        "evidence_snippet": snippet.replace("\n", " ").strip(),
                        "confidence": f"{confidence if is_primary else max(0.1, confidence - 0.25):.2f}",
                        "is_heuristic_primary": "yes" if is_primary else "no",
                        "rationale": rationale,
                        "source": "revises_ledger",
                    }
                )

        # Latent REVISES-split candidates from Supports edges (CSV only).
        # Firm package edge remains corroboration; CKA tip still has few minted
        # Revises lines, so Transit reviews whether a Supports edge is pure
        # corroboration or should be reminted as REVISES (softening vs builds-on).
        if c.supports and not c.revises:
            primary_key, snippet, confidence, rationale = classify_revises(c, "")
            # Without cue hits, classify_revises defaults to softening at 0.35.
            for prior in c.supports:
                term = terms[primary_key]
                other = terms[
                    "revises_builds_on"
                    if primary_key == "revises_softening"
                    else "revises_softening"
                ]
                for proposed, is_primary in ((term, True), (other, False)):
                    revises_candidates.append(
                        {
                            "claim_id": c.claim_id,
                            "prior_claim_id": prior,
                            "episode": ep if ep is not None else "",
                            "proposed_term": proposed,
                            "evidence_snippet": snippet.replace("\n", " ").strip(),
                            "confidence": f"{confidence if is_primary else max(0.1, confidence - 0.25):.2f}",
                            "is_heuristic_primary": "yes" if is_primary else "no",
                            "rationale": rationale + "; latent_from=Supports",
                            "source": "supports_latent",
                        }
                    )

    for a in artifacts.values():
        ep = a.episode
        ep_id = episode_ids.get(ep or -1, f"cka:episode:{ep}" if ep is not None else None)
        if ep_id:
            add_edge(
                Edge(
                    source=a.artifact_id,
                    target=ep_id,
                    relationship=terms["belongs_to_collection"],
                    episode=ep,
                    explanation="Artifact registered in episode",
                )
            )

    nodes: list[dict[str, Any]] = []
    nodes.append(
        {
            "@type": "KnowledgeGraphNode",
            "identifier": show_id,
            "label": "Candace Owens show (CKA)",
            "node_kind": "show",
        }
    )
    for ep, ep_id in sorted(episode_ids.items()):
        if ep < 0:
            continue
        nodes.append(
            {
                "@type": "KnowledgeGraphNode",
                "identifier": ep_id,
                "label": f"CKA episode {ep}",
                "node_kind": "episode",
                "episode": ep,
            }
        )
    for c in sorted(claims.values(), key=lambda x: x.claim_id):
        nodes.append(
            {
                "@type": "KnowledgeGraphNode",
                "identifier": c.claim_id,
                "label": c.label,
                "node_kind": "claim",
                "episode": c.episode,
            }
        )
    for a in sorted(artifacts.values(), key=lambda x: x.artifact_id):
        nodes.append(
            {
                "@type": "KnowledgeGraphNode",
                "identifier": a.artifact_id,
                "label": a.label,
                "node_kind": "artifact",
                "episode": a.episode,
            }
        )

    counts: Counter = Counter(e.relationship for e in edges)
    return BuildResult(
        edges=edges,
        revises_candidates=revises_candidates,
        nodes=nodes,
        counts=counts,
        vocab_version=vocab.version,
        vocab_date=vocab.date_modified,
    )


def write_package(out_dir: Path, result: BuildResult, vocab: Vocabulary, cka_root: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    package = {
        "@context": "https://brc222.org/schema.json",
        "@type": "BRC222CompanionPackage",
        "monument": "cka",
        "vocabulary": {
            "version": vocab.version,
            "dateModified": vocab.date_modified,
            "source": "https://brc222.org/vocabulary.json",
            "vendored": "projects/monuments/cka/vendor/brc222/vocabulary.json",
        },
        "generated_at": generated,
        "cka_root": str(cka_root),
        "locks": {
            "deploy": False,
            "neo4j_write": False,
            "boc_promo": False,
            "pack_inscription": False,
            "canopi_deploy": False,
        },
        "edge_counts": dict(sorted(result.counts.items())),
        "revises_candidate_count": len(result.revises_candidates),
        "nodes": result.nodes,
        "bridges": [e.to_bridge() for e in result.edges],
    }
    (out_dir / "package.json").write_text(
        json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Compact bridges-only file for review
    bridges_doc = {
        "vocabulary_version": vocab.version,
        "edge_counts": dict(sorted(result.counts.items())),
        "bridges": package["bridges"],
    }
    (out_dir / "bridges.json").write_text(
        json.dumps(bridges_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    csv_path = out_dir / "revises-split-candidates.csv"
    fieldnames = [
        "claim_id",
        "prior_claim_id",
        "episode",
        "proposed_term",
        "evidence_snippet",
        "confidence",
        "is_heuristic_primary",
        "rationale",
        "source",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for row in result.revises_candidates:
            w.writerow({k: row.get(k, "") for k in fieldnames})

    # Summary counts for heuristic primary only
    primary_rows = [r for r in result.revises_candidates if r.get("is_heuristic_primary") == "yes"]
    primary_counts = Counter(r["proposed_term"] for r in primary_rows)

    readme = f"""# CKA BRC-222 companion package (staged)

**Status:** staged for Transit review. Not deployed.

| Field | Value |
|-------|-------|
| vocabulary | {vocab.version} ({vocab.date_modified}) |
| vocab source | https://brc222.org/vocabulary.json |
| generated_at (UTC) | {generated} |
| bridges | {len(result.edges)} |
| revises candidate rows | {len(result.revises_candidates)} (both terms per edge) |
| revises heuristic primary | {dict(primary_counts)} |

## Edge counts (emitted relationship names from vocab)

```
{json.dumps(dict(sorted(result.counts.items())), indent=2)}
```

## Ledger -> BRC-222 map

Resolved at runtime from vendored `vocabulary.json` (never emitted as raw literals):

| Ledger | Lookup key | Vocab term |
|--------|------------|------------|
| Artifact backs claim | artifact_backs_claim | (vocab) |
| Supports / later confirms | independent_or_later_confirms | (vocab) |
| CONTRADICTS | airing_opposes | (vocab) |
| Refutes / evidence shows false | evidence_shows_false | (vocab) |
| REVISES softening / Qualifies | revises_softening | (vocab) |
| REVISES builds on | revises_builds_on | (vocab) |
| Belongs to episode / show | belongs_to_collection | (vocab) |

No `direction` field. Retired terms rejected: amplifies, contextualizes, timeline, related, isContradictedBy.

## REVISES split heuristic

For each ledger `Revises:` edge the builder emits **one** bridge. Edges whose newer claim has a
Transit ruling in `config/companion_revises_rulings.json` use the ruled term
(`review_status: transit_ruled`); other edges use the heuristic primary
(`review_status: pending_transit`). The CSV keeps both candidate terms per edge.

Primary pick rule:
1. Score QUALIFY_CUES vs EXTEND_CUES in claim label+body.
2. Higher qualify score -> softening term as primary.
3. Higher extend score -> builds-on term as primary.
4. Tie / no cues -> default softening term at low confidence (no builds-on default).

Latent rows (`source=supports_latent`) come from every `Supports:` edge that lacks a
minted `Revises:` line. Cue hits raise confidence; otherwise primary defaults to the
softening term at low confidence. Those rows do **not** change the firm corroboration
bridge; they are CSV-only hints because the live CKA tip still has few minted `Revises:` lines.

Transit confirms the final term per edge before any deploy.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    summary = {
        "generated_at": generated,
        "vocabulary_version": vocab.version,
        "vocabulary_dateModified": vocab.date_modified,
        "edge_counts": dict(sorted(result.counts.items())),
        "revises_candidate_rows": len(result.revises_candidates),
        "revises_heuristic_primary_counts": dict(primary_counts),
        "bridge_count": len(result.edges),
        "node_count": len(result.nodes),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


def load_revises_rulings(cka_root: Path) -> dict[str, str]:
    """config/companion_revises_rulings.json: {"rulings": {"C-x": {"term_key": "revises_softening", ...}}}."""
    path = cka_root / "config" / "companion_revises_rulings.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for cid, row in (data.get("rulings") or {}).items():
        key = row.get("term_key") if isinstance(row, dict) else row
        if key not in ("revises_softening", "revises_builds_on"):
            raise ValueError(f"{path}: {cid} has unknown term_key {key!r}")
        out[cid] = key
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build CKA BRC-222 2.0.0 companion package")
    ap.add_argument("--cka-root", type=Path, default=DEFAULT_CKA_ROOT)
    ap.add_argument("--vocab", type=Path, default=DEFAULT_VOCAB)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--json-summary", type=Path, default=None)
    args = ap.parse_args(argv)

    vocab = Vocabulary(args.vocab)
    if vocab.version != "2.0.0":
        print(f"WARN: vocabulary version is {vocab.version!r}, expected '2.0.0'", file=sys.stderr)

    # Fail fast if any ledger lookup key is missing from vocab
    for _k, name in LEDGER_LOOKUP_KEYS.items():
        vocab.require(name)

    claims, artifacts, episode_ids = load_cka_corpus(args.cka_root)
    result = build_package(vocab, claims, artifacts, episode_ids, revises_rulings=load_revises_rulings(args.cka_root))
    write_package(args.out, result, vocab, args.cka_root)

    primary = Counter(
        r["proposed_term"]
        for r in result.revises_candidates
        if r.get("is_heuristic_primary") == "yes"
    )
    print(f"Wrote package to {args.out}")
    print(f"Vocab {vocab.version} ({vocab.date_modified}) from {args.vocab}")
    print(f"Claims {len(claims)} artifacts {len(artifacts)} episodes {len(episode_ids)}")
    print(f"Bridges {len(result.edges)} counts={dict(sorted(result.counts.items()))}")
    print(f"Revises candidates (primary): {dict(primary)}")

    if args.json_summary:
        args.json_summary.write_text(
            json.dumps(
                {
                    "out": str(args.out),
                    "edge_counts": dict(sorted(result.counts.items())),
                    "revises_primary": dict(primary),
                    "bridge_count": len(result.edges),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
