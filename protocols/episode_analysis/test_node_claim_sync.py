#!/usr/bin/env python3
"""Tests for node↔claim edge sanitization (phase-1 refs)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from protocols.episode_analysis.node_claim_sync import (
    sanitize_node_claim_graph_final,
    sanitize_node_claim_graph_phase1,
)


def test_phase1_drops_mismatched_node_to_claim():
    data = {
        "nodes": [
            {"ref": "NODE_1", "related_claims": ["CLAIM_1"]},
            {"ref": "NODE_2", "related_claims": ["CLAIM_1"]},
        ],
        "claims": [
            {"ref": "CLAIM_1", "related_nodes": ["NODE_1"]},
        ],
    }
    log = sanitize_node_claim_graph_phase1(data, add_claim_backlinks=False)
    assert any("NODE_2" in line and "CLAIM_1" in line for line in log)
    n2 = next(n for n in data["nodes"] if n["ref"] == "NODE_2")
    assert n2["related_claims"] == []


def test_phase1_backlink_adds_claim_to_node():
    data = {
        "nodes": [{"ref": "NODE_1", "related_claims": []}],
        "claims": [{"ref": "CLAIM_1", "related_nodes": ["NODE_1"]}],
    }
    sanitize_node_claim_graph_phase1(data, add_claim_backlinks=True)
    assert data["nodes"][0]["related_claims"] == ["CLAIM_1"]


def test_phase1_drops_unknown_claim_ref_on_node():
    data = {
        "nodes": [{"ref": "NODE_1", "related_claims": ["CLAIM_999"]}],
        "claims": [],
    }
    log = sanitize_node_claim_graph_phase1(data, add_claim_backlinks=False)
    assert any("no such claim" in line for line in log)
    assert data["nodes"][0]["related_claims"] == []


def test_phase1_drops_unknown_claim_on_artifact_sub():
    data = {
        "artifacts": [
            {
                "family_ref": "ART_1",
                "sub_items": [{"ref": "ART_1.1", "related_claims": ["CLAIM_1", "CLAIM_404"]}],
            }
        ],
        "claims": [{"ref": "CLAIM_1", "related_nodes": []}],
        "nodes": [],
    }
    sanitize_node_claim_graph_phase1(data, add_claim_backlinks=False)
    assert data["artifacts"][0]["sub_items"][0]["related_claims"] == ["CLAIM_1"]


def test_phase1_empty_related_nodes_keeps_node_claim():
    data = {
        "nodes": [{"ref": "NODE_9", "related_claims": ["CLAIM_1"]}],
        "claims": [{"ref": "CLAIM_1", "related_nodes": []}],
    }
    sanitize_node_claim_graph_phase1(data, add_claim_backlinks=False)
    assert data["nodes"][0]["related_claims"] == ["CLAIM_1"]


def test_final_ids_same_policy():
    data = {
        "nodes": [
            {"@id": "N-1", "ref": "N-1", "related_claims": ["C-1"]},
            {"@id": "N-2", "ref": "N-2", "related_claims": ["C-1"]},
        ],
        "claims": [{"@id": "C-1", "ref": "C-1", "related_nodes": ["N-1"]}],
    }
    sanitize_node_claim_graph_final(data, add_claim_backlinks=False)
    n2 = next(n for n in data["nodes"] if n["@id"] == "N-2")
    assert n2["related_claims"] == []


if __name__ == "__main__":
    test_phase1_drops_mismatched_node_to_claim()
    test_phase1_backlink_adds_claim_to_node()
    test_phase1_drops_unknown_claim_ref_on_node()
    test_phase1_drops_unknown_claim_on_artifact_sub()
    test_phase1_empty_related_nodes_keeps_node_claim()
    test_final_ids_same_policy()
    print("ok")
