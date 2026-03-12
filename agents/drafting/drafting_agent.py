"""
Drafting Agent — stub
Writes in consistent voices for each project.
Drafts Substack posts, social replies, event copy, and grant/fellowship answers.

Permissions: no external write, no publish.
Voice profiles loaded from voices/ directory.

Full implementation planned after base lab is stable.
"""

from __future__ import annotations

from pathlib import Path

VOICES_DIR = Path(__file__).parent.parent.parent / "voices"

VOICE_FILES = {
    "meta_layer":  "meta_layer_voice.md",
    "canopi":      "canopi_voice.md",
    "substack":    "substack_voice.md",
    "grant":       "grant_voice.md",
}

DRAFT_TYPES = [
    "substack_post",
    "social_reply",
    "event_copy",
    "grant_answer",
    "fellowship_answer",
]


def load_voice(name: str) -> str:
    filename = VOICE_FILES.get(name)
    if not filename:
        raise ValueError(f"Unknown voice profile: {name}")
    path = VOICES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Voice profile not found: {path}")
    return path.read_text(encoding="utf-8")


def run() -> None:
    print("[drafting-agent] STUB — not yet implemented")
    print("Available voice profiles:")
    for name, filename in VOICE_FILES.items():
        path = VOICES_DIR / filename
        status = "present" if path.exists() else "MISSING"
        print(f"  - {name}: {filename} [{status}]")
    print("Planned draft types:")
    for d in DRAFT_TYPES:
        print(f"  - {d}")


if __name__ == "__main__":
    run()
