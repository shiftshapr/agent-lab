"""Regression tests for the CKA supplement integration tools (bugs seen in batches 2-7)."""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1] / "cka"
sys.path.insert(0, str(CKA / "scripts"))
import supplement_integrate as si  # noqa: E402

SUPPLEMENT = """## 3. Artifact Register

**A-L1** Clip

## 6. Meme Register

**M-12** (meme) DIA

### Occurrence 1

Video Timestamp: 00:01:00
Speaker: N-3
Quote: email us more tips

### Occurrence 2

Video Timestamp: 00:02:00
Speaker: N-3
Quote: more tips please

---

## 7. Coverage Notes
"""


def test_section_keeps_subheadings():
    """Batch 2-3 bug: a register section ended at the first ### heading, so meme occurrences were dropped."""
    sec = si.section(SUPPLEMENT, "meme")
    assert len(re.findall(r"^### Occurrence", sec, re.M)) == 2
    assert "Coverage Notes" not in sec


def test_uppercase_register_headers_match():
    """Batch 4-5 bug: '# IV. NODE REGISTER' was not recognised, so rows were appended in a new section."""
    draft = "# III. ARTIFACT REGISTER\n\n**A-1** x\n\n# IV. NODE REGISTER\n\n**N-1** Charlie Kirk\n\n# V. CLAIM REGISTER\n"
    out = si.insert_at_section_end(draft, "node", "**N-2** Erika Kirk", "## 4. Node Register")
    assert out.count("NODE REGISTER") == 1 and "## 4. Node Register" not in out
    assert out.index("**N-2**") < out.index("# V. CLAIM REGISTER")


def test_insert_memes_skips_exact_repeats():
    """Rerunning the meme insertion (backfill) must not duplicate occurrences."""
    draft = "## 6. Meme Register\n\n"
    sec = si.section(SUPPLEMENT, "meme")
    once = si.insert_memes(draft, sec, lambda mid: {"canonical_term": "(meme) DIA"})
    twice = si.insert_memes(once, sec, lambda mid: {"canonical_term": "(meme) DIA"})
    assert once.count("### Occurrence") == 2
    assert twice == once


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, CKA / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_verify_batch_counts():
    vb = _load("verify_batch", "scripts/supplement/verify_batch.py")
    assert vb.staged_counts(SUPPLEMENT) == (0, 0, 2)
    assert vb.draft_counts("**C-1** a\n**A-2.1** b\n### Occurrence 1\n") == (1, 1, 1)


def test_name_corrections_config_is_well_formed():
    """Every rule compiles; scoped rules name episodes as integers; no rule is listed twice."""
    rules = json.loads((CKA / "config" / "transcript_name_corrections.json").read_text(encoding="utf-8"))["corrections"]
    seen = set()
    for r in rules:
        assert len(r) in (2, 3)
        re.compile(r[0])
        if len(r) == 3:
            assert r[2] and all(isinstance(e, int) for e in r[2])
        key = (r[0], tuple(r[2]) if len(r) == 3 else None)
        assert key not in seen, r[0]
        seen.add(key)


def test_name_corrections_are_applied():
    """The archive carries no text a correction rule would still change (dry run reports zero)."""
    out = subprocess.run([sys.executable, str(CKA / "scripts" / "apply_name_corrections.py"), "--dry-run"],
                         capture_output=True, text=True, check=True).stdout
    assert out.strip() == "transcripts: 0, drafts: 0, inscriptions: 0, aliases: 0", out
