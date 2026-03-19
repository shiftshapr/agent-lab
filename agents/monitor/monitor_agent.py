"""
Monitor Agent — stub
Scans X, LinkedIn, Reddit, Substack, and grant/fellowship sources.
Produces digests, candidate replies, and opportunity lists.

Permissions: read-only. No external write capabilities.

Full implementation planned after base lab is stable.
"""

from __future__ import annotations

from pathlib import Path

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"

SOURCES = [
    "Email (Zoho View MCP)",
    "Calendar (Zoho View MCP)",
    "Slack",
    "X (Twitter)",
    "LinkedIn",
    "Reddit",
    "Substack",
    "Grant / Fellowship databases",
]

OUTPUT_TYPES = [
    "daily_digest",
    "candidate_replies",
    "opportunity_list",
    "trend_summary",
]


def run() -> None:
    print("[monitor-agent] STUB — not yet implemented")
    print("Planned sources:")
    for s in SOURCES:
        print(f"  - {s}")
    print("Planned outputs:")
    for o in OUTPUT_TYPES:
        print(f"  - {o}")


if __name__ == "__main__":
    run()
