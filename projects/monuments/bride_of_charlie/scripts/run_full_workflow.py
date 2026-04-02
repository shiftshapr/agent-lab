"""
Run Full Workflow — Bride of Charlie
Executes the ideal workflow from prepare through final reports.

Usage:
  cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
  python scripts/run_full_workflow.py

  --no-backup       Skip backing up existing drafts
  --skip-search     Skip DuckDuckGo name verification (faster)
  --stop-after N    Stop after stage N (1-6)
  --skip-fetch      Skip transcript fetch even when episode transcripts are missing
  --max-passes N    Max second-pass iterations (default 5)

Env:
  BRIDE_STOP_AFTER_GREEN_VALIDATE=1  Stop multi-pass loop when neo4j_validate exits 0 (saves API $)
  BRIDE_EXPECTED_EPISODES            Optional override for fetch threshold (else: youtube_links.txt line count)
  BRIDE_EDITORIAL_PASS=1             Run editorial_transcript_pass (+ sync) as part of transcript postprocess (see docs/EDITORIAL_PASS.md)
  BRIDE_TRANSCRIPT_OVERRIDES=1       After editorial, apply config/transcript_overrides.json (accepted items); then sync hashes (default on)
  BRIDE_EXPORT_DUAL_TRANSCRIPTS=1   Pass --dual-transcripts to export_for_inscription.py (verbatim + display)
  BRIDE_EXPORT_DISPLAY_CLEAN=1      With dual, pass --display-clean (uh/um strip in display file); then re-sync hashes

Fetch: raw transcripts are not re-downloaded when you already have one file per link in
input/youtube_links.txt (Stage 2). Optional override: BRIDE_EXPECTED_EPISODES. Manual one-off:
run_workflow.py fetch.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Script is at projects/monuments/bride_of_charlie/scripts/
PROJECT_DIR = Path(__file__).resolve().parent.parent
AGENT_LAB = PROJECT_DIR.parent.parent.parent
UV_CMD = ["uv", "run", "--project", str(AGENT_LAB / "framework" / "deer-flow" / "backend")]


def _bootstrap_agent_lab_env() -> None:
    """Load .env and fix legacy local Bolt :7687 (OrbStack hijack) -> compose port :17687."""
    try:
        from dotenv import load_dotenv

        load_dotenv(AGENT_LAB / ".env", override=False)
    except ImportError:
        pass
    uri = os.environ.get("NEO4J_URI", "").strip()
    if re.fullmatch(r"bolt://(localhost|127\.0\.0\.1):7687/?", uri, re.IGNORECASE):
        os.environ["NEO4J_URI"] = "bolt://127.0.0.1:17687"


_bootstrap_agent_lab_env()


def run(cmd: list[str], cwd: Path | None = None) -> int:
    """Run command, return exit code."""
    return subprocess.run(cmd, cwd=cwd or AGENT_LAB).returncode


def run_python(script: str, args: list[str] = None, cwd: Path | None = None) -> int:
    """Run Python script via uv."""
    cmd = UV_CMD + ["python", str(script)] + (args or [])
    return run(cmd, cwd=cwd or AGENT_LAB)


def run_python_capture(script: str, args: list[str] = None, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run Python script via uv, return (returncode, stdout, stderr)."""
    cmd = UV_CMD + ["python", str(script)] + (args or [])
    result = subprocess.run(cmd, cwd=cwd or AGENT_LAB, capture_output=True, text=True)
    return result.returncode, result.stdout or "", result.stderr or ""


def run_transcript_postprocess_and_sync(project: Path) -> None:
    """
    After neo4j apply-dir (or any transcripts_corrected regen): editorial rules →
    human overrides → transcript_sha256 sync.
    """
    editorial = os.getenv("BRIDE_EDITORIAL_PASS", "").strip() in ("1", "true", "yes")
    ovr = os.getenv("BRIDE_TRANSCRIPT_OVERRIDES", "1").strip() in ("1", "true", "yes")
    ep_script = project / "scripts" / "editorial_transcript_pass.py"
    ap_script = project / "scripts" / "apply_transcript_overrides.py"
    sh_script = project / "scripts" / "sync_transcript_hashes.py"
    ran = False
    if editorial and ep_script.is_file():
        print("\n      editorial_transcript_pass.py...")
        run_python(ep_script, [])
        ran = True
    if ovr and ap_script.is_file():
        print("\n      apply_transcript_overrides.py --apply...")
        run_python(ap_script, ["--apply"])
        ran = True
    elif ovr and not ap_script.is_file():
        print("      (apply_transcript_overrides.py not found — skip overrides)")
    if ran and sh_script.is_file():
        print("\n      sync_transcript_hashes.py...")
        run_python(sh_script, [])


def _apply_corrections_count(transcripts_dir: Path, corrected_dir: Path) -> int:
    """Run apply-dir (raw → corrected) and return number of replacements. Returns -1 if skipped."""
    script = PROJECT_DIR / "scripts" / "neo4j_corrections.py"
    if not script.exists():
        return -1
    code, out, _ = run_python_capture(
        script,
        ["apply-dir", str(transcripts_dir), "--output-dir", str(corrected_dir)],
    )
    if code != 0:
        return -1
    # Parse "✓ Total: N correction(s) across M file(s)"
    m = re.search(r"Total:\s*(\d+)\s+correction", out)
    return int(m.group(1)) if m else 0


LINKS_FILE = PROJECT_DIR / "input" / "youtube_links.txt"


def expected_episode_count_from_links() -> int | None:
    """Count non-comment lines in youtube_links.txt (same rules as fetch_transcripts.py)."""
    if not LINKS_FILE.exists():
        return None
    try:
        text = LINKS_FILE.read_text(encoding="utf-8")
    except OSError:
        return None
    links = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return len(links) if links else None


def resolve_expected_episodes() -> tuple[int, str]:
    """
    How many episode_*.txt files we expect in transcripts/ before skipping fetch.

    BRIDE_EXPECTED_EPISODES overrides. Otherwise use len(youtube_links.txt non-comment lines).
    Fallback 7 if the links file is missing or empty.
    """
    raw = os.getenv("BRIDE_EXPECTED_EPISODES", "").strip()
    if raw:
        try:
            return int(raw), "BRIDE_EXPECTED_EPISODES"
        except ValueError:
            pass
    n = expected_episode_count_from_links()
    if n is not None:
        return n, str(LINKS_FILE.relative_to(PROJECT_DIR))
    return 7, "default (no links file)"


def clear_neo4j() -> bool:
    """Clear Neo4j graph, preserving NameCorrection nodes. Returns True if successful."""
    if not os.getenv("NEO4J_URI"):
        return False
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "openclaw")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # Preserve NameCorrection so transcript corrections persist across runs
            session.run("""
                MATCH (n)
                WHERE NOT n:NameCorrection
                DETACH DELETE n
            """)
        driver.close()
        return True
    except Exception as e:
        print(f"      Could not clear Neo4j: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full Bride of Charlie workflow")
    parser.add_argument("--no-backup", action="store_true", help="Skip backing up drafts")
    parser.add_argument("--skip-search", action="store_true", help="Skip DuckDuckGo verification")
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Never fetch from YouTube (even if transcripts/ is short of expected episode_*.txt)",
    )
    parser.add_argument("--stop-after", type=int, choices=[1, 2, 3, 4, 5, 6],
                       help="Stop after stage N")
    parser.add_argument("--max-passes", type=int, default=5,
                       help="Max second-pass iterations (default 5)")
    args = parser.parse_args()
    
    print("=" * 80)
    print("BRIDE OF CHARLIE — FULL WORKFLOW")
    print("=" * 80)
    
    # -------------------------------------------------------------------------
    # Stage 1: Prepare
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STAGE 1: PREPARE")
    print("=" * 80)
    
    drafts_dir = PROJECT_DIR / "drafts"
    transcripts_dir = PROJECT_DIR / "transcripts"  # raw only — never modified by corrections
    corrected_dir = PROJECT_DIR / "transcripts_corrected"  # generated from raw + NameCorrection
    
    if not args.no_backup and drafts_dir.exists():
        backup_name = f"drafts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = PROJECT_DIR / backup_name
        print(f"\n[1.1] Backing up drafts to {backup_name}...")
        import shutil
        shutil.move(str(drafts_dir), str(backup_dir))
        print(f"      ✓ Backed up to {backup_dir.name}")
    
    if not drafts_dir.exists():
        drafts_dir.mkdir(parents=True)
        print(f"\n[1.2] Created fresh drafts/")

    # Build corrected copies — raw transcripts/ is never modified
    print("\n[1.3] Building transcripts_corrected/ from raw transcripts/ + NameCorrection...")
    if (PROJECT_DIR / "scripts" / "neo4j_corrections.py").exists():
        code = run_python(
            PROJECT_DIR / "scripts" / "neo4j_corrections.py",
            ["apply-dir", str(transcripts_dir), "--output-dir", str(corrected_dir)],
        )
        if code != 0:
            print("      (apply-dir failed — check Neo4j or paths)")
        else:
            print("      ✓ Corrected transcripts written to transcripts_corrected/")
    else:
        print("      (Skipped - neo4j_corrections.py not found)")

    print("\n[1.3b] Transcript postprocess (editorial + overrides + hash sync)...")
    run_transcript_postprocess_and_sync(PROJECT_DIR)

    print("\n[1.4] Clearing Neo4j graph (preserving NameCorrection)...")
    if clear_neo4j():
        print("      ✓ Graph cleared")
    else:
        print("      (Skipped - Neo4j not available or not configured)")
    
    raw_episode_n = (
        len(list(transcripts_dir.glob("episode_*.txt"))) if transcripts_dir.exists() else 0
    )
    corrected_count = (
        len(list(corrected_dir.glob("episode_*.txt"))) if corrected_dir.exists() else 0
    )
    print(f"\n[1.5] Raw episode transcripts: {raw_episode_n} file(s) matching episode_*.txt in transcripts/")
    print(f"      Corrected: {corrected_count} file(s) in transcripts_corrected/ (input to episode analysis)")
    if raw_episode_n == 0:
        print("      ERROR: No episode_*.txt in transcripts/. Run fetch or add files.")
        return 1
    if corrected_count == 0:
        print("      ERROR: transcripts_corrected/ is empty after [1.3]. Fix apply-dir / Neo4j.")
        return 1
    
    if args.stop_after == 1:
        print("\n--- Stopping after Stage 1 ---")
        return 0
    
    # -------------------------------------------------------------------------
    # Stage 2: Fetch (optional)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STAGE 2: FETCH TRANSCRIPTS")
    print("=" * 80)
    
    expected_episodes, expected_src = resolve_expected_episodes()
    print(f"      Expected episode transcripts: {expected_episodes} (from {expected_src})")
    if args.skip_fetch:
        print("\n[2.1] Skipping fetch (--skip-fetch)")
    elif raw_episode_n < expected_episodes:
        print(
            f"\n[2.1] Fetching missing transcripts ({raw_episode_n}/{expected_episodes} episode_*.txt in transcripts/)..."
        )
        run_python(
            AGENT_LAB / "projects" / "monuments" / "bride_of_charlie" / "scripts" / "run_workflow.py",
            ["fetch"],
        )
    else:
        print(
            f"\n[2.1] Skipping fetch ({raw_episode_n} episode_*.txt ≥ expected {expected_episodes}; raw files kept)"
        )

    # Keep corrected/ in sync if fetch added episodes (idempotent)
    print("\n[2.2] Sync transcripts_corrected/ from raw transcripts/...")
    if (PROJECT_DIR / "scripts" / "neo4j_corrections.py").exists():
        run_python(
            PROJECT_DIR / "scripts" / "neo4j_corrections.py",
            ["apply-dir", str(transcripts_dir), "--output-dir", str(corrected_dir)],
        )

    print("\n[2.3] Transcript postprocess (editorial + overrides + hash sync)...")
    run_transcript_postprocess_and_sync(PROJECT_DIR)
    
    if args.stop_after == 2:
        print("\n--- Stopping after Stage 2 ---")
        return 0
    
    # -------------------------------------------------------------------------
    # Stage 3 & 4: Generate + Verify (with second-pass until no corrections needed)
    # -------------------------------------------------------------------------
    # Two-phase episode analysis (Phase-1 JSON + assign_ids) unless explicitly disabled
    if os.getenv("EPISODE_ANALYSIS_TWO_PHASE", "").strip() == "":
        os.environ["EPISODE_ANALYSIS_TWO_PHASE"] = "1"

    os.environ["EPISODE_ANALYSIS_PROJECT"] = "bride_of_charlie"
    os.environ["EPISODE_ANALYSIS_INPUT"] = "transcripts_corrected"
    os.environ["EPISODE_ANALYSIS_OUTPUT"] = "drafts"
    os.environ["EPISODE_ANALYSIS_FORCE"] = "1"
    if os.getenv("NEO4J_URI"):
        os.environ["NEO4J_AUTO_INGEST"] = "true"

    pass_num = 0
    while pass_num < args.max_passes:
        pass_num += 1
        pass_label = f" (pass {pass_num})" if pass_num > 1 else ""

        print("\n" + "=" * 80)
        print(f"STAGE 3: GENERATE EPISODES{pass_label}")
        print("=" * 80)

        print("\n[3.1] Running episode analysis (this may take 1-3 hours)...")
        code = run_python(AGENT_LAB / "agents" / "protocol" / "protocol_agent.py",
                        ["--protocol", "episode_analysis", "--project", "bride_of_charlie", "--force"])

        if code != 0:
            print("\n      ERROR: Episode analysis failed. Check logs/")
            return 1

        draft_count = len(list(drafts_dir.glob("episode_*.md"))) if drafts_dir.exists() else 0
        print(f"\n      ✓ Generated {draft_count} episode draft(s)")

        print("\n[3.2] Fixing ID collisions (post-processing)...")
        run_python(PROJECT_DIR / "scripts" / "fix_collisions.py", ["--drafts", str(drafts_dir)])

        if args.stop_after == 3:
            print("\n--- Stopping after Stage 3 ---")
            return 0

        print("\n" + "=" * 80)
        print(f"STAGE 4: INGEST & VERIFY{pass_label}")
        print("=" * 80)

        print("\n[4.1] Ingesting to Neo4j...")
        code = run_python(PROJECT_DIR / "scripts" / "neo4j_ingest.py", ["--force"])
        if code != 0:
            print("      ⚠ Ingest failed. Is Neo4j running?")

        print("\n[4.2] Verifying drafts (numbering + names)...")
        verify_args = ["--drafts", str(drafts_dir)]
        if args.skip_search:
            verify_args.append("--skip-search")
        code = run_python(PROJECT_DIR / "scripts" / "verify_drafts.py", verify_args)
        if code != 0:
            print("      ⚠ Verification found issues. Review output above.")

        print("\n[4.2b] Importing verify findings into name corrections & rebuilding transcripts_corrected/...")
        corrections_applied = -1
        if (PROJECT_DIR / "scripts" / "neo4j_corrections.py").exists():
            run_python(PROJECT_DIR / "scripts" / "neo4j_corrections.py", ["import-from-verify"])
            corrections_applied = _apply_corrections_count(transcripts_dir, corrected_dir)
            if corrections_applied >= 0:
                if corrections_applied > 0:
                    print(f"      ✓ Rebuilt corrected transcripts ({corrections_applied} replacement(s)); raw unchanged")
                else:
                    print("      ✓ Name corrections updated; corrected files refreshed (no new replacements)")
            else:
                print("      (apply-dir skipped or failed — Neo4j may be unavailable)")
        else:
            print("      (Skipped - neo4j_corrections.py not found)")

        print("\n[4.2c] Transcript postprocess after corrected rebuild...")
        run_transcript_postprocess_and_sync(PROJECT_DIR)

        print("\n[4.3] Merging duplicate nodes...")
        run_python(PROJECT_DIR / "scripts" / "neo4j_merge.py", ["--auto"])

        print("\n[4.4] Validating graph integrity...")
        validate_ok = True
        if os.getenv("NEO4J_URI"):
            vcode = run_python(PROJECT_DIR / "scripts" / "neo4j_validate.py")
            validate_ok = vcode == 0
            if not validate_ok:
                print("      ⚠ Validation found CRITICAL integrity issues.")
            else:
                print("      ✓ Neo4j validate: no CRITICAL issues")
        else:
            print("      (Skipped - NEO4J_URI not set)")

        if args.stop_after == 4:
            print("\n--- Stopping after Stage 4 ---")
            return 0

        stop_green = os.getenv("BRIDE_STOP_AFTER_GREEN_VALIDATE", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if stop_green and validate_ok and os.getenv("NEO4J_URI"):
            print(
                "\n      BRIDE_STOP_AFTER_GREEN_VALIDATE=1: exiting multi-pass loop "
                "(graph clean on CRITICAL checks; name-correction loop skipped even if replacements > 0)."
            )
            break

        # Second pass: if corrections were applied, re-generate from updated transcripts
        if corrections_applied <= 0:
            break
        print(f"\n[4.5] Second pass: {corrections_applied} replacement(s) in transcripts_corrected/ — re-generating drafts...")
    else:
        print(f"\n      Reached max passes ({args.max_passes}); stopping second-pass loop.")
    
    # -------------------------------------------------------------------------
    # Stage 5: Cross-Episode Analysis
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STAGE 5: CROSS-EPISODE ANALYSIS")
    print("=" * 80)
    
    print("\n[5.1] Running cross-episode synthesis...")
    code = run_python(AGENT_LAB / "projects" / "monuments" / "bride_of_charlie" / "scripts" / "run_workflow.py",
                    ["cross"])
    if code != 0:
        print("      ⚠ Cross-episode analysis failed.")
    
    print("\n[5.2] Running pattern detection...")
    patterns_out = PROJECT_DIR / "drafts" / "patterns_report.md"
    run_python(PROJECT_DIR / "scripts" / "neo4j_patterns.py", 
              ["all", "--output", str(patterns_out)])
    
    print("\n[5.3] Generating quality metrics...")
    quality_out = PROJECT_DIR / "drafts" / "quality_report.md"
    run_python(PROJECT_DIR / "scripts" / "neo4j_quality.py",
              ["--output", str(quality_out)])
    
    if args.stop_after == 5:
        print("\n--- Stopping after Stage 5 ---")
        return 0

    # -------------------------------------------------------------------------
    # Stage 5b: Export for inscription (JSON + corrected transcript)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STAGE 5b: EXPORT FOR INSCRIPTION")
    print("=" * 80)
    print("\n[5b.1] Bundling episode JSON + corrected transcripts...")
    export_args = [
        "--drafts",
        str(drafts_dir),
        "--inscription",
        str(PROJECT_DIR / "inscription"),
        "--transcripts",
        str(corrected_dir),
    ]
    if os.getenv("BRIDE_EXPORT_DUAL_TRANSCRIPTS", "").strip().lower() in ("1", "true", "yes"):
        export_args.append("--dual-transcripts")
        if os.getenv("BRIDE_EXPORT_DISPLAY_CLEAN", "").strip().lower() in ("1", "true", "yes"):
            export_args.append("--display-clean")
    run_python(PROJECT_DIR / "scripts" / "export_for_inscription.py", export_args)
    print("      ✓ Inscription-ready files in inscription/")
    if os.getenv("BRIDE_EXPORT_DUAL_TRANSCRIPTS", "").strip().lower() in ("1", "true", "yes"):
        sh_script = PROJECT_DIR / "scripts" / "sync_transcript_hashes.py"
        if sh_script.is_file():
            print("\n[5b.2] sync_transcript_hashes.py (after dual / display export)...")
            run_python(sh_script, [])

    # -------------------------------------------------------------------------
    # Stage 6: Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("STAGE 6: COMPLETE")
    print("=" * 80)
    
    print("\n✓ Workflow complete!")
    print(f"\n  Drafts: {drafts_dir}")
    print(f"  Inscription: {PROJECT_DIR / 'inscription'} (JSON + corrected transcript per episode)")
    print(f"  Patterns report: drafts/patterns_report.md")
    print(f"  Quality report: drafts/quality_report.md")
    print("\n  Next steps:")
    print("    1. Review drafts/ and inscription/")
    print("    2. Run: python scripts/investigative_assistant.py")
    print("    3. Inscribe: inscription/episode_NNN.json + episode_NNN_transcript.txt")
    print("    4. Log changes in protocol_updates/")
    print("\n" + "=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
