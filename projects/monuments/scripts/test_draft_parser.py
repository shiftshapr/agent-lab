"""ROADMAP 0.7: one draft parser. extract_claims (neo4j_ingest) is used by the builder, the tag sync and the
timestamp check; these tests hold it to the preflight's claim iterator and to the inscriptions."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MON = Path(__file__).resolve().parents[1]
CKA = MON / "cka"
sys.path.insert(0, str(MON / "bride_of_charlie" / "scripts"))
from neo4j_ingest import extract_claims  # noqa: E402


def _preflight():
    spec = importlib.util.spec_from_file_location("dia_preflight_t", MON / "scripts" / "dia_preflight.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dia_preflight_t"] = mod
    spec.loader.exec_module(mod)
    return mod


DRAFT = """## 5. Claim Register

**C-1** Host Says the Footage Was Omitted

Claim Timestamp: 00:01:00
Claim: The host says the footage was omitted.
Transcript Snippet: the footage was omitted
Tags: relevance:core

**C-2** Host Says It Matters

Claim Timestamp: 00:02:00
Claim: The host says it matters.

## 6. Meme Register

**M-1** (meme) Example
Confidence: high
Tags: wave3
"""


def test_last_claim_stops_at_next_section():
    """A last claim must not pick up the Meme Register's Confidence or Tags lines."""
    c = {x["id"]: x for x in extract_claims(DRAFT, 1)}
    assert c["C-1"]["tags"] == ["relevance:core"]
    assert c["C-2"]["tags"] == [] and c["C-2"]["confidence"] is None


def test_preflight_keeps_claims_whose_title_says_omitted():
    """The meta-label filter skipped real claims titled '... Omitted ...', hiding them from preflight checks."""
    assert [cid for cid, _, _ in _preflight().iter_claim_blocks(DRAFT)] == ["C-1", "C-2"]


def test_archive_parsers_agree():
    """For every CKA draft: extract_claims, the preflight iterator and the inscription hold the same claims,
    and each inscription claim's timestamp, snippet and tags match the parse."""
    pf = _preflight()
    for dp in sorted((CKA / "drafts").glob("episode_*.md")):
        ip = CKA / "inscription" / dp.name.replace(".md", ".json")
        if not ip.exists():
            continue
        text = dp.read_text(encoding="utf-8")
        parsed = {c["id"]: c for c in extract_claims(text, 0)}
        assert set(parsed) == {cid for cid, _, _ in pf.iter_claim_blocks(text)}, dp.name
        insc = {c["ref"]: c for c in json.loads(ip.read_text(encoding="utf-8"))["claims"]}
        assert set(insc) == set(parsed), dp.name
        for cid, c in insc.items():
            p = parsed[cid]
            assert c.get("claim_timestamp") == p["claim_ts"], (dp.name, cid)
            assert c.get("transcript_snippet") == p["transcript_snippet"], (dp.name, cid)
            assert set(p["tags"]) <= set(c.get("tags") or []), (dp.name, cid)
