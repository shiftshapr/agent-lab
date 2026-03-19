"""
Run Full Workflow — Bride of Charlie
Executes the ideal workflow from prepare through final reports.

Usage:
  cd ~/workspace/agent-lab/projects/monuments/bride_of_charlie
  python scripts/run_full_workflow.py

  --no-backup       Skip backing up existing drafts
  --skip-search     Skip DuckDuckGo name verification (faster)
  --stop-after N    Stop after stage N (1-6)
  --skip-fetch      Skip transcript fetch (use existing)
  --max-passes N    Max second-pass iterations (default 5)
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


def _apply_corrections_count(transcripts_dir: Path) -> int:
    """Run apply-dir and return number of corrections applied. Returns -1 if skipped."""
    script = PROJECT_DIR / "scripts" / "neo4j_corrections.py"
    if not script.exists():
        return -1
    code, out, _ = run_python_capture(script, ["apply-dir", str(transcripts_dir)])
    if code != 0:
        return -1
    # Parse "✓ Total: N correction(s) across M file(s)"
    m = re.search(r"Total:\s*(\d+)\s+correction", out)
    return int(m.group(1)) if m else 0


def clear_neo4j() -> bool:
    """Clear Neo4j graph, preserving NameCorrection nodes. Returns True if successful."""
    if not os.getenv("NEO4J_URI"):
        return False
    try:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
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
    parser.add_argument("--skip-fetch", action="store_true", help="Skip transcript fetch")
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
    transcripts_dir = PROJECT_DIR / "transcripts"
    
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

    # Apply corrections BEFORE clear — NameCorrection lives in Neo4j; clear wipes it
    print("\n[1.3] Applying name corrections to transcripts...")
    if (PROJECT_DIR / "scripts" / "neo4j_corrections.py").exists():
        code = run_python(PROJECT_DIR / "scripts" / "neo4j_corrections.py",
                         ["apply-dir", str(transcripts_dir)])
        if code != 0:
            print("      (Skipped - Neo4j may not be running; corrections require Neo4j)")
        else:
            print("      ✓ Corrections applied (transcripts updated)")
    else:
        print("      (Skipped - neo4j_corrections.py not found)")

    print("\n[1.4] Clearing Neo4j graph (preserving NameCorrection)...")
    if clear_neo4j():
        print("      ✓ Graph cleared")
    else:
        print("      (Skipped - Neo4j not available or not configured)")
    
    transcript_count = len(list(transcripts_dir.glob("*.txt"))) if transcripts_dir.exists() else 0
    print(f"\n[1.5] Transcripts: {transcript_count} files in transcripts/")
    if transcript_count == 0:
        print("      ERROR: No transcripts found. Run fetch first or add transcripts to transcripts/")
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
    
    if not args.skip_fetch and transcript_count < 7:
        print("\n[2.1] Fetching transcripts...")
        run_python(AGENT_LAB / "projects" / "monuments" / "bride_of_charlie" / "scripts" / "run_workflow.py", 
                  ["fetch"])
    else:
        print("\n[2.1] Skipping fetch (transcripts exist)")
    
    if args.stop_after == 2:
        print("\n--- Stopping after Stage 2 ---")
        return 0
    
    # -------------------------------------------------------------------------
    # Stage 3 & 4: Generate + Verify (with second-pass until no corrections needed)
    # -------------------------------------------------------------------------
    os.environ["EPISODE_ANALYSIS_PROJECT"] = "bride_of_charlie"
    os.environ["EPISODE_ANALYSIS_INPUT"] = "transcripts"
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

        print("\n[4.2b] Importing verify findings into name corrections & re-applying to transcripts...")
        corrections_applied = -1
        if (PROJECT_DIR / "scripts" / "neo4j_corrections.py").exists():
            run_python(PROJECT_DIR / "scripts" / "neo4j_corrections.py", ["import-from-verify"])
            corrections_applied = _apply_corrections_count(transcripts_dir)
            if corrections_applied >= 0:
                if corrections_applied > 0:
                    print(f"      ✓ Applied {corrections_applied} correction(s); transcripts updated")
                else:
                    print("      ✓ Name corrections updated; no transcript changes needed")
            else:
                print("      (apply-dir skipped or failed — Neo4j may be unavailable)")
        else:
            print("      (Skipped - neo4j_corrections.py not found)")

        print("\n[4.3] Merging duplicate nodes...")
        run_python(PROJECT_DIR / "scripts" / "neo4j_merge.py", ["--auto"])

        print("\n[4.4] Validating graph integrity...")
        if os.getenv("NEO4J_URI"):
            code = run_python(PROJECT_DIR / "scripts" / "neo4j_validate.py")
            if code != 0:
                print("      ⚠ Validation found integrity issues.")
        else:
            print("      (Skipped - NEO4J_URI not set)")

        if args.stop_after == 4:
            print("\n--- Stopping after Stage 4 ---")
            return 0

        # Second pass: if corrections were applied, re-generate from updated transcripts
        if corrections_applied <= 0:
            break
        print(f"\n[4.5] Second pass: {corrections_applied} correction(s) applied — re-generating drafts from updated transcripts...")
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
    run_python(PROJECT_DIR / "scripts" / "export_for_inscription.py",
               ["--drafts", str(drafts_dir), "--inscription", str(PROJECT_DIR / "inscription"),
                "--transcripts", str(transcripts_dir)])
    print("      ✓ Inscription-ready files in inscription/")

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
