#!/usr/bin/env python3
"""Smoke tests for DIA preflight (run from repo root)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = ROOT / "projects" / "monuments" / "scripts" / "dia_preflight.py"
sys.path.insert(0, str(PREFLIGHT.parent))

import dia_preflight as dp  # noqa: E402


def test_self_test_exits_zero():
    proc = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_bride_of_charlie_main_tip_passes():
    proc = subprocess.run(
        [sys.executable, str(PREFLIGHT), "--monument", "bride_of_charlie"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "RESULT: PASS" in proc.stdout


# ---------------------------------------------------------------------------
# Wave 1 gates (unit tests on synthetic inputs)
# ---------------------------------------------------------------------------


def _episode(tmp_path: Path, text: str, ep: int = 1) -> list[tuple[int, str, Path, str]]:
    drafts = tmp_path / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    path = drafts / f"episode_{ep:03d}.md"
    path.write_text(text, encoding="utf-8")
    return [(ep, path.name, path, text)]


def _checks(report: dp.PreflightReport, sev: str = "P1") -> list[str]:
    return [f.check for f in report.findings if f.severity == sev]


@pytest.mark.parametrize("dash", ["\u2013", "\u2014"], ids=["en_dash", "legacy_em_dash"])
def test_person_like_topic_flags_topic_band_person_and_honorific(dash):
    content = f"## 4. Node Register\n\n**N-1009** Charlie Kirk {dash} referenced throughout.\n\n**N-2349** Father Ripperger\n\n**N-1018** Eileen Marx\n"
    intro = dp.first_introduction_meta(dp.collect_register_entries([(1, "episode_001.md", Path("x"), content)]))
    canonical = {
        "N-1": {"canonical_name": "Charlie Kirk", "type": "person"},
        "N-14": {"canonical_name": "Victor Marx's son", "type": "person"},
    }
    report = dp.PreflightReport("t", "t")
    dp.check_person_like_topic(report, intro, canonical)
    flagged = {f.location for f in report.findings if f.check == "person_like_topic"}
    assert flagged == {"N-1009", "N-2349", "N-1018"}


@pytest.mark.parametrize("dash", ["\u2013", "\u2014"], ids=["en_dash", "legacy_em_dash"])
def test_person_like_topic_ignores_topics_about_people(dash):
    content = (
        f"## 4. Node Register\n\n**N-2183** Officer Bagley {dash} Sex Crimes Unit Background\n\n"
        "**N-1391** Charlie Kirk's Pre-Death Messages\n\n**N-1135** Daily Mail\n\n**N-1092** The Hamptons\n"
    )
    intro = dp.first_introduction_meta(dp.collect_register_entries([(1, "episode_001.md", Path("x"), content)]))
    canonical = {"N-1": {"canonical_name": "Charlie Kirk", "type": "person"}}
    report = dp.PreflightReport("t", "t")
    dp.check_person_like_topic(report, intro, canonical)
    assert report.findings == []


def test_person_like_topic_flags_canonical_person_type_in_topic_band():
    report = dp.PreflightReport("t", "t")
    dp.check_person_like_topic(report, {}, {"N-24": {"canonical_name": "x", "type": "person"}, "N-1500": {"canonical_name": "Someone", "type": "person"}})
    assert [f.location for f in report.findings] == ["N-1500"]


CLAIM_DRAFT = """## 4. Node Register

**N-1** Alice Smith

**N-2** Bob Jones

**N-3** Host Person

## 5. Claim Register

**C-1** Alice speaks on the PBD show

Claim Timestamp: 00:00:10
Claim: Alice Smith describes the event.
Mentions: {mentions}

---
"""


def _grounding_report(tmp_path: Path, mentions: str, canonical: dict, transcript: str, gates: dict | None = None):
    eps = _episode(tmp_path, CLAIM_DRAFT.format(mentions=mentions))
    (tmp_path / "transcripts_corrected").mkdir(exist_ok=True)
    (tmp_path / "transcripts_corrected" / "episode_001_vid.txt").write_text(transcript, encoding="utf-8")
    if gates is not None:
        (tmp_path / "config").mkdir(exist_ok=True)
        (tmp_path / "config" / "preflight_gates.json").write_text(json.dumps(gates), encoding="utf-8")
    intro = dp.first_introduction_meta(dp.collect_register_entries(eps))
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_mention_grounding(report, tmp_path, eps, intro, canonical)
    return report


CANON = {
    "N-1": {"canonical_name": "Alice Smith", "type": "person"},
    "N-2": {"canonical_name": "Bob Jones", "type": "person", "aliases": []},
    "N-3": {"canonical_name": "Host Person", "type": "person"},
    "N-4": {"canonical_name": "Patrick Bet-David", "type": "person", "aliases": ["PBD"]},
}


def test_mention_grounding_flags_name_absent_from_claim_and_transcript(tmp_path):
    report = _grounding_report(tmp_path, "N-1, N-2", CANON, "[00:00:05] Alice Smith talks.")
    assert [f.location for f in report.findings] == ["C-1:N-2"]
    assert _checks(report) == ["mention_grounding"]


def test_mention_grounding_accepts_transcript_surname_alias_and_acronym(tmp_path):
    canon = {**CANON, "N-2": {"canonical_name": "Bob Jones", "type": "person", "aliases": ["Bobby Jonez"]}}
    report = _grounding_report(tmp_path, "N-1, N-2, N-4", canon, "[00:09:00] and later Jonez said hello.")
    assert report.findings == []


def test_mention_grounding_respects_exempt_and_reviewed(tmp_path):
    gates = {"mention_grounding": {"exempt_ids": ["N-3"], "reviewed": [{"claim": "C-1", "node": "N-2", "reason": "her husband"}]}}
    report = _grounding_report(tmp_path, "N-1, N-2, N-3", CANON, "[00:00:05] Alice Smith talks.", gates)
    assert report.findings == []


TS_DRAFT = """- **YouTube id**: vid

## 5. Claim Register

**C-1** In range

Claim Timestamp: 00:01:30
Claim: ok

---

**C-2** Past end

Claim Timestamp: 00:05:00
Claim: late

---
"""


def test_claim_ts_past_end_uses_youtube_duration(tmp_path):
    eps = _episode(tmp_path, TS_DRAFT)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "yt_durations.json").write_text(json.dumps({"by_youtube_id": {"vid": 180}}), encoding="utf-8")
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_claim_ts_past_end(report, tmp_path, eps)
    assert [f.location for f in report.findings] == ["C-2"]


def test_claim_ts_past_end_falls_back_to_last_marker_and_skips_without_durations(tmp_path):
    eps = _episode(tmp_path, TS_DRAFT)
    (tmp_path / "transcripts_corrected").mkdir()
    (tmp_path / "transcripts_corrected" / "episode_001_vid.txt").write_text("[00:00:01] a [00:02:00] b", encoding="utf-8")
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_claim_ts_past_end(report, tmp_path, eps)
    assert report.findings == []  # no yt_durations.json: gate opts out
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "yt_durations.json").write_text(json.dumps({"by_youtube_id": {}}), encoding="utf-8")
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_claim_ts_past_end(report, tmp_path, eps)
    assert [f.location for f in report.findings] == ["C-2"]


def test_claims_missing_from_drafts(tmp_path):
    eps = _episode(tmp_path, TS_DRAFT)
    (tmp_path / "inscription").mkdir()
    (tmp_path / "inscription" / "episode_001.json").write_text(
        json.dumps({"claims": [{"@id": "C-1"}, {"@id": "C-2"}, {"@id": "C-77"}]}), encoding="utf-8"
    )
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_claims_missing_from_drafts(report, tmp_path, eps)
    assert [f.location for f in report.findings] == ["C-77"]


def test_duplicate_claim_headers_including_residue_headers(tmp_path):
    text = TS_DRAFT + "\n**C-1 / C-9** residue header\n\nClaim: junk\n"
    eps = _episode(tmp_path, text)
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_duplicate_claim_headers(report, eps)
    assert [f.location for f in report.findings] == ["C-1"]
    assert _checks(report) == ["duplicate_claim_header"]


def test_tombstone_collision():
    report = dp.PreflightReport("t", "t")
    dp.check_tombstone_collision(
        report,
        {"N-88": {"canonical_name": "PBD", "retired_ids": ["N-452", "N-999"]}, "N-452": {"canonical_name": "Ali Breland"}},
    )
    assert [f.location for f in report.findings] == ["N-452"]


def test_wave1_fixture_trips_every_gate(tmp_path):
    root = tmp_path / "wave1_fixture"
    dp.build_wave1_fixture(root)
    report = dp._run_fixture("test_mon_w1_pytest", root, skip_inscription=False)
    p1 = set(_checks(report))
    assert set(dp.WAVE1_CHECKS) <= p1
    assert set(dp.WAVE1_P0_CHECKS) <= set(_checks(report, "P0"))
    locs = {f.location for f in report.findings if f.check == "mention_grounding"}
    assert set(dp.WAVE1_FIXTURE_LOCATIONS) <= locs


# --- .md transcripts and windowed grounding ---------------------------------

WIN_DRAFT = """## 4. Node Register

**N-1** Alice Smith

**N-2** Bob Jones

## 5. Claim Register

**C-1** Alice speaks

Claim Timestamp: {ts}
Claim: Alice Smith describes the event.
Mentions: N-1, N-2

---
"""

WIN_TRANSCRIPT = "[00:00:05] Alice Smith talks. [00:01:00] Other topics. [00:05:00] Bob Jones arrives. [00:06:00] Bye."
WIN_GATES = {"mention_grounding": {"window_seconds": 60}}


def _win_report(tmp_path: Path, ts: str, transcript: str = WIN_TRANSCRIPT, gates: dict | None = None, ext: str = ".txt", ep: int = 1):
    eps = _episode(tmp_path, WIN_DRAFT.format(ts=ts), ep=ep)
    tdir = tmp_path / "transcripts_corrected"
    tdir.mkdir(exist_ok=True)
    (tdir / f"episode_{ep:03d}_vid{ext}").write_text(transcript, encoding="utf-8")
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "preflight_gates.json").write_text(json.dumps(gates if gates is not None else WIN_GATES), encoding="utf-8")
    intro = dp.first_introduction_meta(dp.collect_register_entries(eps))
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_mention_grounding(report, tmp_path, eps, intro, CANON)
    return report


def test_find_transcript_reads_md(tmp_path):
    report = _win_report(tmp_path, "00:04:50", ext=".md")
    assert dp.find_transcript(tmp_path, 1).suffix == ".md"
    assert report.findings == []
    report = _win_report(tmp_path / "b", "00:00:10", ext=".md")
    assert [f.location for f in report.findings] == ["C-1:N-2"]


def test_windowed_grounding_fails_outside_window(tmp_path):
    report = _win_report(tmp_path, "00:00:10")
    assert [f.location for f in report.findings] == ["C-1:N-2"]
    assert "within +-60s" in report.findings[0].message


def test_windowed_grounding_passes_inside_window(tmp_path):
    assert _win_report(tmp_path, "00:04:30").findings == []


def test_windowed_grounding_early_episodes_use_wider_window(tmp_path):
    gates = {"mention_grounding": {"window_seconds": 60, "window_seconds_early": 300, "early_max_episode": 10}}
    assert _win_report(tmp_path, "00:01:30", gates=gates, ep=5).findings == []
    assert [f.location for f in _win_report(tmp_path / "b", "00:01:30", gates=gates, ep=11).findings] == ["C-1:N-2"]


def test_windowed_grounding_placeholder_timestamp_falls_back_to_episode(tmp_path):
    assert _win_report(tmp_path, "00:00:00\u201300:00:01").findings == []


def test_windowed_grounding_first_name_ok(tmp_path):
    transcript = "[00:00:05] Alice Smith talks and Bob waves. [00:01:00] Bye."
    report = _win_report(tmp_path, "00:00:10", transcript=transcript)
    assert [f.location for f in report.findings] == ["C-1:N-2"]
    gates = {"mention_grounding": {"window_seconds": 60, "first_name_ok": ["N-2"]}}
    assert _win_report(tmp_path / "b", "00:00:10", transcript=transcript, gates=gates).findings == []


# --- name_annotation_mismatch --------------------------------------------------


def test_name_annotation_mismatch_flags_wrong_person_only():
    content = (
        "## 4. Node Register\n\n**N-1** Alice Smith\n\n**N-2** Bob Jones\n\n"
        "## 5. Claim Register\n\nReused: N-1 (Alice Smith), N-2 (Bobby Jones), N-1 (verbal reference)\n"
        "Context: N-2 (Alice Smith) spoke.\n"
    )
    eps = [(1, "episode_001.md", Path("x"), content)]
    register = dp.collect_register_entries(eps)
    report = dp.PreflightReport("t", "t")
    dp.check_name_annotation_mismatch(report, eps, register, {})
    assert [f.location for f in report.findings] == ["episode_001.md:10:N-2"]
    assert _checks(report) == ["name_annotation_mismatch"]


# --- hole_mint_order ----------------------------------------------------------------


def test_annotation_person_requires_surname_match():
    m = dp.annotation_name_matches
    # Wrong person who only shares a first name: rejected for persons.
    assert not m("Blake Wynn", ["Blake Neff"], person=True)
    assert not m("Josh Hawley", ["Josh Hammer"], person=True)
    assert not m("Andrew Tate", ["Andrew Kolvet"], person=True)
    assert not m("Charlie Skyler", ["Charlie Kirk"], person=True)
    # Single-token, nickname and title references stay accepted.
    assert m("Charlie", ["Charlie Kirk"], person=True)
    assert m("Don Jr", ["Donald Trump Jr.", "Don Jr"], person=True)
    assert m("Governor Cox", ["Spencer Cox"], person=True)
    assert m("Michael Knowles", ["Michael Knowles", "Michael Nolles"], person=True)
    # Topics keep the shared-word rule.
    assert m("Blake Wynn", ["Blake Neff"], person=False)
    assert m("Butler rally timeline", ["Butler Rally Security"], person=False)


def test_name_annotation_mismatch_flags_first_name_only_person_match():
    content = "## 5. Claim Register\n\n**C-1** T\n\nMentions: N-224 (Blake Wynn), N-1 (Charlie)\n"
    eps = [(1, "episode_001.md", Path("x"), content)]
    canonical = {"N-224": {"canonical_name": "Blake Neff", "type": "person", "aliases": []},
                 "N-1": {"canonical_name": "Charlie Kirk", "type": "person", "aliases": []}}
    report = dp.PreflightReport("t", "x")
    dp.check_name_annotation_mismatch(report, eps, [], canonical)
    assert [f.location for f in report.findings] == ["episode_001.md:5:N-224"]


def test_annotation_single_word_alias_needs_surname():
    """N1: a bare first-name alias must not ground a multi-word person label."""
    m = dp.annotation_name_matches
    assert not m("Blake Wynn", ["Blake Neff", "Blake"], person=True)
    assert not m("Lance Smith", ["Lance Twiggs", "Lance"], person=True)
    assert not m("Mark Levin", ["Mark Herman", "Mark"], person=True)
    # A one-word alias that is the surname still grounds a titled reference.
    assert m("Governor Cox", ["Spencer Cox", "Cox"], person=True)
    # One-word labels still match the first-name alias.
    assert m("Blake", ["Blake Neff", "Blake"], person=True)
    assert m("Blake Neff", ["Blake Neff", "Blake"], person=True)


def test_name_annotation_mismatch_flags_first_name_alias_person_match():
    content = "## 5. Claim Register\n\n**C-1** T\n\nMentions: N-224 (Blake Wynn), N-224 (Blake)\n"
    eps = [(1, "episode_001.md", Path("x"), content)]
    canonical = {"N-224": {"canonical_name": "Blake Neff", "type": "person", "aliases": ["Blake", "Blake Nef"]}}
    report = dp.PreflightReport("t", "x")
    dp.check_name_annotation_mismatch(report, eps, [], canonical)
    assert [f.location for f in report.findings] == ["episode_001.md:5:N-224"]
    assert "Blake Wynn" in report.findings[0].message


def _hole_eps(ep1_ledger: str, ep2_ledger: str = "", ep2_register: str = "") -> list[tuple[int, str, Path, str]]:
    def draft(ledger: str, register: str) -> str:
        return f"## 1. Meta-Data\n\n- **Episode Ledger Summary**:\n{ledger}\n## 4. Node Register\n\n{register}\n## 5. Claim Register\n"
    reg1 = "".join(f"**N-{n}** Person {n}\n\nNode Type: Person\n\n" for n in (1, 2, 3, 4))
    eps = [(1, "episode_001.md", Path("x"), draft(ep1_ledger, reg1))]
    if ep2_ledger or ep2_register:
        eps.append((2, "episode_002.md", Path("y"), draft(ep2_ledger, ep2_register)))
    return eps


def _hole_report(tmp_path: Path, eps) -> dp.PreflightReport:
    intro = dp.first_introduction_meta(dp.collect_register_entries(eps))
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_hole_minted(report, tmp_path, eps, intro, {})
    return report


def test_hole_mint_order_accepts_ascending_compact_batch(tmp_path):
    eps = _hole_eps("  - New Nodes Introduced: N-1, N-2\n  - Reused Nodes Appearing:\n  - Hole-minted Nodes (b): N-3, N-4\n")
    assert _hole_report(tmp_path, eps).findings == []


def test_hole_mint_order_flags_descending_ids(tmp_path):
    eps = _hole_eps("  - New Nodes Introduced: N-1, N-2\n  - Hole-minted Nodes (b): N-4, N-3\n")
    report = _hole_report(tmp_path, eps)
    assert [(f.severity, f.check, f.location) for f in report.findings] == [("P0", "hole_mint_order", "N-3")]


def test_hole_mint_order_flags_id_hidden_on_reused_line(tmp_path):
    eps = _hole_eps("  - New Nodes Introduced: N-1, N-2\n  - Reused Nodes Appearing: N-3\n  - Hole-minted Nodes (b): N-3, N-4\n")
    assert [f.location for f in _hole_report(tmp_path, eps).findings] == ["N-3"]


def test_hole_mint_order_flags_id_hidden_on_existing_nodes_reused_line(tmp_path):
    for line in ("Existing Nodes Reused: N-3 (Person 3)\n", "- **Existing Nodes Reused:** N-3\n"):
        eps = _hole_eps("  - New Nodes Introduced: N-1, N-2\n  - Hole-minted Nodes (b): N-3, N-4\n" + line)
        assert [f.location for f in _hole_report(tmp_path, eps).findings] == ["N-3"]


def test_hole_mint_order_flags_gap_below_batch_max(tmp_path):
    eps = _hole_eps("  - New Nodes Introduced: N-1, N-2\n  - Hole-minted Nodes (b): N-3, N-4\n", "  - Hole-minted Nodes (b): N-9\n",
                    "**N-9** Person 9\n\nNode Type: Person\n\n")
    report = _hole_report(tmp_path, eps)
    assert [f.location for f in report.findings] == ["N-9"]
    assert "free person ids remain below it: N-5" in report.findings[0].message


def test_hole_mint_order_flags_wrong_episode(tmp_path):
    eps = _hole_eps("  - New Nodes Introduced: N-1, N-2\n  - Hole-minted Nodes (b): N-3\n", "  - Hole-minted Nodes (b): N-4\n")
    report = _hole_report(tmp_path, eps)
    assert [f.location for f in report.findings] == ["N-4"]
    assert "first registered in episode_001.md" in report.findings[0].message


def test_hole_mint_order_flags_ledger_appearance_in_earlier_episode(tmp_path):
    """N3: a hole-minted id listed on any ledger line of an earlier episode is flagged."""
    def draft(ledger: str, register: str) -> str:
        return f"## 1. Meta-Data\n\n- **Episode Ledger Summary**:\n{ledger}\n## 4. Node Register\n\n{register}\n## 5. Claim Register\n"
    reg1 = "".join(f"**N-{n}** Person {n}\n\nNode Type: Person\n\n" for n in (1, 2, 3))
    reg2 = "**N-4** Person 4\n\nNode Type: Person\n\n"
    for line in ("  - Reused Nodes Appearing: N-4\n", "  - New Nodes Introduced: N-1, N-2, N-4\n", "Existing Nodes Reused: N-4\n"):
        ledger1 = "  - New Nodes Introduced: N-1, N-2, N-3\n" + line if "New Nodes" not in line else line.replace("N-4", "N-3, N-4")
        eps = [
            (1, "episode_001.md", Path("x"), draft(ledger1, reg1)),
            (2, "episode_002.md", Path("y"), draft("  - New Nodes Introduced:\n  - Hole-minted Nodes (b): N-4\n", reg2)),
        ]
        report = _hole_report(tmp_path, eps)
        msgs = [f.message for f in report.findings if f.check == "hole_mint_order"]
        assert any("earlier episode (ep1)" in x for x in msgs), (line, msgs)
    # Clean control: the id first appears in its Hole-minted episode.
    eps = [
        (1, "episode_001.md", Path("x"), draft("  - New Nodes Introduced: N-1, N-2, N-3\n", reg1)),
        (2, "episode_002.md", Path("y"), draft("  - New Nodes Introduced:\n  - Hole-minted Nodes (b): N-4\n", reg2)),
    ]
    assert _hole_report(tmp_path, eps).findings == []


def _ep_draft(ledger: str, register: str, claims: str = "", artifacts: str = "") -> str:
    return (
        f"## 1. Meta-Data\n\n- **Episode Ledger Summary**:\n{ledger}\n## 3. Artifact Register\n\n{artifacts}\n"
        f"## 4. Node Register\n\n{register}\n## 5. Claim Register\n\n{claims}"
    )


def _reg(*ids: int, kind: str = "Person") -> str:
    return "".join(f"**N-{n}** Node {n}\n\nNode Type: {kind}\n\n*Related: C-1*\n\n---\n\n" for n in ids)


def test_cited_before_intro_flags_mentions_and_related(tmp_path):
    """PR 60 re-audit P0-1: a person cited before its introduction episode is P0."""
    base = (0, "episode_000.md", Path("b"), "baseline N-1\n")
    for line in ("Mentions: N-5\n", "Related Nodes: N-5\n", "*Related: C-1, N-5*\n"):
        claims = f"**C-1** Claim\n\nClaim Timestamp: 00:01:00\nClaim: x\n{line}\n---\n"
        eps = [
            base,
            (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-2\n", _reg(2), claims)),
            (2, "episode_002.md", Path("y"), _ep_draft("  - New Nodes Introduced: N-5\n", _reg(5))),
        ]
        report = dp.PreflightReport("t", str(tmp_path))
        dp.check_cited_before_intro(report, eps)
        assert [(f.severity, f.check, f.location) for f in report.findings] == [("P0", "cited_before_intro", "N-5")], line
    # Clean controls: cited in its own episode, a baseline id, and a topic-band id.
    claims = "**C-1** Claim\n\nClaim: x\nMentions: N-1, N-2\nRelated Nodes: N-1500\n\n---\n"
    eps = [base, (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-2\n", _reg(2), claims))]
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_cited_before_intro(report, eps)
    assert report.findings == []


def test_cited_before_intro_flags_reused_before_new(tmp_path):
    """Wave 2.1 (N-898 Macron): Reused (and registered) in an earlier episode than its New line is P0."""
    base = (0, "episode_000.md", Path("b"), "baseline N-1\n")
    eps = [
        base,
        (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-2\n  - Reused Nodes Appearing: N-5\n", _reg(2, 5))),
        (2, "episode_002.md", Path("y"), _ep_draft("  - New Nodes Introduced: N-5\n", _reg(5))),
    ]
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_cited_before_intro(report, eps)
    got = sorted((f.check, f.location, f.message.split(" line")[0].split("on a ")[-1]) for f in report.findings)
    assert got == [("cited_before_intro", "N-5", "Reused"), ("cited_before_intro", "N-5", "register row")]
    # Clean control: introduced first, reused later.
    eps = [
        base,
        (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-5\n", _reg(5))),
        (2, "episode_002.md", Path("y"), _ep_draft("  - New Nodes Introduced: N-6\n  - Reused Nodes Appearing: N-5\n", _reg(5, 6))),
    ]
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_cited_before_intro(report, eps)
    assert report.findings == []


def test_ledger_intro_flags_ids_only_ever_reused(tmp_path):
    base = (0, "episode_000.md", Path("b"), "baseline N-1, N-1000\n")
    eps = [
        base,
        (1, "episode_001.md", Path("x"), _ep_draft("  - Reused Nodes Appearing: N-1, N-7\n", _reg(7))),
        (2, "episode_002.md", Path("y"), _ep_draft("  - New Nodes Introduced: N-8\n  - Hole-minted Nodes (b): N-9\n", _reg(8, 9) + _reg(1500, kind="Topic"))),
    ]
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_ledger_intro(report, eps)
    assert sorted((f.severity, f.check, f.location) for f in report.findings) == [
        ("P0", "intro_missing", "N-1500"),
        ("P0", "intro_missing", "N-7"),
    ]


def test_tip_mint_order_accepts_band_tip_and_flags_holes(tmp_path):
    def run(ep2_ledger: str, reg2: str) -> list[tuple[str, str, str]]:
        eps = [
            (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-1000, N-1001\n", _reg(1000, 1001, kind="Topic"))),
            (2, "episode_002.md", Path("y"), _ep_draft(ep2_ledger, reg2)),
        ]
        intro = dp.first_introduction_meta(dp.collect_register_entries(eps))
        report = dp.PreflightReport("t", str(tmp_path))
        dp.check_tip_minted(report, eps, intro)
        return [(f.severity, f.check, f.location) for f in report.findings]

    assert run("  - New Nodes Introduced:\n  - Tip-minted Nodes (b): N-1005\n", _reg(1005, kind="Organization")) == []
    # An id below the band frontier is a hole mint, not a tip mint.
    assert run("  - New Nodes Introduced: N-1003\n  - Tip-minted Nodes (b): N-1002\n", _reg(1002, 1003, kind="Topic")) == [
        ("P0", "tip_mint_order", "N-1002")
    ]
    # A tip id may not also sit on the New line.
    assert ("P0", "tip_mint_order", "N-1005") in run(
        "  - New Nodes Introduced: N-1005\n  - Tip-minted Nodes (b): N-1005\n", _reg(1005, kind="Topic")
    )


def test_dangling_claim_ref_flags_undefined_claims(tmp_path):
    claims = "**C-1** Claim\n\nClaim: x\nRevises: C-9\n\n---\n"
    arts = "**A-1.1** Artifact\n\n*Related: C-1, C-7, N-1*\n\n"
    eps = [(1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-1\n", _reg(1), claims, arts))]
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_dangling_claim_refs(report, eps)
    assert sorted((f.severity, f.check, f.location) for f in report.findings) == [
        ("P1", "dangling_claim_ref", "C-7"),
        ("P1", "dangling_claim_ref", "C-9"),
    ]


def test_artifact_related_line_counts_as_citation():
    """A super-chat artifact whose *Related:* line names only its author node still cites that node."""
    content = _ep_draft(
        "  - New Nodes Introduced: N-1, N-2\n",
        "**N-1** Handle\n\nNode Type: Person\n\n*Related: A-1.1*\n\n---\n\n**N-2** Other\n\nNode Type: Person\n\n*Related: N-1*\n\n",
        artifacts="**A-1.1** Super chat\n\nVideo Timestamp: 00:01:00\n\n*Related: N-1*\n\n",
    )
    cited = dp.collect_claim_artifact_related_n_ids([(1, "episode_001.md", Path("x"), content)])
    assert 1 in cited and 2 not in cited


def test_hostile_ledger_check_covers_mentions_and_related():
    import importlib.util

    path = ROOT / "projects" / "monuments" / "cka" / "scripts" / "hostile_hard_gates_audit.py"
    spec = importlib.util.spec_from_file_location("cka_hostile_audit_t", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    text = "Mentions: N-1, N-7\nRelated Nodes: N-1000, N-1009\n"
    assert mod.cited_not_on_ledger(text, {"N-1", "N-1000"}) == [("N-7", "Mentions"), ("N-1009", "Related Nodes")]
    assert mod.cited_not_on_ledger(text, {"N-1", "N-7", "N-1000", "N-1009"}) == []


def test_cka_has_no_wave1_people_regressions():
    """Wave 1 cleared these classes on CKA; they must stay at zero."""
    report = dp.run_preflight("cka")
    bad = [
        f
        for f in report.findings
        if f.check
        in (
            "person_like_topic",
            "mention_grounding",
            "tombstone_collision",
            "person_band",
            "register_orphan",
            "retired_citation",
            "unknown_node",
            "name_annotation_mismatch",
            "hole_mint_order",
            "tip_mint_order",
            "cited_before_intro",
            "intro_missing",
            "dangling_claim_ref",
            "prose_em_dash",
            "quote_dash_fidelity",
            "inscription_missing",
        )
    ]
    assert bad == [], bad


if __name__ == "__main__":
    test_self_test_exits_zero()
    test_bride_of_charlie_main_tip_passes()
    print("ok")


def test_hostile_wrapper_prints_accepted_codes():
    """PR 60 re-audit: the hostile console output must name the accepted codes, not only the counts."""
    import subprocess

    out = subprocess.run(
        [sys.executable, str(ROOT / "projects" / "monuments" / "scripts" / "hostile_hard_gates.py"), "--monument", "cka"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout
    assert '"accepted"' in out and "CA_DEBT_CALLOUT" in out


def test_stamp_form_flags_minutes_above_59(tmp_path):
    """Wave 2.1 (C-1909 00:60:00)."""
    content = "**C-1** x\n\nClaim Timestamp: 00:60:00\nVideo Timestamp: 00:59:22\n"
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_stamps(report, [(1, "episode_001.md", Path("x"), content)])
    assert [(f.severity, f.check) for f in report.findings] == [("P1", "stamp_form")]


# ---------------------------------------------------------------------------
# Dash rule gates (Daveed, 8 Oct 2026)
# ---------------------------------------------------------------------------

EM, EN = "\u2014", "\u2013"


def test_prose_em_dash_flags_prose_but_not_quotes(tmp_path):
    text = (
        f"**A-1.1** Bowyer SD card account {EM} law enforcement instruction\n"
        f"**A-1.2** Bowyer SD card account {EN} law enforcement instruction\n"
        f"Transcript Snippet: wait {EM} no\n"
        f"Quote: they knew {EM} they knew\n"
        f'Contents (read on air): Candace {EN} "Not now {EM} not ever"\n'
        f"Claim: Host says X {EM} not Y.\n"
    )
    eps = _episode(tmp_path, text)
    ins = tmp_path / "inscription"
    ins.mkdir()
    (ins / "episode_001.json").write_text(
        json.dumps({"artifacts": [{"description": f"a {EM} b", "transcript_snippet": f"c {EM} d"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    can = tmp_path / "canonical"
    can.mkdir()
    (can / "nodes.json").write_text(json.dumps({"nodes": {"N-1": {"canonical_name": f"X {EM} Y"}}}), encoding="utf-8")
    report = dp.PreflightReport("t", "t")
    dp.check_prose_em_dash(report, tmp_path, eps)
    locs = sorted(f.location for f in report.findings)
    assert all(f.severity == "P2" and f.check == "prose_em_dash" for f in report.findings)
    assert locs == sorted(["episode_001.md:1", "episode_001.md:6", "inscription/episode_001.json/artifacts/0/description", "canonical/nodes.json/nodes/N-1/canonical_name"])


def _transcript(tmp_path: Path, body: str, ep: int = 1) -> None:
    d = tmp_path / "transcripts_corrected"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"episode_{ep:03d}_abc.md").write_text(body, encoding="utf-8")


def test_quote_dash_fidelity_matches_transcript_dashes(tmp_path):
    _transcript(
        tmp_path,
        "# Title\n\n- [0:00] Intro\n- [41:12] Tucker says the quiet part\n\n[00:10]\n"
        f"I said wait {EN} no, they knew. And then about me. Tucker says the quiet part out loud.\n",
    )
    text = "\n".join(
        [
            f"Transcript Snippet: I said wait {EN} no, they knew.",  # exact: pass
            f"Quote: I said wait {EM} no",  # em where transcript has en: fail
            "Quote: I said wait no, they knew.",  # dash dropped: fail
            "Quote: about me. - Tucker says the quiet part",  # pasted chapter bullet: fail
            "Transcript Snippet: Tucker says the quiet part out loud.",  # no dashes either side: pass
            f"Quote: they knew...about me {EM} Tucker",  # ellipsis segment, dash not in transcript: fail
        ]
    )
    eps = _episode(tmp_path, text)
    report = dp.PreflightReport("t", "t")
    dp.check_quote_dash_fidelity(report, tmp_path, eps)
    assert all(f.severity == "P1" and f.check == "quote_dash_fidelity" for f in report.findings)
    assert sorted(f.location for f in report.findings) == ["episode_001.md:2", "episode_001.md:3", "episode_001.md:4", "episode_001.md:6"]


def test_quote_dash_fidelity_checks_inscription_quotes(tmp_path):
    _transcript(tmp_path, "[00:01]\nno dashes here at all\n")
    ins = tmp_path / "inscription"
    ins.mkdir()
    (ins / "episode_001.json").write_text(
        json.dumps({"memes": [{"quote": f"no {EM} dashes"}], "claims": [{"transcript_snippet": "no dashes here"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    report = dp.PreflightReport("t", "t")
    dp.check_quote_dash_fidelity(report, tmp_path, [])
    assert [f.location for f in report.findings] == ["inscription/episode_001.json/memes/0/quote"]


def test_dash_gates_are_opt_in_per_monument():
    cka = dp.load_gate_config(dp.MONUMENTS_ROOT / "cka").get("dash_rule") or {}
    assert cka.get("prose_em_dash") and cka.get("quote_dash_fidelity")
    boc = dp.load_gate_config(dp.MONUMENTS_ROOT / "bride_of_charlie").get("dash_rule") or {}
    assert not boc


def test_cka_ep119_m55_quote_is_verbatim():
    text = (dp.MONUMENTS_ROOT / "cka" / "drafts" / "episode_119.md").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("Quote:") and "quiet part" in l)
    quote = line.split(":", 1)[1].strip()
    tp = dp.find_transcript(dp.MONUMENTS_ROOT / "cka", 119)
    assert quote in tp.read_text(encoding="utf-8")
    assert " - " not in quote and "##" not in quote


def test_cited_before_intro_covers_topics_in_strict_mode(tmp_path):
    """Wave 3 / Transit 820af0d P2-2: a topic on a Reused line before its New line must fail."""
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "episode_001.md").write_text(
        "## 4. Node Register\n\n**N-1282** Some Topic\n\n"
        "- **Reused Nodes Appearing:** N-1282\n",
        encoding="utf-8",
    )
    (drafts / "episode_002.md").write_text(
        "## 4. Node Register\n\n**N-1282** Some Topic\n\n"
        "- **New Nodes Introduced:** N-1282\n",
        encoding="utf-8",
    )
    eps = [
        (1, "episode_001.md", drafts / "episode_001.md", (drafts / "episode_001.md").read_text()),
        (2, "episode_002.md", drafts / "episode_002.md", (drafts / "episode_002.md").read_text()),
    ]
    report = dp.PreflightReport("t", "t")
    dp.check_cited_before_intro(report, eps, strict=True)
    assert any(f.check == "cited_before_intro" and f.location == "N-1282" for f in report.findings)
    report2 = dp.PreflightReport("t", "t")
    dp.check_cited_before_intro(report2, eps, strict=False)
    assert report2.findings == []


def test_inscription_missing_flags_draft_only_ids(tmp_path):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    text = (
        "## 5. Claim Register\n\n**C-9001** Draft only claim\n\nClaim: x\n\n"
        "## 3. Artifact Register\n\n**A-9001** Family\n\n**A-9001.1** Sub\n\n"
        "Description: y\n"
    )
    (drafts / "episode_001.md").write_text(text, encoding="utf-8")
    ins = tmp_path / "inscription"
    ins.mkdir()
    (ins / "episode_001.json").write_text(
        json.dumps({"claims": [{"@id": "C-1", "label": "other"}], "artifacts": []}),
        encoding="utf-8",
    )
    eps = [(1, "episode_001.md", drafts / "episode_001.md", text)]
    report = dp.PreflightReport("t", "t")
    dp.check_inscription_missing(report, tmp_path, eps)
    locs = sorted(f.location for f in report.findings)
    assert locs == ["A-9001", "A-9001.1", "C-9001"]
    assert all(f.severity == "P1" and f.check == "inscription_missing" for f in report.findings)



def _nbi_report(tmp_path: Path, eps, canonical: dict, accepted: list | None = None, enabled: bool = True):
    (tmp_path / "config").mkdir(exist_ok=True)
    gates = {"named_before_intro": {"enabled": enabled, "accepted": accepted or []}}
    (tmp_path / "config" / "preflight_gates.json").write_text(json.dumps(gates), encoding="utf-8")
    report = dp.PreflightReport("t", str(tmp_path))
    dp.check_named_before_intro(report, tmp_path, eps, canonical)
    return report


NBI_CANON = {
    "N-2": {"canonical_name": "Node Two", "type": "person", "aliases": []},
    "N-5": {"canonical_name": "Dan Bongino", "type": "person", "aliases": ["Dan Bonino"]},
    "N-6": {"canonical_name": "Pat Smith", "type": "person", "aliases": []},
    "N-7": {"canonical_name": "Pat Smith", "type": "person", "aliases": []},
}


def test_named_before_intro_flags_name_and_alias_without_n_id(tmp_path):
    """Transit 73d663b P1-3: a person named in claim text before their intro episode fails even with no N-id."""
    base = (0, "episode_000.md", Path("b"), "baseline N-1\n")
    for text in ("Claim: Host cites Dan Bongino on air.\n", "Claim: Host cites Dan Bonino on air.\n",
                 "Claim: x\nInvestigative Direction: ask dan bongino.\n"):
        claims = f"**C-1** Claim\n\nClaim Timestamp: 00:01:00\n{text}\n---\n"
        eps = [
            base,
            (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-2\n", _reg(2), claims)),
            (2, "episode_002.md", Path("y"), _ep_draft("  - New Nodes Introduced: N-5\n", _reg(5))),
        ]
        report = _nbi_report(tmp_path, eps, NBI_CANON)
        assert [(f.severity, f.check, f.location) for f in report.findings] == [("P1", "named_before_intro", "N-5")], text
    # Artifact labels are scanned too.
    arts = "**A-1.1** Dan Bongino clip on X\n\n"
    eps = [
        base,
        (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-2\n", _reg(2), "", arts)),
        (2, "episode_002.md", Path("y"), _ep_draft("  - New Nodes Introduced: N-5\n", _reg(5))),
    ]
    assert [f.location for f in _nbi_report(tmp_path, eps, NBI_CANON).findings] == ["N-5"]


def test_named_before_intro_clean_controls(tmp_path):
    base = (0, "episode_000.md", Path("b"), "baseline N-1\n")
    late = (2, "episode_002.md", Path("y"), _ep_draft("  - New Nodes Introduced: N-5, N-6, N-7\n", _reg(5, 6, 7)))
    # Named in its own intro episode; quote fields are not scanned; ambiguous names (two persons) are skipped.
    claims = ('**C-1** Claim\n\nClaim: Pat Smith spoke.\nTranscript Snippet: Dan Bongino said so.\n\n---\n')
    eps = [base, (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-2\n", _reg(2), claims)), late]
    assert _nbi_report(tmp_path, eps, NBI_CANON).findings == []
    claims2 = "**C-2** Claim\n\nClaim: Dan Bongino spoke.\n\n---\n"
    eps = [base, (2, "episode_002.md", Path("y"), _ep_draft("  - New Nodes Introduced: N-5\n", _reg(5), claims2))]
    assert _nbi_report(tmp_path, eps, NBI_CANON).findings == []
    # Accepted debt pair and the disabled gate are both silent.
    claims3 = "**C-1** Claim\n\nClaim: Dan Bongino spoke.\n\n---\n"
    eps = [base, (1, "episode_001.md", Path("x"), _ep_draft("  - New Nodes Introduced: N-2\n", _reg(2), claims3)), late]
    assert _nbi_report(tmp_path, eps, NBI_CANON, accepted=[{"id": "N-5", "episodes": [1], "reason": "debt"}]).findings == []
    assert _nbi_report(tmp_path, eps, NBI_CANON, enabled=False).findings == []


def _pbl_dir(tmp_path, nodes, retired=None, reserved=None, next_person_id=None, enabled=True):
    d = tmp_path / "mon"
    (d / "config").mkdir(parents=True, exist_ok=True)
    (d / "canonical").mkdir(parents=True, exist_ok=True)
    (d / "config" / "preflight_gates.json").write_text(json.dumps({"person_band_lock": {"enabled": enabled}}))
    (d / "config" / "retired_node_ids.json").write_text(json.dumps({
        "retired": retired or {}, "reserved_baseline_ids": {"ids": reserved or []}}))
    (d / "canonical" / "nodes.json").write_text(json.dumps({"next_person_id": next_person_id, "nodes": nodes}))
    return d


def test_person_band_lock_flags_reuse_reserved_high_band_and_next_id(tmp_path):
    """Transit b558034: while the band is locked, no tombstone/reserved reuse, no person >= N-1000, next_person_id null."""
    nodes = {
        "N-5": {"canonical_name": "Reused Tombstone", "type": "person"},
        "N-17": {"canonical_name": "On Reserved", "type": "person"},
        "N-1200": {"canonical_name": "High Person", "type": "person"},
        "N-1201": {"canonical_name": "A Topic", "type": "topic"},
    }
    d = _pbl_dir(tmp_path, nodes, retired={"legacy-N-5": {"survives_as": None}}, reserved=["N-17"], next_person_id=630)
    report = dp.PreflightReport("t", str(d))
    dp.check_person_band_lock(report, d, nodes)
    got = sorted((f.severity, f.check, f.location) for f in report.findings)
    assert got == sorted([("P1", "person_band_lock", "next_person_id"), ("P1", "person_band_lock", "N-5"),
                          ("P1", "person_band_lock", "N-17"), ("P1", "person_band_lock", "N-1200")])


def test_person_band_lock_clean_and_disabled(tmp_path):
    nodes = {"N-6": {"canonical_name": "Live Person", "type": "person"},
             "N-1201": {"canonical_name": "A Topic", "type": "topic"}}
    d = _pbl_dir(tmp_path, nodes, retired={"legacy-N-5": {"survives_as": "N-6"}}, reserved=["N-17"])
    report = dp.PreflightReport("t", str(d))
    dp.check_person_band_lock(report, d, nodes)
    assert report.findings == []
    bad = {"N-1200": {"canonical_name": "High Person", "type": "person"}}
    d2 = _pbl_dir(tmp_path / "off", bad, next_person_id=1, enabled=False)
    report = dp.PreflightReport("t", str(d2))
    dp.check_person_band_lock(report, d2, bad)
    assert report.findings == []



# --- person_band_lock hardening (Transit baa2ed9 G1/G2) -----------------------

CKA_DIR = Path(__file__).resolve().parents[1] / "cka"


def _band_fixture(tmp_path, *, gates=None):
    """Synthetic full band: live N-1..N-5, tombstoned N-6..N-998, reserved N-999, pinned snapshot."""
    d = tmp_path / "band"
    (d / "config").mkdir(parents=True)
    (d / "canonical").mkdir(parents=True)
    nodes = {f"N-{i}": {"canonical_name": f"Person {i}", "type": "person", "aliases": []} for i in range(1, 6)}
    retired = {f"legacy-N-{i}": {"survives_as": None} for i in range(6, 999)}
    (d / "canonical" / "nodes.json").write_text(json.dumps({"next_person_id": None, "nodes": nodes}))
    (d / "config" / "retired_node_ids.json").write_text(json.dumps(
        {"retired": retired, "reserved_baseline_ids": {"ids": ["N-999"]}}))
    (d / "config" / "preflight_gates.json").write_text(json.dumps(
        gates if gates is not None else {"person_band_lock": {"enabled": True, "snapshot": "config/person_band_snapshot.json"}}))
    snap, errors = dp.build_band_snapshot(d, nodes, None)
    assert errors == [] and snap["counts"]["total"] == 999
    (d / "config" / "person_band_snapshot.json").write_text(json.dumps(snap))
    return d, nodes


def _band_report(d, nodes):
    report = dp.PreflightReport("t", str(d))
    dp.check_person_band_lock(report, d, nodes)
    return report


def _lock_p1(report):
    return sorted(f.location for f in report.findings if f.check == "person_band_lock" and f.severity == "P1")


def test_person_band_lock_snapshot_clean(tmp_path):
    d, nodes = _band_fixture(tmp_path)
    assert _band_report(d, nodes).findings == []


def test_person_band_lock_deleted_tombstone_and_reuse_fails(tmp_path):
    """Transit baa2ed9 mutation E: delete legacy-N-161 from the ledger and mint a new person at N-161."""
    d, nodes = _band_fixture(tmp_path)
    rpath = d / "config" / "retired_node_ids.json"
    data = json.loads(rpath.read_text())
    del data["retired"]["legacy-N-161"]
    rpath.write_text(json.dumps(data))
    nodes = dict(nodes, **{"N-161": {"canonical_name": "New Person", "type": "person"}})
    p1 = _lock_p1(_band_report(d, nodes))
    assert p1.count("N-161") == 2  # pinned tombstone removed + id not live in the snapshot


def test_person_band_lock_deleted_tombstone_alone_fails(tmp_path):
    d, nodes = _band_fixture(tmp_path)
    rpath = d / "config" / "retired_node_ids.json"
    data = json.loads(rpath.read_text())
    del data["retired"]["legacy-N-7"]
    data["reserved_baseline_ids"]["ids"] = []
    rpath.write_text(json.dumps(data))
    assert _lock_p1(_band_report(d, nodes)) == ["N-7", "N-999"]


def test_person_band_lock_missing_key_is_on(tmp_path):
    """Transit baa2ed9 mutation G: remove the person_band_lock key and set next_person_id = 630."""
    d, nodes = _band_fixture(tmp_path, gates={"dash_rule": {}})
    npath = d / "canonical" / "nodes.json"
    data = json.loads(npath.read_text())
    data["next_person_id"] = 630
    npath.write_text(json.dumps(data))
    report = _band_report(d, nodes)
    assert _lock_p1(report) == ["next_person_id"]
    assert any(f.severity == "WARN" and f.check == "person_band_lock" for f in report.findings)


def test_person_band_lock_disable_needs_cited_ruling(tmp_path):
    d, nodes = _band_fixture(tmp_path, gates={"person_band_lock": {"enabled": False}})
    nodes = dict(nodes, **{"N-1200": {"canonical_name": "High", "type": "person"}})
    p1 = _lock_p1(_band_report(d, nodes))
    assert "person_band_lock" in p1 and "N-1200" in p1
    d2, nodes2 = _band_fixture(tmp_path / "lifted", gates={"person_band_lock": {"enabled": False, "lifted_by": "Daveed ruling (doc, date)"}})
    assert _band_report(d2, nodes2).findings == []


def test_person_band_lock_snapshot_missing_tampered_or_identity_change(tmp_path):
    d, nodes = _band_fixture(tmp_path)
    spath = d / "config" / "person_band_snapshot.json"
    snap = json.loads(spath.read_text())
    snap["tombstoned"].remove("N-161")  # hand edit without a valid digest
    spath.write_text(json.dumps(snap))
    assert _lock_p1(_band_report(d, nodes)) == ["config/person_band_snapshot.json"]
    spath.unlink()
    assert _lock_p1(_band_report(d, nodes)) == ["config/person_band_snapshot.json"]
    d2, nodes2 = _band_fixture(tmp_path / "ident")
    nodes2 = dict(nodes2, **{"N-3": {"canonical_name": "Someone Else", "type": "person", "aliases": []}})
    assert _lock_p1(_band_report(d2, nodes2)) == ["N-3"]
    renamed = dict(nodes2, **{"N-3": {"canonical_name": "Person Three", "type": "person", "aliases": ["Person 3"]}})
    assert _band_report(d2, renamed).findings == []


def test_person_band_lock_retirement_is_append_only(tmp_path):
    d, nodes = _band_fixture(tmp_path)
    rpath = d / "config" / "retired_node_ids.json"
    data = json.loads(rpath.read_text())
    data["retired"]["legacy-N-5"] = {"survives_as": None}
    rpath.write_text(json.dumps(data))
    nodes = {k: v for k, v in nodes.items() if k != "N-5"}
    report = _band_report(d, nodes)
    assert _lock_p1(report) == [] and [f.severity for f in report.findings] == ["P2"]  # stale snapshot
    prev = json.loads((d / "config" / "person_band_snapshot.json").read_text())
    snap, errors = dp.build_band_snapshot(d, nodes, prev)
    assert errors == [] and snap["counts"] == {"live": 4, "tombstoned": 994, "reserved": 1, "total": 999}
    del data["retired"]["legacy-N-6"]
    rpath.write_text(json.dumps(data))
    snap, errors = dp.build_band_snapshot(d, nodes, prev)
    assert snap is None and any("N-6" in e for e in errors)


def test_band_lock_malformed_config_fails_closed(tmp_path):
    """G2: malformed preflight_gates.json / retired_node_ids.json give clean findings, never a traceback."""
    d, nodes = _band_fixture(tmp_path)
    (d / "config" / "preflight_gates.json").write_text("{not json")
    (d / "config" / "retired_node_ids.json").write_text("{\"retired\": ")
    report = _band_report(d, nodes)
    p1 = _lock_p1(report)
    assert "retired_node_ids.json" in p1 and p1.count("N-7") == 1  # lock stays on, pinned tombstones now missing
    readable = dp.PreflightReport("t", str(d))
    bad = dp.check_json_readable(readable, d)
    assert bad == {"config/preflight_gates.json", "config/retired_node_ids.json"}
    assert {f.severity for f in readable.findings} == {"P0"}


def test_malformed_config_run_reports_p0_without_traceback(tmp_path):
    root = tmp_path / "wave1_fixture"
    dp.build_wave1_fixture(root)
    (root / "config" / "preflight_gates.json").write_text("{broken")
    (root / "config" / "retired_node_ids.json").write_text("[1, 2")
    report = dp._run_fixture("test_mon_g2_pytest", root, skip_inscription=False)
    locs = {f.location for f in report.findings if f.check == "config_unreadable" and f.severity == "P0"}
    assert {"config/preflight_gates.json", "config/retired_node_ids.json"} <= locs


def _cka_copy(tmp_path):
    import shutil

    d = tmp_path / "cka"
    shutil.copytree(CKA_DIR / "config", d / "config")
    shutil.copytree(CKA_DIR / "canonical", d / "canonical")
    nodes = dp.load_canonical_nodes(d / "canonical" / "nodes.json")
    return d, nodes


def test_cka_band_lock_clean_and_snapshot_covers_999(tmp_path):
    d, nodes = _cka_copy(tmp_path)
    snap = json.loads((d / "config" / "person_band_snapshot.json").read_text())
    assert snap["counts"]["total"] == 999
    assert _lock_p1(_band_report(d, nodes)) == []


def test_cka_mutation_e_delete_tombstone_and_mint_fails(tmp_path):
    d, nodes = _cka_copy(tmp_path)
    rpath = d / "config" / "retired_node_ids.json"
    data = json.loads(rpath.read_text())
    del data["retired"]["legacy-N-161"]
    rpath.write_text(json.dumps(data))
    nodes = dict(nodes, **{"N-161": {"canonical_name": "New Person", "type": "person"}})
    assert _lock_p1(_band_report(d, nodes)).count("N-161") == 2


def test_cka_mutation_g_remove_key_fails(tmp_path):
    d, nodes = _cka_copy(tmp_path)
    gpath = d / "config" / "preflight_gates.json"
    gates = json.loads(gpath.read_text())
    del gates["person_band_lock"]
    gpath.write_text(json.dumps(gates))
    npath = d / "canonical" / "nodes.json"
    data = json.loads(npath.read_text())
    data["next_person_id"] = 630
    npath.write_text(json.dumps(data))
    assert _lock_p1(_band_report(d, nodes)) == ["next_person_id"]
