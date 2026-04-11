#!/usr/bin/env python3
"""
Fine-Grained Annotation Tool — Bride of Charlie

Add or query notes on specific artifact items or claims.
Annotations stored in inscription/.annotations/episode_N.jsonl (one JSON object per line).

Usage:
    # Add annotation
    python3 scripts/annotate_episode.py add 1 --id A-1000.1 --note "Verify hospital record"

    # Add annotation with category
    python3 scripts/annotate_episode.py add 1 --id C-1000 --note "Needs primary source" --category needs_verification

    # Query all annotations for episode 1
    python3 scripts/annotate_episode.py query 1

    # Query annotations for specific item
    python3 scripts/annotate_episode.py query 1 --id A-1000.1

    # List annotations with a specific category
    python3 scripts/annotate_episode.py query 1 --category needs_verification

    # Delete an annotation by ID
    python3 scripts/annotate_episode.py delete 1 --id A-1000.1

    # Export all annotations as JSON
    python3 scripts/annotate_episode.py export 1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
INSCRIPTION_DIR = PROJECT_DIR / "inscription"
ANNOTATIONS_DIR = INSCRIPTION_DIR / ".annotations"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def annotation_file(ep: int) -> Path:
    ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    return ANNOTATIONS_DIR / f"episode_{ep:03d}.jsonl"


def load_annotations(ep: int) -> list[dict]:
    fp = annotation_file(ep)
    if not fp.exists():
        return []
    annotations = []
    with open(fp) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    annotations.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return annotations


def save_annotation(ep: int, annotation: dict) -> None:
    fp = annotation_file(ep)
    with open(fp, "a") as f:
        f.write(json.dumps(annotation, ensure_ascii=False) + "\n")


def next_annotation_id(ep: int, item_id: str) -> int:
    """Generate next sequence number for (episode, item_id)."""
    annotations = load_annotations(ep)
    max_seq = 0
    for ann in annotations:
        if ann.get("item_id") == item_id:
            try:
                seq = int(ann.get("annotation_id", "0").split(".")[-1])
                max_seq = max(max_seq, seq)
            except (ValueError, IndexError):
                pass
    return max_seq + 1


def add_annotation(
    ep: int,
    item_id: str,
    note: str,
    category: str = "general",
    tags: list[str] | None = None,
) -> dict:
    """Add a new annotation to an episode item."""
    seq = next_annotation_id(ep, item_id)
    annotation_id = f"{item_id}.ann{seq}"
    annotation = {
        "annotation_id": annotation_id,
        "item_id": item_id,
        "episode": ep,
        "category": category,
        "note": note,
        "tags": tags or [],
        "created_at": utcnow(),
    }
    save_annotation(ep, annotation)
    return annotation


def query_annotations(
    ep: int,
    item_id: str | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Query annotations with optional filters."""
    annotations = load_annotations(ep)
    results = annotations
    if item_id:
        results = [a for a in results if a.get("item_id") == item_id]
    if category:
        results = [a for a in results if a.get("category") == category]
    if limit:
        results = results[-limit:]
    return results


def delete_annotation(ep: int, item_id: str) -> int:
    """
    Delete all annotations for item_id.
    Returns count of deleted annotations.
    """
    fp = annotation_file(ep)
    annotations = load_annotations(ep)
    remaining = [a for a in annotations if a.get("item_id") != item_id]
    deleted = len(annotations) - len(remaining)
    with open(fp, "w") as f:
        for ann in remaining:
            f.write(json.dumps(ann, ensure_ascii=False) + "\n")
    return deleted


def export_annotations(ep: int) -> dict:
    """Export all annotations for an episode as a structured dict."""
    annotations = load_annotations(ep)
    by_item: dict[str, list[dict]] = {}
    for ann in annotations:
        iid = ann.get("item_id", "unknown")
        by_item.setdefault(iid, []).append(ann)
    return {
        "episode": ep,
        "total_annotations": len(annotations),
        "by_item": by_item,
    }


def validate_item_id(ep: int, item_id: str) -> bool:
    """
    Check if item_id actually exists in the episode JSON.
    Returns True if found, False otherwise.
    """
    ep_file = INSCRIPTION_DIR / f"episode_{ep:03d}.json"
    if not ep_file.exists():
        return False
    with open(ep_file) as f:
        data = json.load(f)

    # Check artifacts
    for a in data.get("artifacts", []):
        for sub in a.get("sub_items", []):
            if sub.get("@id") == item_id or sub.get("ref") == item_id:
                return True
    # Check claims
    for c in data.get("claims", []):
        if c.get("@id") == item_id or c.get("ref") == item_id:
            return True
    # Check nodes
    for n in data.get("nodes", []):
        if n.get("@id") == item_id or n.get("ref") == item_id:
            return True
    # Check memes
    for m in data.get("memes", []):
        if m.get("@id") == item_id or m.get("ref") == item_id:
            return True
    return False


def format_annotation(ann: dict, show_id: bool = True) -> str:
    parts = []
    if show_id:
        parts.append(f"[{ann.get('annotation_id', '?')}]")
    parts.append(f"<{ann.get('item_id')}>")
    cat = ann.get("category", "general")
    if cat != "general":
        parts.append(f"[{cat}]")
    note = ann.get("note", "")
    parts.append(note)
    ts = ann.get("created_at", "")
    if ts:
        parts.append(f"@ {ts[:10]}")
    tags = ann.get("tags", [])
    if tags:
        parts.append(f"tags: {', '.join(tags)}")
    return " ".join(parts)


def cmd_add(args: argparse.Namespace) -> None:
    ep = int(args.episode)
    item_id = args.id

    # Validate item exists
    if not validate_item_id(ep, item_id):
        print(f"[annotate_episode] WARNING: {item_id} not found in episode_{ep:03d}.json — adding anyway (id may be misspelled).")

    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",")]

    ann = add_annotation(ep, item_id, args.note, args.category or "general", tags)
    print(f"✅ Added annotation {ann['annotation_id']}: {ann['note'][:80]}")


def cmd_query(args: argparse.Namespace) -> None:
    ep = int(args.episode)
    item_id = args.id
    category = args.category

    results = query_annotations(ep, item_id=item_id, category=category)
    if not results:
        msg = f"No annotations found"
        if item_id:
            msg += f" for {item_id}"
        if category:
            msg += f" in category '{category}'"
        print(msg)
        return

    print(f"\nAnnotations for Episode {ep}" + (f" ({item_id})" if item_id else ""))
    print("=" * 80)
    for ann in results:
        print(format_annotation(ann))
    print("-" * 80)
    print(f"Total: {len(results)} annotation(s)")


def cmd_delete(args: argparse.Namespace) -> None:
    ep = int(args.episode)
    item_id = args.id
    deleted = delete_annotation(ep, item_id)
    print(f"🗑  Deleted {deleted} annotation(s) for {item_id} in episode {ep}")


def cmd_export(args: argparse.Namespace) -> None:
    ep = int(args.episode)
    data = export_annotations(ep)
    out_path = ANNOTATIONS_DIR / f"episode_{ep:03d}_annotations_export.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"📄 Exported {data['total_annotations']} annotations to {out_path}")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show annotation stats for an episode."""
    ep = int(args.episode)
    annotations = load_annotations(ep)
    if not annotations:
        print(f"No annotations for episode {ep}")
        return

    from collections import Counter
    categories = Counter(a.get("category", "general") for a in annotations)
    items = Counter(a.get("item_id", "?") for a in annotations)

    print(f"\nAnnotation Stats — Episode {ep}")
    print("=" * 50)
    print(f"  Total annotations: {len(annotations)}")
    print(f"  Unique items annotated: {len(items)}")
    print(f"\n  By category:")
    for cat, count in categories.most_common():
        print(f"    {cat}: {count}")
    print(f"\n  Most-annotated items:")
    for item_id, count in items.most_common(5):
        print(f"    {item_id}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-grained annotation tool for Bride of Charlie episodes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a note to an artifact or claim")
    p_add.add_argument("episode", help="Episode number")
    p_add.add_argument("--id", required=True, help="Item ID (e.g. A-1000.1, C-1001, N-2)")
    p_add.add_argument("--note", required=True, help="Annotation text")
    p_add.add_argument("--category", default="general", help="Category (e.g. needs_verification, question, confirmed)")
    p_add.add_argument("--tags", help="Comma-separated tags")

    # query
    p_q = sub.add_parser("query", help="Query annotations")
    p_q.add_argument("episode", help="Episode number")
    p_q.add_argument("--id", help="Filter by item ID")
    p_q.add_argument("--category", help="Filter by category")

    # delete
    p_del = sub.add_parser("delete", help="Delete annotations for an item")
    p_del.add_argument("episode", help="Episode number")
    p_del.add_argument("--id", required=True, help="Item ID to delete annotations for")

    # export
    p_exp = sub.add_parser("export", help="Export annotations as JSON")
    p_exp.add_argument("episode", help="Episode number")

    # stats
    p_stats = sub.add_parser("stats", help="Show annotation statistics")
    p_stats.add_argument("episode", help="Episode number")

    args = parser.parse_args()

    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "query":
        cmd_query(args)
    elif args.cmd == "delete":
        cmd_delete(args)
    elif args.cmd == "export":
        cmd_export(args)
    elif args.cmd == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
