"""Tests for ``bride_neo4j_hub`` (no live Neo4j required for import path)."""

from __future__ import annotations

import unittest
from pathlib import Path

from apps.draft_editor import bride_neo4j_hub as nhub


class TestNeo4jHubSummary(unittest.TestCase):
    def test_missing_validate_script(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            out = nhub.fetch_neo4j_summary(p)
            self.assertFalse(out.get("available"))
            self.assertIn("not found", (out.get("error") or "").lower())


if __name__ == "__main__":
    unittest.main()
