#!/usr/bin/env python3
"""Validate schema accepts confidence and uncertainty_note on entities."""
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import jsonschema

SCHEMA_PATH = Path(__file__).parent.parent / "templates" / "entity_schema.json"


def main():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    sample = {
        "@context": "https://brc222.org/context/v1",
        "@type": "EpisodeAnalysis",
        "meta": {"episode": 1, "source": "T", "video_timestamp_range": "0"},
        "executive_summary": ".",
        "artifacts": [
            {
                "family_ref": "ART_1",
                "bundle_name": "B",
                "sub_items": [
                    {
                        "ref": "ART_1.1",
                        "description": "x",
                        "confidence": "low",
                        "uncertainty_note": "Partially obscured",
                        "related_claims": [],
                        "related_nodes": [],
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
                "related_artifacts": [],
                "related_claims": [],
                "confidence": "medium",
                "uncertainty_note": "Name spelled phonetically in transcript",
            }
        ],
        "claims": [
            {
                "ref": "CLAIM_1",
                "label": "l",
                "claim": "c",
                "anchored_artifacts": ["ART_1.1"],
                "related_nodes": ["NODE_1"],
                "confidence": "high",
            }
        ],
        "memes": [
            {
                "ref": "M-1",
                "occurrences": [
                    {
                        "episode": 1,
                        "quote": "q",
                        "speaker_node_ref": "NODE_1",
                        "confidence": "low",
                        "uncertainty_note": "Overlapping speakers",
                    }
                ],
            }
        ],
    }
    jsonschema.validate(instance=sample, schema=schema)
    # invalid confidence should fail
    bad = json.loads(json.dumps(sample))
    bad["claims"][0]["confidence"] = "maybe"
    try:
        jsonschema.validate(instance=bad, schema=schema)
    except jsonschema.ValidationError:
        print("OK  Invalid confidence rejected.")
    else:
        raise SystemExit("expected ValidationError for bad confidence")
    print("OK  Confidence / uncertainty schema tests passed.")


if __name__ == "__main__":
    main()
