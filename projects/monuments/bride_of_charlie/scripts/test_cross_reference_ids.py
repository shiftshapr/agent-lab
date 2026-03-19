#!/usr/bin/env python3
"""
Test cross-reference IDs: schema validation + assign_ids remapping.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import jsonschema

SCHEMA_PATH = Path(__file__).parent.parent / "templates" / "entity_schema.json"
from assign_ids import assign_ids_to_entities, apply_ids_to_json


def test_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    sample = {
        "@context": "https://brc222.org/context/v1",
        "@type": "EpisodeAnalysis",
        "meta": {"episode": 1, "source": "Test", "video_timestamp_range": "0-1"},
        "executive_summary": "Test.",
        "artifacts": [
            {
                "@type": "ArtifactFamily",
                "@id": "ART_1",
                "family_ref": "ART_1",
                "bundle_name": "B",
                "sub_items": [
                    {
                        "@type": "Artifact",
                        "@id": "ART_1.1",
                        "ref": "ART_1.1",
                        "description": "A1",
                        "same_as_artifact_refs": [],
                        "related_claims": [],
                        "related_nodes": [],
                    },
                    {
                        "@type": "Artifact",
                        "@id": "ART_1.2",
                        "ref": "ART_1.2",
                        "description": "Dup",
                        "same_as_artifact_refs": ["ART_1.1"],
                        "related_claims": [],
                        "related_nodes": [],
                    },
                ],
            }
        ],
        "nodes": [
            {
                "@type": "Person",
                "@id": "NODE_1",
                "ref": "NODE_1",
                "name": "X",
                "type": "person",
                "description": ".",
                "related_artifacts": [],
                "related_claims": [],
            }
        ],
        "claims": [
            {
                "@type": "Claim",
                "@id": "CLAIM_1",
                "ref": "CLAIM_1",
                "label": "L1",
                "claim": "C1",
                "anchored_artifacts": ["ART_1.1"],
                "related_nodes": ["NODE_1"],
                "supports_claim_refs": [],
            },
            {
                "@type": "Claim",
                "@id": "CLAIM_2",
                "ref": "CLAIM_2",
                "label": "L2",
                "claim": "C2",
                "anchored_artifacts": ["ART_1.2"],
                "related_nodes": ["NODE_1"],
                "contradicts_claim_refs": ["CLAIM_1"],
                "supports_claim_refs": ["CLAIM_1"],
            },
        ],
    }
    jsonschema.validate(instance=sample, schema=schema)
    print("OK  Cross-reference schema validation passed.")


def test_assign_ids_remapping():
    data = json.loads(
        json.dumps(
            {
                "meta": {"episode": 1},
                "executive_summary": "x",
                "artifacts": [
                    {
                        "family_ref": "ART_1",
                        "bundle_name": "B",
                        "sub_items": [
                            {"ref": "ART_1.1", "description": "a"},
                            {
                                "ref": "ART_1.2",
                                "description": "b",
                                "same_as_artifact_refs": ["ART_1.1"],
                                "related_claims": [],
                                "related_nodes": [],
                            },
                        ],
                    }
                ],
                "nodes": [
                    {"ref": "NODE_1", "type": "person", "name": "n", "description": "d"}
                ],
                "claims": [
                    {
                        "ref": "CLAIM_1",
                        "label": "l",
                        "claim": "c",
                        "anchored_artifacts": ["ART_1.1"],
                        "related_nodes": ["NODE_1"],
                    },
                    {
                        "ref": "CLAIM_2",
                        "label": "l2",
                        "claim": "c2",
                        "anchored_artifacts": ["ART_1.2"],
                        "related_nodes": ["NODE_1"],
                        "contradicts_claim_refs": ["CLAIM_1"],
                        "supports_claim_refs": ["CLAIM_1"],
                    },
                ],
                "memes": [
                    {
                        "ref": "M-1",
                        "occurrences": [
                            {"speaker_node_ref": "NODE_1", "episode": 1, "quote": "q"}
                        ],
                    }
                ],
            }
        )
    )
    ledger = {
        "next_artifact": 100,
        "next_claim": 200,
        "next_node": 1,
        "next_node_inv": 1000,
    }
    ref_to_id, _ = assign_ids_to_entities(data, ledger)
    out = apply_ids_to_json(data, ref_to_id)
    c1 = out["claims"][0]["ref"]
    c2 = out["claims"][1]["ref"]
    assert out["claims"][1]["contradicts_claim_refs"] == [c1]
    assert out["claims"][1]["supports_claim_refs"] == [c1]
    a11 = out["artifacts"][0]["sub_items"][0]["ref"]
    assert out["artifacts"][0]["sub_items"][1]["same_as_artifact_refs"] == [a11]
    assert out["memes"][0]["occurrences"][0]["speaker_node_ref"] == ref_to_id["NODE_1"]
    print("OK  assign_ids cross-reference + meme speaker remapping passed.")


if __name__ == "__main__":
    test_schema()
    test_assign_ids_remapping()
