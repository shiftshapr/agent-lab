#!/usr/bin/env python3
"""
Bride of Charlie — Review State Tracker & Gap Detector

Tracks review status per episode. State stored in inscription/.review_state.json (simple JSON, no new deps).
Companion to run_workflow.py — gives visibility into what's been generated vs reviewed vs published.

Usage:
    python3 scripts/review_status.py list                    # show all episodes with status
    python3 scripts/review_status.py status <episode>       # show status for one episode  
    python3 scripts/review_status.py approve <episode> [--scope all|artifacts|claims]
    python3 scripts/review_status.py approve-all           # approve ALL episodes in inscription/
    python3 scripts/review_status.py flag <episode> --id <A-####.n> --flag <reason>
    python3 scripts/review_status.py annotate <episode> --id <A-####.n> --note "..."
    python3 scripts/review_status.py pending               # show flagged items across all episodes
    python3 scripts/review_status.py promote <episode>         # copy reviewed episode to output/
    python3 scripts/review_status.py summary                # pipeline stats
    python3 scripts/review_status.py gaps                  # what's missing where
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

INSCRIPTION_DIR = Path(__file__).resolve().parent.parent / "inscription"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRANSCRIPTS_CORR = Path(__file__).resolve().parent.parent / "transcripts_corrected"
TRANSCRIPTS_RAW = Path(__file__).resolve().parent.parent / "transcripts"
REVIEW_FILE = INSCRIPTION_DIR / ".review_state.json"


def utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_state() -> dict:
    if not REVIEW_FILE.exists():
        return {"episodes": {}}
    with open(REVIEW_FILE) as f:
        return json.load(f)


def save_state(state: dict):
    INSCRIPTION_DIR.mkdir(parents=True, exist_ok=True)
    with open(REVIEW_FILE, "w") as f:
        json.dump(state, f, indent=2)


def episode_num(ep_file: Path) -> int:
    """Extract episode number from filename like episode_001_abc.json."""
    name = ep_file.stem  # "episode_001_abc"
    parts = name.split("_")
    return int(parts[1])


def list_episodes():
    state = load_state()
    episodes = {}
    for ep_file in sorted(INSCRIPTION_DIR.glob("episode_*.json")):
        n = episode_num(ep_file)
        review = state.get("episodes", {}).get(str(n), {})
        episodes[n] = {
            "status": review.get("status", "no_review"),
            "reviewed_at": review.get("approved_at", ""),
            "artifacts_approved": len([i for i in review.get("items", {}).values() if i.get("status") == "approved"]),
            "flags": review.get("summary", {}).get("flags", 0),
        }
    
    inscription_count = len(list(INSCRIPTION_DIR.glob("episode_*.json")))
    output_count = len(list(OUTPUT_DIR.glob("episode_*.json")))
    
    print(f"\n{'Episode':<10} {'Status':<15} {'Approved Items':<15} {'Flags':}")
    print("-" * 55)
    for n in sorted(episodes):
        info = episodes[n]
        s = info["status"]
        icon = {"approved": "✅", "rejected": "🚫", "in_review": "📝", "promoted": "📦", "no_review": "  "}.get(s, "  ")
        flags = info["flags"]
        print(f"  Episode {n:<3} {icon} {s:<13} {info['artifacts_approved']:<15} {flags}")
    
    print(f"\n inscription/: {inscription_count} episodes | output/: {output_count} episodes")


def show_status(episode: str):
    ep_file = INSCRIPTION_DIR / f"episode_{int(episode):03d}.json"
    if not ep_file.exists():
        print(f"ERROR: {ep_file.name} not found")
        return
    with open(ep_file) as f:
        data = json.load(f)
    
    state = load_state()
    review = state.get("episodes", {}).get(episode, {})
    s = review.get("status", "no_review")
    icon = {"approved": "✅", "rejected": "🚫", "in_review": "📝", "promoted": "📦", "no_review": "  "}.get(s, "  ")
    
    print(f"\nEpisode {episode}: {icon} {s}")
    if review.get("approved_at"):
        print(f"  Approved: {review['approved_at']} by {review.get('reviewed_by', 'human')}")
    
    # Count from JSON
    artifacts = data.get("artifacts", [])
    claims = data.get("claims", [])
    sub_artifact_count = sum(len(a.get("sub_items", [])) for a in artifacts)
    claim_count = len(claims)
    
    print(f"  Artifacts: {sub_artifact_count} items across {len(artifacts)} families")
    print(f"  Claims: {claim_count}")
    
    summary = review.get("summary", {})
    if summary:
        print(f"\n  Review Summary:")
        print(f"    artifacts approved: {summary.get('artifacts_approved', 0)}/{sub_artifact_count}")
        print(f"    claims approved:   {summary.get('claims_approved', 0)}/{claim_count}")
        print(f"    flags:             {summary.get('flags', 0)}")
    
    items = review.get("items", {})
    if items:
        print(f"\n  Item-level reviews ({len(items)} items):")
        for item_id, item in sorted(items.items()):
            istatus = item.get("status", "pending")
            flag = item.get("flag_type", "")
            icon = {"approved": "✅", "rejected": "❌", "flagged": "🚩", "pending": "⏳"}.get(istatus, " ")
            note = item.get("reviewer_notes", "")
            print(f"    {icon} {item_id}: {istatus}" + (f" [{flag}]" if flag else "") + (f" — {note[:50]}" if note else ""))


def approve_episode(episode: str, scope: str = "all"):
    """Approve all items in an episode (mark reviewed + approved)."""
    ep_file = INSCRIPTION_DIR / f"episode_{int(episode):03d}.json"
    if not ep_file.exists():
        print(f"ERROR: {ep_file.name} not found")
        return 1
    
    with open(ep_file) as f:
        data = json.load(f)
    
    state = load_state()
    ep_state = state.setdefault("episodes", {})[episode] = {
        "status": "approved",
        "approved_at": utcnow(),
        "reviewed_by": "human",
        "items": {},
        "summary": {
            "artifacts_reviewed": 0, "artifacts_approved": 0, "artifacts_rejected": 0,
            "claims_reviewed": 0, "claims_approved": 0, "claims_rejected": 0,
            "flags": 0,
        }
    }
    
    sub_artifact_count = sum(len(a.get("sub_items", [])) for a in data.get("artifacts", []))
    claim_count = len(data.get("claims", []))
    
    if scope in ("all", "artifacts"):
        for a in data.get("artifacts", []):
            for sub in a.get("sub_items", []):
                aid = sub.get("@id", sub.get("ref", ""))
                if aid:
                    ep_state["items"][aid] = {"status": "approved", "reviewed_at": utcnow()}
    if scope in ("all", "claims"):
        for c in data.get("claims", []):
            cid = c.get("@id", "")
            if cid:
                ep_state["items"][cid] = {"status": "approved", "reviewed_at": utcnow()}
    
    summary = ep_state["summary"]
    summary["artifacts_reviewed"] = sub_artifact_count
    summary["claims_reviewed"] = claim_count
    summary["artifacts_approved"] = len([i for i in ep_state["items"].values() if i.get("status") == "approved" and i.get("reviewed_at", "").startswith("A-")])
    summary["claims_approved"] = len([i for i in ep_state["items"].values() if i.get("status") == "approved" and i.get("reviewed_at", "").startswith("C-")])
    
    save_state(state)
    print(f"✅ Episode {episode} approved ({sub_artifact_count} artifact items, {claim_count} claims)")
    return 0


def flag_item(episode: str, item_id: str, flag: str, reason: str = ""):
    """Flag a specific artifact or claim for follow-up."""
    ep_file = INSCRIPTION_DIR / f"episode_{int(episode):03d}.json"
    if not ep_file.exists():
        print(f"ERROR: episode_{episode}.json not found")
        return 1
    
    state = load_state()
    ep_state = state.setdefault("episodes", {}).setdefault(episode, {
        "items": {}, "status": "in_review",
    })
    items = ep_state.setdefault("items", {})
    summary = ep_state.setdefault("summary", {"flags": 0})
    
    items[item_id] = {
        "status": "flagged",
        "flag_type": flag,
        "reviewer_notes": reason,
        "reviewed_at": utcnow(),
    }
    summary["flags"] = summary.get("flags", 0) + 1
    
    if ep_state.get("status") == "no_review":
        ep_state["status"] = "in_review"
    
    save_state(state)
    msg = f"🚩 Episode {episode} item {item_id} flagged: {flag}"
    if reason:
        msg += f" — {reason}"
    print(msg)
    return 0


def annotate_item(episode: str, item_id: str, note: str):
    """Add a reviewer note to a specific item (via flag with 'annotation' type)."""
    ep_file = INSCRIPTION_DIR / f"episode_{int(episode):03d}.json"
    if not ep_file.exists():
        print(f"ERROR: episode_{episode}.json not found")
        return 1

    state = load_state()
    ep_state = state.setdefault("episodes", {}).setdefault(episode, {
        "items": {}, "status": "in_review",
    })
    items = ep_state.setdefault("items", {})

    items[item_id] = {
        "status": "flagged",
        "flag_type": "annotation",
        "reviewer_notes": note,
        "reviewed_at": utcnow(),
    }
    if ep_state.get("status") == "no_review":
        ep_state["status"] = "in_review"

    save_state(state)
    print(f"📝 Annotated {item_id} in episode {episode}: {note[:80]}")
    return 0


def approve_all_episodes():
    """Approve all episodes currently in inscription/."""
    episodes = []
    for ep_file in sorted(INSCRIPTION_DIR.glob("episode_*.json")):
        m = re.search(r"episode_(\d+)", ep_file.stem)
        if m:
            episodes.append(int(m.group(1)))

    if not episodes:
        print("No episodes found in inscription/")
        return

    state = load_state()
    approved_count = 0
    for ep in episodes:
        ep_str = str(ep)
        with open(INSCRIPTION_DIR / f"episode_{ep:03d}.json") as f:
            data = json.load(f)

        ep_state = state.setdefault("episodes", {})[ep_str] = {
            "status": "approved",
            "approved_at": utcnow(),
            "reviewed_by": "human",
            "items": {},
            "summary": {
                "artifacts_reviewed": 0, "artifacts_approved": 0, "artifacts_rejected": 0,
                "claims_reviewed": 0, "claims_approved": 0, "claims_rejected": 0,
                "flags": 0,
            }
        }

        sub_count = sum(len(a.get("sub_items", [])) for a in data.get("artifacts", []))
        claim_count = len(data.get("claims", []))

        for a in data.get("artifacts", []):
            for sub in a.get("sub_items", []):
                aid = sub.get("@id", sub.get("ref", ""))
                if aid:
                    ep_state["items"][aid] = {"status": "approved", "reviewed_at": utcnow()}
        for c in data.get("claims", []):
            cid = c.get("@id", "")
            if cid:
                ep_state["items"][cid] = {"status": "approved", "reviewed_at": utcnow()}

        summary = ep_state["summary"]
        summary["artifacts_reviewed"] = sub_count
        summary["claims_reviewed"] = claim_count
        summary["artifacts_approved"] = sub_count
        summary["claims_approved"] = claim_count
        approved_count += 1

    save_state(state)
    print(f"✅ Approved {approved_count} episodes: {sorted(episodes)}")


def show_pending():
    """Show all flagged items across all episodes."""
    state = load_state()
    episodes = state.get("episodes", {})

    pending_items: list[tuple[int, str, dict]] = []
    for ep_str, ep_data in episodes.items():
        ep = int(ep_str)
        for item_id, item in ep_data.get("items", {}).items():
            if item.get("status") == "flagged":
                pending_items.append((ep, item_id, item))

    if not pending_items:
        print("No flagged items found.")
        return

    print(f"\nFlagged Items ({len(pending_items)} total)")
    print("=" * 80)
    for ep, item_id, item in sorted(pending_items):
        flag_type = item.get("flag_type", "flagged")
        note = item.get("reviewer_notes", "")
        ts = item.get("reviewed_at", "")[:10]
        print(f"  Ep{ep} {item_id} [{flag_type}]")
        if note:
            print(f"    → {note[:100]}")
        print(f"    flagged {ts}")
    print("-" * 80)


def promote_episode(episode: str):
    """"Copy approved inscription JSON to output/."""
    ep_file = INSCRIPTION_DIR / f"episode_{int(episode):03d}.json"
    if not ep_file.exists():
        print(f"ERROR: {ep_file.name} not found")
        return 1
    
    state = load_state()
    review = state.get("episodes", {}).get(episode, {})
    
    if review.get("status") != "approved":
        print(f"ERROR: Episode {episode} is '{review.get('status', 'no_review')}' — must be 'approved' before promoting")
        return 1
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"episode_{episode}.json"
    shutil.copy2(ep_file, out_file)
    
    review["status"] = "promoted"
    review["promoted_at"] = utcnow()
    save_state(state)
    
    print(f"📦 Episode {episode} promoted to output/{out_file.name}")
    return 0


def summary_stats():
    """Pipeline-wide statistics."""
    state = load_state()
    episodes = state.get("episodes", {})
    
    status_counts = {"no_review": 0, "in_review": 0, "approved": 0, "rejected": 0, "promoted": 0}
    for ep_data in episodes.values():
        status_counts[ep_data.get("status", "no_review")] += 1
    
    inscription_count = len(list(INSCRIPTION_DIR.glob("episode_*.json")))
    output_count = len(list(OUTPUT_DIR.glob("episode_*.json")))
    transcript_count = len(list(TRANSCRIPTS_CORR.glob("episode_*.txt")))
    raw_count = len(list(TRANSCRIPTS_RAW.glob("episode_*.txt")))
    
    print(f"\nPipeline Summary:")
    print(f"  transcripts_corrected/: {transcript_count} episodes")
    print(f"  inscription/:     {inscription_count} JSONs")
    print(f"  output/:          {output_count} approved")
    print(f"  Reviews:          {status_counts['approved'] + status_counts['promoted']} approved | {status_counts['in_review']} in_review | {status_counts['no_review']} not started")


def find_gaps():
    """Find what's missing where."""
    inscription_eps = set(episode_num(f) for f in INSCRIPTION_DIR.glob("episode_*.json"))
    output_eps = set(episode_num(f) for f in OUTPUT_DIR.glob("episode_*.json"))
    corrected_eps = set(episode_num(f) for f in TRANSCRIPTS_CORR.glob("episode_*.txt"))
    raw_eps = set(episode_num(f) for f in TRANSCRIPTS_RAW.glob("episode_*.txt"))
    
    state = load_state()
    reviewed_eps = set(int(n) for n in state.get("episodes", {}) if state["episodes"][n].get("status") in ("approved", "promoted"))
    
    all_eps = inscription_eps | corrected_eps | raw_eps
    if not all_eps:
        # Infer from files
        max_ep = max(inscription_eps | corrected_eps | raw_eps, default=0)
        all_eps = set(range(1, max_ep + 1))
    
    missing_transcripts = all_eps - raw_eps
    missing_corrected = all_eps - corrected_eps
    missing_inscription = all_eps - inscription_eps
    missing_output = inscription_eps - output_eps
    missing_review = inscription_eps - reviewed_eps
    
    print(f"\nGap Analysis:")
    if missing_transcripts:
        print(f"  🔴 transcripts/ missing: Episode {sorted(missing_transcripts)}")
    if missing_corrected:
        print(f"  🟡 transcripts_corrected/ missing: Episode {sorted(missing_corrected)}")
    if missing_inscription:
        print(f"  🔴 inscription/ missing: Episode {sorted(missing_inscription)}")
    if missing_output:
        print(f"  🟡 output/ missing (need approval): Episode {sorted(missing_output)}")
    if missing_review:
        print(f"  🟡 inscription/ unreviewed: Episode {sorted(missing_review)}")
    if not any([missing_transcripts, missing_corrected, missing_inscription, missing_output, missing_review]):
        print("  ✅ No gaps — pipeline complete!")


def main():
    parser = argparse.ArgumentParser(description="Brideo of Charlie review state tracker")
    sub = parser.add_subparsers(dest="cmd")
    
    sub.add_parser("list", help="List all episodes with review status")
    sub.add_parser("summary", help="Pipeline-wide statistics")
    sub.add_parser("gaps", help="Find missing episodes across pipeline stages")
    
    p_status = sub.add_parser("status", help="Show detailed status for one episode")
    p_status.add_argument("episode")
    
    p_approve = sub.add_parser("approve", help="Approve an episode (marks all items approved)")
    p_approve.add_argument("episode")
    p_approve.add_argument("--scope", choices=["all", "artifacts", "claims"], default="all")
    
    p_flag = sub.add_parser("flag", help="Flag a specific item")
    p_flag.add_argument("episode")
    p_flag.add_argument("--id", required=True, help="Item ID (e.g. A-1000.1 or C-1001)")
    p_flag.add_argument("--flag", required=True, help="Flag reason (e.g. needs_verification)")
    p_flag.add_argument("--reason", default="", help="Optional notes")
    
    p_promote = sub.add_parser("promote", help="Copy approved episode to output/")
    p_promote.add_argument("episode")

    # New commands
    sub.add_parser("approve-all", help="Approve all episodes in inscription/")
    sub.add_parser("pending", help="Show all flagged items across episodes")

    p_annotate = sub.add_parser("annotate", help="Add reviewer annotation to an item")
    p_annotate.add_argument("episode")
    p_annotate.add_argument("--id", required=True, help="Item ID (e.g. A-1000.1)")
    p_annotate.add_argument("--note", required=True, help="Annotation text")

    args = parser.parse_args()
    if not args.cmd:
        list_episodes()
    elif args.cmd == "list":
        list_episodes()
    elif args.cmd == "summary":
        summary_stats()
    elif args.cmd == "gaps":
        find_gaps()
    elif args.cmd == "status":
        show_status(args.episode)
    elif args.cmd == "approve":
        sys.exit(approve_episode(args.episode, args.scope))
    elif args.cmd == "approve-all":
        approve_all_episodes()
    elif args.cmd == "flag":
        sys.exit(flag_item(args.episode, args.id, args.flag, args.reason))
    elif args.cmd == "annotate":
        sys.exit(annotate_item(args.episode, args.id, args.note))
    elif args.cmd == "pending":
        show_pending()
    elif args.cmd == "promote":
        sys.exit(promote_episode(args.episode))


if __name__ == "__main__":
    main()
