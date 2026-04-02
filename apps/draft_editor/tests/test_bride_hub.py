"""Unit tests for ``bride_hub`` (stdlib only — run: python -m unittest apps.draft_editor.tests.test_bride_hub)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apps.draft_editor import bride_hub as bh


class TestEpisodeNumbersForUi(unittest.TestCase):
    def test_bride_repo_matches_youtube_line_count(self) -> None:
        root = Path(__file__).resolve().parents[3]
        bride = root / "projects" / "monuments" / "bride_of_charlie"
        if not (bride / "input" / "youtube_links.txt").is_file():
            self.skipTest("youtube_links.txt missing")
        nums = bh.episode_numbers_for_ui(bride)
        self.assertGreaterEqual(len(nums), 1)
        self.assertEqual(nums[0], 1)
        self.assertEqual(nums, list(range(1, len(nums) + 1)))


class TestMakeFileId(unittest.TestCase):
    def test_stable_and_length(self) -> None:
        a = bh.make_file_id("transcripts/episode_001_x.txt")
        b = bh.make_file_id("transcripts/episode_001_x.txt")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in a))

    def test_different_paths_differ(self) -> None:
        self.assertNotEqual(
            bh.make_file_id("a.txt"),
            bh.make_file_id("b.txt"),
        )


class TestTranscriptDiff(unittest.TestCase):
    def test_episode_one_when_present(self) -> None:
        root = Path(__file__).resolve().parents[3]
        bride = root / "projects" / "monuments" / "bride_of_charlie"
        raw_glob = bride / "transcripts"
        if not raw_glob.is_dir():
            self.skipTest("Bride transcripts/ missing")
        out = bh.transcript_diff_for_episode(bride, 1)
        if out.get("error"):
            self.skipTest(out["error"])
        self.assertIn("unified_diff", out)
        self.assertIn("raw_path", out)
        self.assertIn("enhanced_path", out)
        self.assertIsInstance(out.get("truncated"), bool)


class TestFindExistingVideo(unittest.TestCase):
    def test_finds_line_in_youtube_links(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "input").mkdir(parents=True)
            (p / "input" / "youtube_links.txt").write_text(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n",
                encoding="utf-8",
            )
            self.assertEqual(
                bh.find_existing_episode_for_video_id(p, "dQw4w9WgXcQ"),
                1,
            )
            self.assertIsNone(bh.find_existing_episode_for_video_id(p, "xxxxxxxxxxx"))


class TestSafePath(unittest.TestCase):
    def test_rejects_traversal(self) -> None:
        bride = Path("/tmp/bride-test").resolve()
        # Path need not exist; _safe_bride_path only checks logic
        self.assertIsNone(bh._safe_bride_path(bride, "../etc/passwd"))
        self.assertIsNone(bh._safe_bride_path(bride, "foo/../../bar"))


class TestTimestampToStartSeconds(unittest.TestCase):
    def test_parses_common_shapes(self) -> None:
        self.assertEqual(bh.timestamp_to_start_seconds("22:04–22:17"), 22 * 60 + 4)
        self.assertEqual(bh.timestamp_to_start_seconds("23:15"), 23 * 60 + 15)
        self.assertEqual(bh.timestamp_to_start_seconds("1:05:30"), 3600 + 5 * 60 + 30)
        self.assertIsNone(bh.timestamp_to_start_seconds(None))
        self.assertIsNone(bh.timestamp_to_start_seconds(""))


class TestResolveEntityDetail(unittest.TestCase):
    def test_claim_c1000_when_inscription_present(self) -> None:
        root = Path(__file__).resolve().parents[3]
        bride = root / "projects" / "monuments" / "bride_of_charlie"
        ins = bride / "inscription" / "episode_001.json"
        if not ins.is_file():
            self.skipTest("episode_001 inscription missing")
        out = bh.resolve_entity_detail(bride, root, "C-1000")
        self.assertTrue(out.get("found"))
        self.assertEqual(out.get("kind"), "claim")
        self.assertEqual(out.get("episode"), 1)
        self.assertIsNotNone(out.get("youtube"))


class TestResolveEntityDetailNodeEvidence(unittest.TestCase):
    def test_node_n1_resolves_evidence_follows_graph(self) -> None:
        """N-1 resolves; snippet claim ids match ``_gather_node_claim_evidence`` policy."""
        root = Path(__file__).resolve().parents[3]
        bride = root / "projects" / "monuments" / "bride_of_charlie"
        ins = bride / "inscription" / "episode_001.json"
        if not ins.is_file():
            self.skipTest("episode_001 inscription missing")
        out = bh.resolve_entity_detail(bride, root, "N-1", episode_hint=1)
        self.assertTrue(out.get("found"))
        self.assertEqual(out.get("kind"), "node")
        data = json.loads(ins.read_text(encoding="utf-8"))
        n1 = next(
            (n for n in (data.get("nodes") or []) if (n.get("@id") or n.get("ref")) == "N-1"),
            None,
        )
        self.assertIsNotNone(n1)
        assert n1 is not None
        gathered = bh._gather_node_claim_evidence(data, "N-1", n1)
        allowed = {row["claim_id"] for row in gathered if row.get("claim_id")}
        ids = {x.get("claim_id") for x in (out.get("transcript_snippets") or []) if x.get("claim_id")}
        self.assertEqual(ids, allowed)

    def test_node_n2_still_gets_c1014_via_related_nodes(self) -> None:
        root = Path(__file__).resolve().parents[3]
        bride = root / "projects" / "monuments" / "bride_of_charlie"
        if not (bride / "inscription" / "episode_001.json").is_file():
            self.skipTest("episode_001 inscription missing")
        out = bh.resolve_entity_detail(bride, root, "N-2", episode_hint=1)
        self.assertTrue(out.get("found"))
        ids = [x.get("claim_id") for x in (out.get("transcript_snippets") or [])]
        self.assertIn("C-1014", ids)

    def test_node_n19_claim_snippet_and_seek(self) -> None:
        """Nodes use related claims for transcript + timestamp (not bio-only description)."""
        root = Path(__file__).resolve().parents[3]
        bride = root / "projects" / "monuments" / "bride_of_charlie"
        ins = bride / "inscription" / "episode_004.json"
        if not ins.is_file():
            self.skipTest("episode_004 inscription missing")
        out = bh.resolve_entity_detail(bride, root, "N-19", episode_hint=4)
        self.assertTrue(out.get("found"))
        self.assertEqual(out.get("kind"), "node")
        sn = out.get("transcript_snippet") or ""
        self.assertIn("Lombardi", sn)
        self.assertEqual(out.get("start_seconds"), 36 * 60 + 45)
        self.assertIsInstance(out.get("transcript_snippets"), list)
        emb = (out.get("youtube") or {}).get("embed", "")
        self.assertIn("start=", emb)


class TestScreenNodeClaimConsistency(unittest.TestCase):
    def test_subject_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "inscription").mkdir()
            doc = {
                "nodes": [
                    {"@id": "N-1", "related_claims": ["C-1"]},
                ],
                "claims": [
                    {"@id": "C-1", "related_nodes": ["N-2"]},
                ],
            }
            (root / "inscription" / "episode_001.json").write_text(
                json.dumps(doc),
                encoding="utf-8",
            )
            r = bh.screen_node_claim_consistency(root, include_backlinks=False)
            self.assertFalse(r["ok"])
            self.assertEqual(r["error_count"], 1)
            self.assertEqual(r["issues"][0]["kind"], "node_claim_subject_mismatch")
            self.assertIn("remediation", r["issues"][0])
            self.assertFalse(r["handling_policy"]["server_auto_fixes"])

    def test_backlink_warning(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "inscription").mkdir()
            doc = {
                "nodes": [
                    {"@id": "N-1", "related_claims": []},
                ],
                "claims": [
                    {"@id": "C-1", "related_nodes": ["N-1"]},
                ],
            }
            (root / "inscription" / "episode_001.json").write_text(
                json.dumps(doc),
                encoding="utf-8",
            )
            r = bh.screen_node_claim_consistency(root, include_backlinks=True)
            kinds = [i["kind"] for i in r["issues"]]
            self.assertIn("claim_node_backlink_missing", kinds)
            self.assertEqual(r["warning_count"], 1)

    def test_symmetric_ok(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "inscription").mkdir()
            doc = {
                "nodes": [
                    {"@id": "N-1", "related_claims": ["C-1"]},
                    {"@id": "N-2", "related_claims": ["C-1"]},
                ],
                "claims": [
                    {"@id": "C-1", "related_nodes": ["N-1", "N-2"]},
                ],
            }
            (root / "inscription" / "episode_001.json").write_text(
                json.dumps(doc),
                encoding="utf-8",
            )
            r = bh.screen_node_claim_consistency(root, include_backlinks=True)
            self.assertTrue(r["ok"])
            self.assertEqual(r["issue_count"], 0)


class TestMemeHub(unittest.TestCase):
    def test_flatten_inscription_includes_memes(self) -> None:
        doc = {
            "memes": [
                {"@id": "M-1", "ref": "M-1", "canonical_term": "Test", "occurrences": []},
            ],
        }
        flat = bh._flatten_inscription_entities(doc)
        self.assertEqual(flat.get("memes"), ["M-1"])

    def test_find_entity_meme(self) -> None:
        doc = {
            "memes": [
                {"@id": "M-2", "canonical_term": "Y", "type": "meme", "occurrences": []},
            ],
        }
        hit = bh.find_entity_in_inscription_data(doc, "M-2")
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit[0], "meme")
        self.assertEqual(hit[1].get("canonical_term"), "Y")

    def test_resolve_m1_when_episode_one_inscription_present(self) -> None:
        root = Path(__file__).resolve().parents[3]
        bride = root / "projects" / "monuments" / "bride_of_charlie"
        ins = bride / "inscription" / "episode_001.json"
        if not ins.is_file():
            self.skipTest("episode_001 inscription missing")
        out = bh.resolve_entity_detail(bride, root, "M-1", episode_hint=1)
        self.assertTrue(out.get("found"))
        self.assertEqual(out.get("kind"), "meme")
        self.assertEqual(out.get("episode"), 1)
        rec = out.get("record") or {}
        self.assertEqual(rec.get("canonical_term"), "Grieving Widow")
        rel = out.get("related") or {}
        self.assertIn("N-2", rel.get("nodes") or [])


class TestGlobalRowSortKey(unittest.TestCase):
    def test_numeric_id_before_episode(self) -> None:
        """N-11 (later episode) sorts before N-1000 (earlier episode)."""
        a = {"id": "N-1000", "episode": 1}
        b = {"id": "N-11", "episode": 2}
        self.assertLess(bh.global_row_sort_key(b), bh.global_row_sort_key(a))

    def test_sub_id_after_base(self) -> None:
        self.assertLess(
            bh.global_row_sort_key({"id": "A-1000", "episode": 1}),
            bh.global_row_sort_key({"id": "A-1000.1", "episode": 1}),
        )


if __name__ == "__main__":
    unittest.main()
