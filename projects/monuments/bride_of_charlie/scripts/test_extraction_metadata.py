#!/usr/bin/env python3
"""Schema + inject_extraction_meta behavior."""
import json
import sys
from pathlib import Path

# agent-lab/projects/monuments/bride_of_charlie/scripts -> parents[4] = agent-lab
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import jsonschema

from protocols.episode_analysis.episode_analysis_protocol import inject_extraction_meta

SCHEMA_PATH = Path(__file__).parent.parent / "templates" / "entity_schema.json"


def main():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    sample = {
        "@context": "https://brc222.org/context/v1",
        "@type": "EpisodeAnalysis",
        "meta": {
            "episode": 1,
            "source": "S",
            "video_timestamp_range": "0",
            "extraction_timestamp": "2026-03-18T12:00:00Z",
            "model_version": "test-model",
            "transcript_sha256": "a" * 64,
        },
        "executive_summary": ".",
        "artifacts": [
            {
                "family_ref": "ART_1",
                "bundle_name": "B",
                "sub_items": [{"ref": "ART_1.1", "description": "x", "related_claims": [], "related_nodes": []}],
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
    jsonschema.validate(instance=sample, schema=schema)

    data = {"meta": {"episode": 2}}
    inject_extraction_meta(data, "hello transcript\n", "my-model")
    assert data["meta"]["episode"] == 2
    assert data["meta"]["model_version"] == "my-model"
    assert len(data["meta"]["transcript_sha256"]) == 64
    assert data["meta"]["extraction_timestamp"].endswith("Z")
    jsonschema.validate(instance={**sample, "meta": data["meta"]}, schema=schema)

    print("OK  Extraction metadata tests passed.")


if __name__ == "__main__":
    main()
