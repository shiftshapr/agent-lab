#!/usr/bin/env python3
"""Sanity checks for neo4j_ingest markdown parsers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from neo4j_ingest import (
    parse_id_list,
    extract_claims,
    extract_artifacts,
    extract_org_relationship_lines,
    extract_topic_mention_lines,
    resolve_draft_graph_node_id,
    resolve_related_graph_node_ids,
)


def main():
    m = {"N-33": "N-2"}
    assert resolve_draft_graph_node_id("N-33", m) == "N-2"
    assert resolve_draft_graph_node_id("N-99", m) == "N-99"
    assert resolve_draft_graph_node_id("A-1", m) == "A-1"
    gset = {"N-2"}
    assert resolve_related_graph_node_ids(["N-33", "N-2"], m, gset) == ["N-2"]

    assert parse_id_list("A-1001.2, C-1003, N-5") == ["A-1001.2", "C-1003", "N-5"]
    assert parse_id_list("C-1, same_as: A-2.1") == ["C-1", "A-2.1"]

    md = """
## 5. Claim Register
**C-100** Label here
Claim Timestamp: 1:00
Claim: The claim text.
Transcript Snippet: Exact words from video.
Anchored Artifacts: A-100.1
Related Nodes: N-1
Contradicts: C-101
Supports: C-99
Qualifies: C-102
Sensitive Tags: fraud, trafficking
Confidence: low
Uncertainty: Might be wrong.
Investigative Direction: Check sources.
""".strip()
    claims = extract_claims(md, 1)
    assert len(claims) == 1
    c = claims[0]
    assert c["id"] == "C-100"
    assert c["transcript_snippet"] == "Exact words from video."
    assert c["contradicts_claims"] == ["C-101"]
    assert c["supports_claims"] == ["C-99"]
    assert c["qualifies_claims"] == ["C-102"]
    assert c["sensitive_topic_tags"] == ["fraud", "trafficking"]
    assert c["confidence"] == "low"
    assert "wrong" in (c.get("uncertainty_note") or "")

    amd = """
**A-10.1** Newspaper
Video Timestamp: 2:00
*Related: C-1, N-2*
Transcript Snippet: shown on screen.
Confidence: medium
Uncertainty: blurry.
""".strip()
    arts = extract_artifacts(amd, 1)
    assert len(arts) == 1
    a = arts[0]
    assert a["id"] == "A-10.1"
    assert a["transcript_snippet"] == "shown on screen."
    assert a["confidence"] == "medium"

    ext = """
## 8. Organization Network
OrgLink: N-101 subsidiary_of N-102
## 12. Topic Threading
TopicMention: C-100 N-1000
""".strip()
    orgs = extract_org_relationship_lines(ext)
    assert len(orgs) == 1 and orgs[0]["relation"] == "subsidiary_of"
    tm = extract_topic_mention_lines(ext)
    assert tm == [{"claim_id": "C-100", "topic_id": "N-1000"}]

    print("OK  neo4j_ingest parse tests passed.")


if __name__ == "__main__":
    main()
