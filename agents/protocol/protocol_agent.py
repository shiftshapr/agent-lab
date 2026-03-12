"""
Protocol Agent
Discovers and executes protocol definitions in the protocols/ directory.
Currently supports: transcript protocol.

Usage:
    python agents/protocol/protocol_agent.py [--protocol transcript]
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

PROTOCOLS_DIR = Path(__file__).parent.parent.parent / "protocols"
AGENTS_DIR    = Path(__file__).parent


def run_protocol(name: str, project: str | None = None) -> None:
    protocol_path = PROTOCOLS_DIR / name / f"{name}_protocol.py"

    if not protocol_path.exists():
        print(f"[protocol-agent] No protocol found at: {protocol_path}")
        sys.exit(1)

    if project:
        os.environ["EPISODE_ANALYSIS_PROJECT"] = project

    print(f"[protocol-agent] Loading protocol: {name}")
    spec   = importlib.util.spec_from_file_location(f"{name}_protocol", protocol_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    runner = getattr(module, f"run_{name.replace('-', '_')}_protocol", None)
    if runner is None:
        print(f"[protocol-agent] Protocol module missing run_{name}_protocol()")
        sys.exit(1)

    print(f"[protocol-agent] Executing {name} protocol…")
    runner()
    print(f"[protocol-agent] Protocol complete: {name}")


def list_protocols() -> list[str]:
    return [
        d.name
        for d in PROTOCOLS_DIR.iterdir()
        if d.is_dir() and (d / f"{d.name}_protocol.py").exists()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Protocol Agent — runs structured workflows")
    parser.add_argument(
        "--protocol",
        default="transcript",
        help="Name of the protocol to run (default: transcript)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available protocols and exit",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Project name for episode_analysis (e.g. bride_of_charlie)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run episode analysis even if drafts exist (EPISODE_ANALYSIS_FORCE=1)",
    )
    args = parser.parse_args()

    if args.force:
        os.environ["EPISODE_ANALYSIS_FORCE"] = "1"

    if args.list:
        protocols = list_protocols()
        if protocols:
            print("Available protocols:")
            for p in protocols:
                print(f"  - {p}")
        else:
            print("No protocols found.")
        return

    run_protocol(args.protocol, project=args.project)


if __name__ == "__main__":
    main()
