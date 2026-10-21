"""ROADMAP 3.0: the CKA source model round-trips Markdown byte for byte and validates its schema."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cka" / "scripts" / "source"))
import cka_source as cs  # noqa: E402

SAMPLE = """## 1. Meta-Data

- **Episode**: 7

## 5. Claim Register

**C-12** Host says X

Claim Timestamp: 00:01:02

Claim: The host says X.
Transcript Snippet: X happened
Anchored Artifacts:
Mentions: N-3
*Related: C-11*

---

## 6. Meme Register

**M-4** (meme) Big Mad

### Occurrence 1

Quote: big mad
"""


class TestSource(unittest.TestCase):
    def test_round_trip_and_fields(self):
        doc = cs.parse_md(SAMPLE, 7)
        self.assertEqual(cs.render(doc), SAMPLE)
        self.assertEqual(cs.validate(doc), [])
        claim = cs.items(doc, "claim")[0]
        self.assertEqual(claim["id"], "C-12")
        self.assertEqual(cs.field(claim, "Claim Timestamp"), "00:01:02")
        cs.set_field(claim, "Claim", "The host says Y.")
        self.assertIn("Claim: The host says Y.", cs.render(doc))
        self.assertEqual(cs.items(doc, "meme")[0]["id"], "M-4")

    def test_missing_required_field(self):
        doc = cs.parse_md(SAMPLE.replace("Claim Timestamp: 00:01:02\n", ""), 7)
        self.assertTrue(any("missing Claim Timestamp" in e for e in cs.validate(doc)))


if __name__ == "__main__":
    unittest.main()
