#!/usr/bin/env python3
"""
Check Substack (and optionally LinkedIn) for unreplied comments.
Outputs context for the agent to draft responses. CTAs from shiftshapr_context.json.

Usage:
  python scripts/check-replies.py                    # List unreplied (from cache)
  python scripts/check-replies.py --fetch            # Fetch comments first, then list
  python scripts/check-replies.py --fetch --json      # JSON output for agent
  python scripts/check-replies.py --publication gometa

Run from agent-lab root. Requires .env (LINKEDIN_STORAGE_STATE for fetch).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AGENT_LAB_ROOT = SCRIPT_DIR.parent


def _load_env() -> None:
    env_path = AGENT_LAB_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def _load_context() -> dict:
    path = AGENT_LAB_ROOT / "data" / "shiftshapr_context.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_ctas(ctx: dict) -> list[dict]:
    return ctx.get("ctas", [
        {"id": "post-ai-doc", "name": "Post-AI DOC Zoom", "slug": "lu.ma/ai-doc", "when": "governance, AI, trust"},
        {"id": "canopi-waitlist", "name": "Canopi waiting list", "slug": "join Canopi waitlist", "when": "collaboration, meta-layer"},
        {"id": "civic-mason", "name": "Civic Mason badge", "slug": "earn a Civic Mason badge", "when": "civic, governance"},
    ])


def main() -> None:
    _load_env()
    parser = argparse.ArgumentParser(description="Check for unreplied Substack comments")
    parser.add_argument("--fetch", action="store_true", help="Fetch comments from Substack (Playwright)")
    parser.add_argument("--publication", default="metaweb", help="Publication id (gometa, metaweb, canopi, etc.)")
    parser.add_argument("--json", action="store_true", help="Output JSON for agent consumption")
    args = parser.parse_args()

    # Ensure we can import from apps.draft_editor
    if str(AGENT_LAB_ROOT) not in sys.path:
        sys.path.insert(0, str(AGENT_LAB_ROOT))

    if args.fetch:
        from apps.draft_editor.substack_comments import fetch_all_comments, load_replies_cache, save_replies_cache
        try:
            comments = fetch_all_comments(args.publication)
            cache = load_replies_cache()
            replied = cache.get("replied_ids", [])
            save_replies_cache(comments, replied)
            if not args.json:
                print(f"Fetched {len(comments)} comments from {args.publication}", file=sys.stderr)
        except Exception as e:
            print(f"Fetch failed: {e}", file=sys.stderr)
            sys.exit(1)

    from apps.draft_editor.substack_comments import load_replies_cache
    from apps.draft_editor.store import list_reply_drafts

    cache = load_replies_cache()
    comments = cache.get("comments", [])
    replied_ids = set(cache.get("replied_ids", []))
    reply_drafts = list_reply_drafts()
    draft_by_comment = {d.get("metadata", {}).get("parent_comment_id"): d for d in reply_drafts}
    unreplied = [c for c in comments if c.get("id") not in replied_ids and c.get("id") not in draft_by_comment]

    ctx = _load_context()
    ctas = _get_ctas(ctx)

    if args.json:
        out = {
            "unreplied": unreplied,
            "total_comments": len(comments),
            "reply_drafts_count": len(reply_drafts),
            "ctas": ctas,
            "publication": args.publication,
        }
        print(json.dumps(out, indent=2))
        return

    # Human-readable
    print("# Unreplied comments\n")
    print(f"Publication: {args.publication}")
    print(f"Total comments in cache: {len(comments)}")
    print(f"Unreplied: {len(unreplied)}")
    print(f"Reply drafts: {len(reply_drafts)}\n")

    print("## Current CTAs (use when drafting replies)")
    for cta in ctas:
        print(f"- **{cta.get('name')}** ({cta.get('slug')}): {cta.get('when')}")

    if unreplied:
        print("\n## Unreplied comments\n")
        for c in unreplied:
            print(f"### {c.get('post_title', '')[:50]} — {c.get('author')}")
            print(f"Post: {c.get('post_url')}")
            print(f"Comment: {c.get('text', '')[:300]}...")
            print(f"ID: {c.get('id')}\n")
    else:
        print("\nNo unreplied comments.")


if __name__ == "__main__":
    main()
