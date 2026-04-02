"""
Drafting Agent — voice-based drafts for Substack, grants, etc.

Writes in consistent voices for each project.
Drafts Substack posts, social replies, event copy, and grant/fellowship answers.

Permissions: no external write, no publish.
Voice profiles loaded from voices/ directory.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
VOICES_DIR = AGENT_LAB_ROOT / "voices"
SCRIPTS_DIR = AGENT_LAB_ROOT / "scripts"

VOICE_FILES = {
    "meta_layer": "meta_layer_voice.md",
    "canopi": "canopi_voice.md",
    "substack": "substack_voice.md",
    "grant": "grant_voice.md",
}

# Draft type -> voice profile
DRAFT_VOICE = {
    "substack_post": "substack",
    "social_reply": "canopi",
    "event_copy": "canopi",
    "grant_answer": "grant",
    "fellowship_answer": "grant",
}

DRAFT_TYPES = list(DRAFT_VOICE.keys())


def load_voice(name: str) -> str:
    filename = VOICE_FILES.get(name)
    if not filename:
        raise ValueError(f"Unknown voice profile: {name}")
    path = VOICES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Voice profile not found: {path}")
    return path.read_text(encoding="utf-8")


def _run_deerflow(prompt: str, timeout: int = 300) -> str:
    """Invoke DeerFlow for draft generation."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "run-deerflow-task.py"), prompt, "--timeout", str(timeout)],
        cwd=str(AGENT_LAB_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout + 30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"DeerFlow failed: {result.stderr[:500]}")
    return result.stdout.strip()


def draft(draft_type: str, context: str, output_path: Path | None = None) -> str:
    """
    Generate a draft using the appropriate voice profile.

    Args:
        draft_type: substack_post, grant_answer, fellowship_answer, etc.
        context: User's topic, notes, or source material
        output_path: Optional file to write the draft to

    Returns:
        The generated draft text
    """
    voice_name = DRAFT_VOICE.get(draft_type, "substack")
    voice_content = load_voice(voice_name)

    type_instructions = {
        "substack_post": "Write a Substack post or newsletter essay. Include a compelling title and 2–4 sections.",
        "grant_answer": "Write a grant application answer. Be specific about outcomes, timeline, and evidence.",
        "fellowship_answer": "Write a fellowship application answer. Emphasize impact and fit.",
        "social_reply": "Write a concise social media reply. Match platform tone.",
        "event_copy": "Write event description or announcement copy.",
    }
    instructions = type_instructions.get(draft_type, "Write the requested content.")

    prompt = f"""You are a drafting assistant. Write in the voice defined below.

## Voice profile (follow closely)
{voice_content}

## Task
{instructions}

## Context / source material
{context}

Produce the draft. Output only the draft content, no meta-commentary."""

    text = _run_deerflow(prompt, timeout=420)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
        print(f"[drafting-agent] Wrote {len(text)} chars to {output_path}", file=sys.stderr)
    return text


def run() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Drafting Agent — voice-based drafts")
    parser.add_argument("--type", "-t", choices=DRAFT_TYPES, help="Draft type")
    parser.add_argument("--context", "-c", default="", help="Topic, notes, or source material")
    parser.add_argument("--output", "-o", type=Path, help="Write draft to file")
    parser.add_argument("--list", action="store_true", help="List voice profiles and draft types")
    args = parser.parse_args()

    if args.list:
        print("Voice profiles:")
        for name, filename in VOICE_FILES.items():
            path = VOICES_DIR / filename
            status = "present" if path.exists() else "MISSING"
            print(f"  - {name}: {filename} [{status}]")
        print("Draft types:")
        for d in DRAFT_TYPES:
            print(f"  - {d} -> {DRAFT_VOICE[d]}")
        return

    if not args.type:
        parser.error("--type is required (or use --list to see options)")

    context = args.context or sys.stdin.read() if not sys.stdin.isatty() else ""
    if not context.strip():
        print("[drafting-agent] Provide --context or pipe content via stdin", file=sys.stderr)
        sys.exit(1)

    try:
        draft(args.type, context, args.output)
    except Exception as e:
        print(f"[drafting-agent] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
