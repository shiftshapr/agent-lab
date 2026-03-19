#!/usr/bin/env python3
"""Tests for phase1_validation schema + reference integrity."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from protocols.episode_analysis.phase1_validation import (
    check_reference_integrity,
    validate_phase1,
)

SCHEMA = Path(__file__).parent.parent / "templates" / "entity_schema.json"


def _minimal_valid() -> dict:
    return {
        "@context": "https://brc222.org/context/v1",
        "@type": "EpisodeAnalysis",
        "meta": {
            "episode": 1,
            "source": "S",
            "video_timestamp_range": "0",
            "extraction_timestamp": "2026-01-01T00:00:00Z",
            "model_version": "m",
            "transcript_sha256": "a" * 64,
        },
        "executive_summary": ".",
        "artifacts": [
            {
                "family_ref": "ART_1",
                "bundle_name": "B",
                "sub_items": [
                    {
                        "ref": "ART_1.1",
                        "description": "x",
                        "related_claims": ["CLAIM_1"],
                        "related_nodes": ["NODE_1"],
                    }
                ],
            }
        ],
        "nodes": [
            {
                "ref": "NODE_1",
                "name": "n",
                "type": "person",
                "description": "d",
                "related_artifacts": ["ART_1.1"],
                "related_claims": ["CLAIM_1"],
            }
        ],
        "claims": [
            {
                "ref": "CLAIM_1",
                "label": "l",
                "claim": "c",
                "anchored_artifacts": ["ART_1.1"],
                "related_nodes": ["NODE_1"],
            }
        ],
    }


def test_integrity_ok():
    errs = check_reference_integrity(_minimal_valid())
    assert errs == [], errs


def test_unknown_anchor():
    d = _minimal_valid()
    d["claims"][0]["anchored_artifacts"] = ["ART_99.1"]
    errs = check_reference_integrity(d)
    assert any("anchored_artifacts" in e for e in errs), errs


def test_self_contradict():
    d = _minimal_valid()
    d["claims"][0]["contradicts_claim_refs"] = ["CLAIM_1"]
    errs = check_reference_integrity(d)
    assert any("itself" in e for e in errs), errs


def test_full_validate_ok():
    errs = validate_phase1(_minimal_valid(), SCHEMA, check_refs=True, check_schema=True)
    assert errs == [], errs


def main():
    test_integrity_ok()
    test_unknown_anchor()
    test_self_contradict()
    test_full_validate_ok()
    print("OK  phase1_validation tests passed.")


if __name__ == "__main__":
    main()
