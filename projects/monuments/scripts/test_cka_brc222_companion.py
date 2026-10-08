#!/usr/bin/env python3
"""Unit tests for CKA BRC-222 companion builder."""

from __future__ import annotations

import ast
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import cka_brc222_companion as mod  # noqa: E402

VOCAB_PATH = REPO_ROOT / "projects" / "monuments" / "cka" / "vendor" / "brc222" / "vocabulary.json"
FIXTURE_DIR = SCRIPT_DIR / "fixtures" / "cka_brc222"


class TestVocabLoad(unittest.TestCase):
    def test_load_version_2(self):
        v = mod.Vocabulary(VOCAB_PATH)
        self.assertEqual(v.version, "2.0.0")
        self.assertEqual(v.date_modified, "2026-10-07")
        for name in mod.LEDGER_LOOKUP_KEYS.values():
            self.assertEqual(v.require(name), name)

    def test_require_missing_fails_loudly(self):
        v = mod.Vocabulary(VOCAB_PATH)
        with self.assertRaises(KeyError):
            v.require("notARealRelationshipTermXYZ")

    def test_reject_retired(self):
        v = mod.Vocabulary(VOCAB_PATH)
        for retired in mod.RETIRED_TERMS:
            with self.assertRaises(ValueError):
                v.require(retired)


class TestNoHardcodedEmit(unittest.TestCase):
    """Emitter source must not hardcode relationship names as emitted terms."""

    def test_no_retired_string_literals(self):
        src = (SCRIPT_DIR / "cka_brc222_companion.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        retired = set(mod.RETIRED_TERMS)
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in retired:
                    found.append(node.value)
        # RETIRED_TERMS frozenset definition itself contains the names; allow only
        # inside the assignment to RETIRED_TERMS.
        # Re-scan with context: fail if retired appears outside RETIRED_TERMS assign.
        found_outside = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if "RETIRED_TERMS" in targets:
                    continue
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in retired:
                    # Check if this constant is under RETIRED_TERMS assign via parent walk
                    found_outside.append(node.value)
        # Simpler string-scan: only RETIRED_TERMS block may list them.
        lines = src.splitlines()
        in_retired_block = False
        bad = []
        for i, line in enumerate(lines, 1):
            if line.startswith("RETIRED_TERMS"):
                in_retired_block = True
            if in_retired_block and line.strip() == "}":
                in_retired_block = False
                continue
            if in_retired_block:
                continue
            for r in retired:
                if f'"{r}"' in line or f"'{r}'" in line:
                    bad.append((i, r, line.strip()))
        self.assertEqual(bad, [], f"retired terms outside RETIRED_TERMS deny-list: {bad}")

    def test_relationship_literals_only_as_lookup_keys(self):
        """Active vocab names may appear only in LEDGER_LOOKUP_KEYS values / require paths."""
        v = mod.Vocabulary(VOCAB_PATH)
        allowed_names = set(v.names())
        src = (SCRIPT_DIR / "cka_brc222_companion.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        # Collect string constants that equal a vocab relationship name.
        # Allowed contexts: LEDGER_LOOKUP_KEYS dict values; arguments to require().
        allowed_nodes: set[int] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == "LEDGER_LOOKUP_KEYS":
                        for n in ast.walk(node.value):
                            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                                if n.value in allowed_names:
                                    allowed_nodes.add(id(n))

            if isinstance(node, ast.Call):
                func = node.func
                is_require = (
                    isinstance(func, ast.Attribute) and func.attr == "require"
                ) or (isinstance(func, ast.Name) and func.id == "require")
                if is_require and node.args:
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                        allowed_nodes.add(id(arg0))

        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in allowed_names and id(node) not in allowed_nodes:
                    bad.append(node.value)
        self.assertEqual(
            bad,
            [],
            "relationship name string literals must only appear as LEDGER_LOOKUP_KEYS "
            f"values or require() args; found: {bad}",
        )

    def test_emitted_relationship_comes_from_vocab_object(self):
        v = mod.Vocabulary(VOCAB_PATH)
        # Build a tiny in-memory corpus
        claims = {
            "C-1": mod.ClaimRec(
                claim_id="C-1",
                label="Test claim",
                body="Host states P.",
                episode=1,
                anchored_artifacts=["A-1.1"],
                contradicts=["C-0"],
                supports=["C-0"],
            )
        }
        artifacts = {
            "A-1.1": mod.ArtifactRec(artifact_id="A-1.1", label="Art", episode=1)
        }
        episode_ids = {1: "cka:episode:1"}
        result = mod.build_package(v, claims, artifacts, episode_ids)
        vocab_names = v.names()
        for edge in result.edges:
            self.assertIn(edge.relationship, vocab_names)
            self.assertNotIn(edge.relationship, mod.RETIRED_TERMS)
            # Must equal vocab.require of itself (round-trip)
            self.assertEqual(v.require(edge.relationship), edge.relationship)
            self.assertNotIn("direction", edge.to_bridge())


class TestGoldenSmoke(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cka_brc222_"))
        self.cka = self.tmp / "cka"
        (self.cka / "drafts").mkdir(parents=True)
        (self.cka / "inscription").mkdir(parents=True)
        draft = """## 1. Meta-Data

- **Episode**: 1
- **CKA seq**: 1

## 3. Artifact Register

**A-100.1** Clip of host reading letter

## 5. Claim Register

**C-100** Host asserts letter expressed concern

Claim Timestamp: 00:01:00
Claim: Host asserts the letter expressed concerns, building on earlier framing with further detail.
Anchored Artifacts: A-100.1
Revises: C-99
Contradicts: C-98
Supports: C-97

**C-101** Softening caveat on prior claim

Claim Timestamp: 00:02:00
Claim: Host softens and qualifies the earlier claim with a caveat that it holds only partially.
Revises: C-100
Qualifies: C-100
"""
        (self.cka / "drafts" / "episode_001.md").write_text(draft, encoding="utf-8")
        # Minimal inscription for same episode
        ins = {
            "meta": {"episode": 1},
            "claims": [
                {
                    "ref": "C-100",
                    "label": "Host asserts letter expressed concern",
                    "claim": "Host asserts the letter expressed concerns.",
                    "anchored_artifacts": ["A-100.1"],
                    "revises_claim_refs": ["C-99"],
                    "contradicts_claim_refs": ["C-98"],
                    "supports_claim_refs": ["C-97"],
                }
            ],
            "artifacts": [
                {
                    "ref": "A-100",
                    "bundle_name": "Letter bundle",
                    "sub_items": [{"ref": "A-100.1", "label": "Clip"}],
                }
            ],
        }
        (self.cka / "inscription" / "episode_001.json").write_text(
            json.dumps(ins), encoding="utf-8"
        )
        self.out = self.tmp / "out"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_golden_smoke_build(self):
        v = mod.Vocabulary(VOCAB_PATH)
        claims, artifacts, episode_ids = mod.load_cka_corpus(self.cka)
        self.assertIn("C-100", claims)
        self.assertIn("C-101", claims)
        self.assertTrue(claims["C-100"].revises)
        result = mod.build_package(v, claims, artifacts, episode_ids)
        mod.write_package(self.out, result, v, self.cka)

        package = json.loads((self.out / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["vocabulary"]["version"], "2.0.0")
        self.assertTrue(package["bridges"])
        rels = {b["relationship"] for b in package["bridges"]}
        # All emitted rels in vocab
        for r in rels:
            self.assertTrue(v.has(r))
            self.assertNotIn(r, mod.RETIRED_TERMS)
        # Expect supported-by, corroborates path, contradicts, member-of, revises candidates
        term_supported = v.require(mod.LEDGER_LOOKUP_KEYS["artifact_backs_claim"])
        term_corr = v.require(mod.LEDGER_LOOKUP_KEYS["independent_or_later_confirms"])
        term_contra = v.require(mod.LEDGER_LOOKUP_KEYS["airing_opposes"])
        term_member = v.require(mod.LEDGER_LOOKUP_KEYS["belongs_to_collection"])
        term_qual = v.require(mod.LEDGER_LOOKUP_KEYS["revises_softening"])
        term_ext = v.require(mod.LEDGER_LOOKUP_KEYS["revises_builds_on"])
        self.assertIn(term_supported, rels)
        self.assertIn(term_corr, rels)
        self.assertIn(term_contra, rels)
        self.assertIn(term_member, rels)
        self.assertIn(term_qual, rels)
        self.assertIn(term_ext, rels)

        # No direction field
        for b in package["bridges"]:
            self.assertNotIn("direction", b)

        # CSV has both candidates for Revises edges
        with (self.out / "revises-split-candidates.csv").open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(rows)
        proposed = {r["proposed_term"] for r in rows}
        self.assertIn(term_qual, proposed)
        self.assertIn(term_ext, proposed)
        # C-101 softening should prefer qualify as primary
        c101_primary = [
            r
            for r in rows
            if r["claim_id"] == "C-101"
            and r["is_heuristic_primary"] == "yes"
            and r["source"] == "revises_ledger"
        ]
        self.assertTrue(c101_primary)
        self.assertEqual(c101_primary[0]["proposed_term"], term_qual)

    def test_revises_emits_one_bridge_and_honours_rulings(self):
        """PR 60 Wave 2.1: one bridge per Revises edge; a Transit ruling pins the term."""
        v = mod.Vocabulary(VOCAB_PATH)
        term_qual = v.require(mod.LEDGER_LOOKUP_KEYS["revises_softening"])
        term_ext = v.require(mod.LEDGER_LOOKUP_KEYS["revises_builds_on"])
        claims, artifacts, episode_ids = mod.load_cka_corpus(self.cka)

        def revises_rels(result):
            return sorted(
                (e.source, e.target, e.relationship)
                for e in result.edges
                if e.relationship in (term_qual, term_ext) and e.source.startswith("C-") and e.target.startswith("C-")
            )

        plain = mod.build_package(v, claims, artifacts, episode_ids)
        # C-100 (extend cues) -> extends only; C-101 (qualify cues) -> isQualifiedBy only.
        self.assertEqual(revises_rels(plain), [("C-100", "C-101", term_qual), ("C-100", "C-99", term_ext)])
        ruled = mod.build_package(v, claims, artifacts, episode_ids, revises_rulings={"C-100": "revises_softening"})
        self.assertEqual(revises_rels(ruled), [("C-100", "C-101", term_qual), ("C-99", "C-100", term_qual)])

    def test_cka_rulings_file_pins_corrections_to_qualified_by(self):
        rulings = mod.load_revises_rulings(mod.DEFAULT_CKA_ROOT)
        for cid in ("C-3737", "C-3738", "C-3739", "C-3740"):
            self.assertEqual(rulings.get(cid), "revises_softening")

    def test_hardcode_guard_fails_on_synthetic_bad_source(self):
        """Sanity: scanner would catch a direct relationship literal emit."""
        bad_src = 'x = "isSupportedBy"\n'
        tree = ast.parse(bad_src)
        v = mod.Vocabulary(VOCAB_PATH)
        names = v.names()
        found = [
            n.value
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in names
        ]
        self.assertIn("isSupportedBy", found)


class TestClassifyRevises(unittest.TestCase):
    def test_qualify_vs_extend(self):
        soft = mod.ClaimRec(
            claim_id="C-2",
            label="Caveat",
            body="Host softens and qualifies the prior with a caveat.",
            episode=1,
        )
        key, _, conf, _ = mod.classify_revises(soft, "C-1")
        self.assertEqual(key, "revises_softening")
        self.assertGreaterEqual(conf, 0.55)

        ext = mod.ClaimRec(
            claim_id="C-3",
            label="More detail",
            body="Host builds on the prior and adds detail, elaborating further.",
            episode=1,
        )
        key2, _, _, _ = mod.classify_revises(ext, "C-1")
        self.assertEqual(key2, "revises_builds_on")



class TestDashRule(unittest.TestCase):
    """Dash rule (Daveed, 8 Oct 2026): no dash is flattened to a hyphen in staged output."""

    EN = "\u2013"
    EM = "\u2014"

    def _build(self, claims, artifacts):
        v = mod.Vocabulary(VOCAB_PATH)
        return mod.build_package(v, claims, artifacts, {1: "cka:episode:1"})

    def test_claim_and_artifact_labels_pass_through_exactly(self):
        claim_label = f"Phil Lyman's vehicle 10{self.EN}19 minutes before {self.EN} per TMZ"
        art_label = f"Bowyer SD card removal account {self.EN} law enforcement instruction"
        claims = {"C-1": mod.ClaimRec(claim_id="C-1", label=claim_label, body="b", episode=1, anchored_artifacts=["A-1.1"])}
        artifacts = {"A-1.1": mod.ArtifactRec(artifact_id="A-1.1", label=art_label, episode=1)}
        res = self._build(claims, artifacts)
        labels = {n["identifier"]: n["label"] for n in res.nodes}
        self.assertEqual(labels["C-1"], claim_label)
        self.assertEqual(labels["A-1.1"], art_label)

    def test_quoted_em_dash_is_not_rewritten(self):
        # A quote-derived label keeps whatever dash the source stored, em dash included.
        quoted = f'Headline: "Not now {self.EM} not ever"'
        artifacts = {"A-1.1": mod.ArtifactRec(artifact_id="A-1.1", label=quoted, episode=1)}
        res = self._build({}, artifacts)
        labels = {n["identifier"]: n["label"] for n in res.nodes}
        self.assertEqual(labels["A-1.1"], quoted)

    def test_revises_evidence_snippet_passes_through(self):
        body = f"Host qualifies the prior claim {self.EN} a caveat, softening it."
        claims = {
            "C-1": mod.ClaimRec(claim_id="C-1", label="Prior", body="p", episode=1),
            "C-2": mod.ClaimRec(claim_id="C-2", label="Later", body=body, episode=1, revises=["C-1"]),
        }
        res = self._build(claims, {})
        snippets = [r["evidence_snippet"] for r in res.revises_candidates]
        self.assertTrue(snippets)
        for s in snippets:
            self.assertEqual(s, body)

    def test_prose_dashes_em_becomes_en_and_never_hyphen(self):
        self.assertEqual(mod._prose_dashes(f"a {self.EM} b"), f"a {self.EN} b")
        self.assertEqual(mod._prose_dashes(f"a {self.EN} b"), f"a {self.EN} b")
        self.assertEqual(mod._prose_dashes(""), "")
        edge = mod.Edge(source="C-1", target="C-2", relationship="isSupportedBy", explanation=f"x {self.EM} y")
        self.assertEqual(edge.to_bridge()["explanation"], f"x {self.EN} y")

    def test_no_ascii_dash_flattening_left_in_builder(self):
        src = (SCRIPT_DIR / "cka_brc222_companion.py").read_text(encoding="utf-8")
        self.assertNotIn("_ascii_dashes", src)
        self.assertNotIn("\u2014", src.replace("\\u2014", ""))

    def test_staged_package_labels_match_source_dashes(self):
        """Committed package: no label carries an em dash and none was flattened from a dash."""
        pkg = json.loads((REPO_ROOT / "projects/monuments/cka/companion/brc222-2.0.0/package.json").read_text(encoding="utf-8"))
        claims, artifacts, _ = mod.load_cka_corpus(mod.DEFAULT_CKA_ROOT)
        src = {**{k: c.label for k, c in claims.items()}, **{k: a.label for k, a in artifacts.items()}}
        for n in pkg["nodes"]:
            if n["identifier"] in src:
                self.assertEqual(n["label"], src[n["identifier"]], n["identifier"])


if __name__ == "__main__":
    unittest.main()
