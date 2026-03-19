#!/usr/bin/env python3
"""
Test quote anchoring: validate that Phase 1 schema accepts transcript_snippet
on claims, artifacts, and quote on meme occurrences.
"""
import json
import sys
from pathlib import Path

# Add agent-lab root for imports
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import jsonschema

SCHEMA_PATH = Path(__file__).parent.parent / "templates" / "entity_schema.json"


def test_quote_anchoring_schema():
    """Phase 1 JSON with transcript_snippet/quote should validate."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    sample = {
        "@context": "https://brc222.org/context/v1",
        "@type": "EpisodeAnalysis",
        "meta": {"episode": 1, "source": "Test", "video_timestamp_range": "00:00-01:00"},
        "executive_summary": "Test.",
        "artifacts": [
            {
                "@type": "ArtifactFamily",
                "@id": "ART_1",
                "family_ref": "ART_1",
                "bundle_name": "Test Bundle",
                "sub_items": [
                    {
                        "@type": "Artifact",
                        "@id": "ART_1.1",
                        "ref": "ART_1.1",
                        "description": "Test artifact",
                        "transcript_snippet": "Here is the exact quote from the transcript.",
                        "related_claims": [],
                        "related_nodes": [],
                    }
                ],
            }
        ],
        "nodes": [
            {
                "@type": "Person",
                "@id": "NODE_1",
                "ref": "NODE_1",
                "name": "Test",
                "type": "person",
                "description": "Test.",
                "related_artifacts": [],
                "related_claims": [],
            }
        ],
        "claims": [
            {
                "@type": "Claim",
                "@id": "CLAIM_1",
                "ref": "CLAIM_1",
                "label": "Test claim",
                "claim": "Test.",
                "anchored_artifacts": ["ART_1.1"],
                "related_nodes": ["NODE_1"],
                "transcript_snippet": "The exact words from the transcript that support this claim.",
            }
        ],
        "memes": [
            {
                "ref": "M-1",
                "canonical_term": "Test",
                "type": "meme",
                "occurrences": [
                    {
                        "episode": 1,
                        "video_timestamp": "00:05:00",
                        "quote": "Exact transcript snippet verbatim.",
                        "speaker_node_ref": "NODE_1",
                        "context": "Test.",
                    }
                ],
                "context": "Test.",
            }
        ],
    }

    jsonschema.validate(instance=sample, schema=schema)
    print("OK  Quote anchoring schema test passed.")


if __name__ == "__main__":
    test_quote_anchoring_schema()
