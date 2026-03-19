#!/usr/bin/env python3
"""Unit test: collect_phase1_extraction_review_items."""
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT))

from canonical_nodes import collect_phase1_extraction_review_items


def main():
    doc = {
        "claims": [{"ref": "CLAIM_1", "confidence": "high"}],
        "nodes": [{"ref": "NODE_1", "confidence": "low", "uncertainty_note": "maybe"}],
        "artifacts": [
            {
                "sub_items": [
                    {"ref": "ART_1.1", "confidence": "medium"},
                ]
            }
        ],
        "memes": [
            {
                "ref": "M-1",
                "occurrences": [{"confidence": "low", "quote": "x"}],
            }
        ],
    }
    items = collect_phase1_extraction_review_items(doc)
    types = {i["entity"] for i in items}
    assert "node" in types and "artifact" in types and "meme_occurrence" in types
    assert not any(i["ref"] == "CLAIM_1" for i in items)
    print("OK  collect_phase1_extraction_review_items tests passed.")


if __name__ == "__main__":
    main()
