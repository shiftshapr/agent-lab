#!/usr/bin/env python3
"""Unit tests for pipeline_gates (name-freeze, SHA freshness, snippet grounding)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_gates import (  # noqa: E402
    assert_name_freeze_for_transcript,
    audit_draft_grounding,
    check_draft_freshness,
    scan_text_for_leftovers,
    sha256_text,
    snippet_in_transcript,
)


def test_tyler_storm_buer_standalone():
    text = "confirmed ASU undergraduate Storm Buer as the new student regent"
    hits = scan_text_for_leftovers(text)
    assert any(h.pattern_id == "storm_buer" for h in hits)


def test_sergeant_ber_variants():
    for phrase in ("Sergeant Ber spoke", "Sgt. Ber arrived", "sgt ber said"):
        hits = scan_text_for_leftovers(phrase)
        assert any(h.pattern_id == "sergeant_ber" for h in hits), phrase


def test_december_not_flagged_for_ber():
    text = "We met in December and talked about the budget."
    hits = scan_text_for_leftovers(text)
    assert not hits, hits


def test_tyler_buer_flagged():
    text = "the state senate confirmed Tyler Storm Buer as regent"
    hits = scan_text_for_leftovers(text)
    ids = {h.pattern_id for h in hits}
    assert "tyler_storm_buer" in ids or "tyler_boyer_variants" in ids


def test_tyler_boyer_pattern():
    text = "Tyler Boyer introduced them at the rally."
    hits = scan_text_for_leftovers(text)
    assert any(h.pattern_id == "tyler_boyer_variants" for h in hits)


def test_snippet_ellipsis_match():
    tx = "we did send erika an email asking specifically how many times she visited romania"
    snip = "we did send Erika an email... how many times she visited Romania"
    assert snippet_in_transcript(snip, tx)


def test_draft_freshness_sha_mismatch(tmp_path: Path):
    project = tmp_path / "proj"
    corr = project / "transcripts_corrected"
    drafts = project / "drafts"
    corr.mkdir(parents=True)
    drafts.mkdir(parents=True)
    tfile = corr / "episode_001_test.txt"
    tfile.write_text("hello world\n", encoding="utf-8")
    digest = sha256_text("hello world\n")
    draft = drafts / "episode_001_test.md"
    draft.write_text(f"- **Transcript SHA-256**: {'0' * 64}\n", encoding="utf-8")
    fresh, err = check_draft_freshness(project, 1, draft_path=draft, transcript_path=tfile)
    assert not fresh
    assert err and "SHA" in err
    draft.write_text(f"- **Transcript SHA-256**: {digest}\n", encoding="utf-8")
    fresh2, err2 = check_draft_freshness(project, 1, draft_path=draft, transcript_path=tfile)
    assert fresh2 and err2 is None


def test_audit_missing_anchored_artifacts():
    md = """
## 5. Claim Register
**C-100** Test claim
Claim Timestamp: 1:00
Claim: Something happened.
Transcript Snippet: exact words in transcript here
Anchored Artifacts:
Related Nodes: N-1
Investigative Direction: check
"""
    tx = "exact words in transcript here and more"
    errs = audit_draft_grounding("episode_001_x.md", md, tx)
    assert any("missing Anchored Artifacts" in e for e in errs)


def test_audit_empty_snippet_fails():
    md = """
**A-10.1** Doc
Video Timestamp: 2:00
*Related: C-1*
Transcript Snippet:
"""
    errs = audit_draft_grounding("episode_001_x.md", md, "some transcript")
    assert any("empty Transcript Snippet" in e for e in errs)


def main() -> None:
    test_tyler_storm_buer_standalone()
    test_sergeant_ber_variants()
    test_december_not_flagged_for_ber()
    test_tyler_buer_flagged()
    test_tyler_boyer_pattern()
    test_snippet_ellipsis_match()
    with tempfile.TemporaryDirectory() as td:
        test_draft_freshness_sha_mismatch(Path(td))
    test_audit_missing_anchored_artifacts()
    test_audit_empty_snippet_fails()
    print("OK  pipeline_gates tests passed.")


if __name__ == "__main__":
    main()
