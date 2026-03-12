"""
Publish Agent — stub
The ONLY agent with external write/publish capabilities.
Dormant by default. Only activated by explicit human command.

Rules (hard-coded, not configurable):
  - No background autonomous publishing
  - No delete by default
  - No archive by default
  - All actions logged to logs/publish_audit.log
  - Only receives content that has passed Risk Reviewer

Full implementation planned after base lab is stable and Risk Reviewer is active.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

LOGS_DIR   = Path(__file__).parent.parent.parent / "logs"
AUDIT_LOG  = LOGS_DIR / "publish_audit.log"

ACTIVE = False  # Only set True by explicit human activation command


def _log_action(action: str, details: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        **details,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def activate() -> None:
    """Explicit human activation. Must be called deliberately."""
    global ACTIVE
    ACTIVE = True
    _log_action("ACTIVATED", {"by": "human"})
    print("[publish-agent] Activated. Publishing enabled.")


def publish(content: str, platform: str, draft_only: bool = True) -> None:
    if not ACTIVE:
        raise RuntimeError(
            "[publish-agent] Cannot publish — agent is dormant. "
            "Call activate() first with explicit human approval."
        )
    mode = "DRAFT" if draft_only else "PUBLISH"
    _log_action(mode, {"platform": platform, "content_preview": content[:120]})
    print(f"[publish-agent] {mode} → {platform}: {content[:80]}…")


def run() -> None:
    print("[publish-agent] STUB — dormant by default")
    print(f"  Active: {ACTIVE}")
    print("  Rules: no background publishing, no delete, all actions logged")
    print("  Activation: requires explicit human command")


if __name__ == "__main__":
    run()
