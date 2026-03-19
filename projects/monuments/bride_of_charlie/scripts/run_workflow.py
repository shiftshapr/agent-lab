"""
Bride of Charlie Workflow Runner

Orchestrates:
  1. Fetch transcripts from YouTube
  2. Run protocol on episodes (in order) -> drafts/
  3. Verify drafts (numbering audit + name spelling check)
  4. Cross-episode analysis -> drafts/
  5. Validate graph integrity (Neo4j, optional)
  6. Log protocol updates to protocol_updates/

Usage:
  cd ~/workspace/agent-lab
  uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/run_workflow.py [step]

Steps: fetch | episodes | verify | cross | validate | all (default: all)
  --force        Re-run episode analysis even if drafts exist (use when drafts are wrong/incomplete)
  --skip-search  Skip name spelling verification via DuckDuckGo
  --validate     Run Neo4j integrity validation after workflow completes
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# run_workflow.py is at projects/monuments/bride_of_charlie/scripts/
AGENT_LAB = Path(__file__).resolve().parent.parent.parent.parent.parent
PROJECT_DIR = Path(__file__).resolve().parent.parent
UV_CMD = ["uv", "run", "--project", str(AGENT_LAB / "framework" / "deer-flow" / "backend")]


def run(cmd: list[str], cwd: Path) -> int:
    return subprocess.run(cmd, cwd=cwd).returncode


def step_fetch() -> int:
    print("\n--- Step 1: Fetch transcripts ---")
    return run(
        UV_CMD + ["python", str(PROJECT_DIR / "scripts" / "fetch_transcripts.py")],
        cwd=AGENT_LAB,
    )


def step_episodes(force: bool = False) -> int:
    print("\n--- Step 2: Run protocol on episodes -> drafts ---")
    os.environ["EPISODE_ANALYSIS_PROJECT"] = "bride_of_charlie"
    os.environ["EPISODE_ANALYSIS_INPUT"] = "transcripts"
    os.environ["EPISODE_ANALYSIS_OUTPUT"] = "drafts"
    if force:
        os.environ["EPISODE_ANALYSIS_FORCE"] = "1"
    protocol_agent = AGENT_LAB / "agents" / "protocol" / "protocol_agent.py"
    cmd = UV_CMD + [
        "python", str(protocol_agent),
        "--protocol", "episode_analysis",
        "--project", "bride_of_charlie",
    ]
    if force:
        cmd.append("--force")
    return run(cmd, cwd=AGENT_LAB)


def step_verify(skip_search: bool = False) -> int:
    print("\n--- Step 3: Verify drafts (numbering + names) ---")
    cmd = UV_CMD + ["python", str(PROJECT_DIR / "scripts" / "verify_drafts.py")]
    if skip_search:
        cmd.append("--skip-search")
    return run(cmd, cwd=AGENT_LAB)


def step_cross() -> int:
    print("\n--- Step 4: Cross-episode analysis -> drafts ---")
    return run(
        UV_CMD + [
            "python", str(PROJECT_DIR / "scripts" / "cross_episode_analysis.py"),
        ],
        cwd=AGENT_LAB,
    )


def step_validate() -> int:
    print("\n--- Step 5: Validate graph integrity (Neo4j) ---")
    neo4j_uri = os.getenv("NEO4J_URI")
    if not neo4j_uri:
        print("  Skipping: NEO4J_URI not set")
        return 0
    return run(
        UV_CMD + ["python", str(PROJECT_DIR / "scripts" / "neo4j_validate.py")],
        cwd=AGENT_LAB,
    )


def main() -> None:
    argv = [a.lower() for a in sys.argv[1:]]
    force = "--force" in argv
    skip_search = "--skip-search" in argv
    validate = "--validate" in argv
    step = next(
        (a for a in argv if a not in ("--force", "--skip-search", "--validate")),
        "all",
    )

    if step == "fetch":
        sys.exit(step_fetch())
    if step == "episodes":
        sys.exit(step_episodes(force=force))
    if step == "verify":
        sys.exit(step_verify(skip_search=skip_search))
    if step == "cross":
        sys.exit(step_cross())
    if step == "validate":
        sys.exit(step_validate())
    if step == "all":
        # Skip fetch — transcripts already exist; avoid using TranscriptAPI credits
        if step_episodes(force=force) != 0:
            sys.exit(1)
        if step_verify(skip_search=skip_search) != 0:
            sys.exit(1)
        if step_cross() != 0:
            sys.exit(1)
        if validate:
            if step_validate() != 0:
                sys.exit(1)
        print("\n--- Workflow complete. Review drafts/, then log changes in protocol_updates/ ---")
        sys.exit(0)

    print("Usage: run_workflow.py [fetch|episodes|verify|cross|validate|all] [--force] [--skip-search] [--validate]")
    sys.exit(1)


if __name__ == "__main__":
    main()
