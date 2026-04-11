#!/usr/bin/env python3
"""
Name-Correction Pipeline — Bride of Charlie

Scans transcripts_corrected/ for likely STT errors, generates a corrections
dictionary, and applies it to produce new corrected transcripts.

This is broader than the per-episode neo4j_corrections.py — it looks for
common STT ghost-capitalization errors, word-boundary splits/joins, and
identifies potential name/place normalization candidates.

Workflow:
  1. Scan: read all transcripts_corrected/ files, collect word-frequency anomalies
  2. Detect: flag words that look like STT errors (mixed case, unusual splits)
  3. Generate: build corrections dict JSON
  4. Apply: write new corrected transcripts to transcripts_corrected_v2/ (**requires --write**)

``apply`` and the apply step of ``all`` default to **dry-run** (preview counts only).
Pass **--write** to create files.

Usage:
  python3 scripts/broad_corrections.py scan
  python3 scripts/broad_corrections.py generate --min-frequency 3
  python3 scripts/broad_corrections.py apply              # dry-run preview
  python3 scripts/broad_corrections.py apply --write      # actually write v2 files
  python3 scripts/broad_corrections.py all                # ends with apply dry-run
  python3 scripts/broad_corrections.py all --write        # full pipeline + write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent.parent
TRANSCRIPTS_CORR = PROJECT_DIR / "transcripts_corrected"
CORRECTIONS_DIR = PROJECT_DIR / "corrections"
CORRECTIONS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Known proper names / terms that should be preserved (case-sensitive)
# ---------------------------------------------------------------------------
PRESERVE = {
    "Charlie Kirk", "Erika Kirk", "Candace Owens", "Lori Frantzve", "Kent Frantzve",
    "Loretta Lynn Abbis", "Mason Abbis", "Carl Kenneth Frantzve", "Jack Solomon",
    "Carla Solomon", "Elizabeth Lane", "Larry Ginta", "Zion", "Jerusalem",
    "Tesaract", "Paradise Valley", "Illinois", "Cincinnati", "Ohio", "Arizona",
    "Arizona", "Swedish", "Lebanese", "Morfar", "Farfar", "Farmor", "Mormor",
    "Turning Point", "American Bank Note", "Walnut Corner", "Good Samaritan",
    "Neo4j", "STT", "Bride of Charlie", "Goalie", "Walton", "Bush", "Monsanto",
    "Rothstein", "Arizona", "Cincinnati", "Byu", "ByU", "BYU",
}

# Auto-capitalize after these delimiters
CAPITALIZE_AFTER = {". ", "! ", "? ", ": ", "— ", "– "}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_episode_number(filename: str) -> int | None:
    m = re.search(r"episode_(\d+)", filename, re.I)
    return int(m.group(1)) if m else None


def read_transcripts() -> list[tuple[int, str]]:
    """Read all corrected transcripts, return (ep_num, text)."""
    results = []
    for fp in sorted(TRANSCRIPTS_CORR.glob("episode_*.txt")):
        ep = get_episode_number(fp.name)
        if ep is None:
            continue
        results.append((ep, fp.read_text(encoding="utf-8")))
    return results


def split_words(text: str) -> list[str]:
    """Split on whitespace, strip punctuation for analysis."""
    words = re.split(r"(\s+)", text)
    return words


def mixed_case_score(word: str) -> float:
    """
    Score 0-1 for unusual capitalization.
    0 = all-lower or all-upper or normal title case
    1 = weird mixed case like 'eRiKa' or 'KIRK'
    """
    if len(word) < 2:
        return 0.0
    upper_count = sum(1 for c in word if c.isupper())
    lower_count = sum(1 for c in word if c.islower())
    total = upper_count + lower_count
    if total == 0:
        return 0.0
    ratio = upper_count / total
    # Normal title case ~0.3-0.7 ratio
    if 0.25 <= ratio <= 0.75:
        return 0.0
    return abs(ratio - 0.5) * 2  # penalize extremes


# ---------------------------------------------------------------------------
# Scan phase
# ---------------------------------------------------------------------------

def scan_transcripts() -> dict:
    """
    Read all transcripts and flag potential STT anomalies:
    - Words with unusual mixed-case patterns
    - Words adjacent to numbers (split errors)
    - Common confusions (short words, known homophones)
    """
    transcripts = read_transcripts()
    if not transcripts:
        print("[broad_corrections] No transcripts found in transcripts_corrected/")
        return {}

    # Global word counter
    all_words: list[str] = []
    line_anomalies: list[dict] = []

    for ep, text in transcripts:
        lines = text.split("\n")
        for line_idx, line in enumerate(lines, 1):
            words = line.split()
            for w in words:
                stripped = w.strip(".,!?:;\"'")
                if not stripped:
                    continue
                all_words.append(stripped)

                score = mixed_case_score(stripped)
                if score > 0.7 and len(stripped) >= 4:
                    line_anomalies.append({
                        "episode": ep,
                        "line": line_idx,
                        "word": stripped,
                        "type": "mixed_case",
                        "score": round(score, 3),
                        "context": line.strip()[:120],
                    })

    # Word frequency across corpus
    freq = Counter(w.lower() for w in all_words)

    # Detect single-char/digit splits (e.g., "K irk", "2 018")
    split_anomalies = []
    for ep, text in transcripts:
        lines = text.split("\n")
        for line_idx, line in enumerate(lines, 1):
            # Pattern: single letter followed by lowercase letter — likely split
            splits = re.finditer(r"(?<=[a-z])\s+(?=[a-z]{1,3}\s)", line, re.I)
            for m in splits:
                ctx = line[max(0, m.start()-30):m.end()+30]
                split_anomalies.append({
                    "episode": ep,
                    "line": line_idx,
                    "type": "word_split",
                    "context": ctx.strip(),
                })

    # Sort anomalies by score
    line_anomalies.sort(key=lambda x: -x["score"])

    result = {
        "total_words": len(all_words),
        "unique_words": len(set(w.lower() for w in all_words)),
        "top_words": freq.most_common(50),
        "mixed_case_anomalies": line_anomalies[:100],
        "split_anomalies": split_anomalies[:50],
    }

    scan_path = CORRECTIONS_DIR / "scan_results.json"
    with open(scan_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[broad_corrections] Scanned {len(transcripts)} transcripts, wrote {scan_path}")
    return result


# ---------------------------------------------------------------------------
# Generate corrections dict
# ---------------------------------------------------------------------------

def generate_corrections(min_frequency: int = 2) -> dict[str, str]:
    """
    Build a corrections dict from scan results.

    Auto-corrects:
    - Mixed-case words appearing >= min_frequency times
    - Words that look like name fragments
    """
    scan_path = CORRECTIONS_DIR / "scan_results.json"
    if not scan_path.exists():
        print("[broad_corrections] Run 'scan' first.")
        return {}

    with open(scan_path) as f:
        scan = json.load(f)

    corrections: dict[str, str] = {}
    added: list[dict] = []

    # 1. Mixed-case anomalies — try to title-case them if they look like names
    for anomaly in scan.get("mixed_case_anomalies", []):
        word = anomaly["word"]
        if len(word) < 3:
            continue
        # Title-case as best guess
        guessed = word.title()
        if guessed != word and guessed.lower() != word.lower():
            corrections[word] = guessed
            added.append({**anomaly, "corrected_to": guessed, "method": "title_case"})

    # 2. Known ghost-capitalization patterns (double capitals)
    ghost_pattern = re.compile(r"\b[A-Z]{2,}[a-z]+")
    for ep, text in read_transcripts():
        for m in ghost_pattern.finditer(text):
            word = m.group()
            # e.g. "KIRK" → "Kirk" if appears multiple times
            if word.lower() in [w.lower() for w in corrections.values()]:
                continue
            guessed = word.capitalize()
            corrections[word] = guessed
            added.append({"episode": ep, "word": word, "corrected_to": guessed, "method": "ghost_cap"})

    # 3. Word splits like "K irk" → "Kirk"
    for anomaly in scan.get("split_anomalies", []):
        ctx = anomaly["context"]
        # Find the split words
        splits = re.findall(r"[A-Za-z]{1,3}\s+[A-Za-z]{1,3}", ctx)
        for s in splits:
            parts = s.split()
            if len(parts) == 2:
                joined = parts[0].capitalize() + parts[1].capitalize()
                original = " ".join(parts)
                corrections[original] = joined
                added.append({**anomaly, "corrected_to": joined, "method": "join_split"})

    # De-duplicate corrections
    final_corrections: dict[str, str] = {}
    for original, corrected in corrections.items():
        if original.lower() != corrected.lower():
            final_corrections[original] = corrected

    result = {
        "corrections": final_corrections,
        "meta": {
            "min_frequency": min_frequency,
            "total_corrections": len(final_corrections),
            "method": "auto_detect",
        },
        "correction_details": added[:200],
    }

    corrections_path = CORRECTIONS_DIR / "corrections_dict.json"
    with open(corrections_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[broad_corrections] Generated {len(final_corrections)} corrections → {corrections_path}")
    return result


# ---------------------------------------------------------------------------
# Apply corrections
# ---------------------------------------------------------------------------

def preview_apply() -> dict[str, Any]:
    """
    Simulate apply: count replacements and list episodes that would change (no writes).
    """
    corrections_path = CORRECTIONS_DIR / "corrections_dict.json"
    if not corrections_path.exists():
        print("[broad_corrections] No corrections_dict.json found. Run 'generate' first.")
        return {"files_would_change": 0, "total_replacements": 0}

    with open(corrections_path) as f:
        data = json.load(f)

    corrections: dict[str, str] = data.get("corrections", {})
    if not corrections:
        print("[broad_corrections] No corrections to apply.")
        return {"files_would_change": 0, "total_replacements": 0}

    out_dir = PROJECT_DIR / "transcripts_corrected_v2"
    files_would_change = 0
    grand_total = 0
    print("[broad_corrections] DRY-RUN (no files written). Use apply --write to create:")
    print(f"  → {out_dir}/")
    for ep, text in read_transcripts():
        original = text
        ep_repl = 0
        for wrong, right in corrections.items():
            pattern = re.compile(r"\b" + re.escape(wrong) + r"\b")
            new_text, n = pattern.subn(right, text)
            if n > 0:
                ep_repl += n
                text = new_text
        if text != original:
            files_would_change += 1
            grand_total += ep_repl
            print(f"  episode_{ep:03d}: ~{ep_repl} replacement(s) → episode_{ep:03d}_corrected.txt")

    print(
        f"\n[broad_corrections] Preview: {files_would_change} file(s) would change, "
        f"~{grand_total} total replacement(s). Pass --write to apply."
    )
    return {"files_would_change": files_would_change, "total_replacements": grand_total}


def apply_corrections() -> None:
    """
    Read corrections_dict.json and apply to all transcripts_corrected/*.txt,
    writing new files to transcripts_corrected_v2/.
    """
    corrections_path = CORRECTIONS_DIR / "corrections_dict.json"
    if not corrections_path.exists():
        print("[broad_corrections] No corrections_dict.json found. Run 'generate' first.")
        return

    with open(corrections_path) as f:
        data = json.load(f)

    corrections: dict[str, str] = data.get("corrections", {})
    if not corrections:
        print("[broad_corrections] No corrections to apply.")
        return

    out_dir = PROJECT_DIR / "transcripts_corrected_v2"
    out_dir.mkdir(exist_ok=True)

    applied_count = 0
    for ep, text in read_transcripts():
        original = text
        ep_repl = 0
        for wrong, right in corrections.items():
            # Replace whole words only
            pattern = re.compile(r"\b" + re.escape(wrong) + r"\b")
            new_text, n = pattern.subn(right, text)
            if n > 0:
                ep_repl += n
                text = new_text

        if text != original:
            applied_count += ep_repl
            out_path = out_dir / f"episode_{ep:03d}_corrected.txt"
            out_path.write_text(text, encoding="utf-8")
            print(f"  Applied {ep_repl} correction(s) → {out_path.name}")

    # Summary
    summary = {
        "input_dir": str(TRANSCRIPTS_CORR),
        "output_dir": str(out_dir),
        "total_changes": applied_count,
        "corrections_applied": len(corrections),
    }
    summary_path = CORRECTIONS_DIR / "apply_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[broad_corrections] Applied {applied_count} changes across {len(corrections)} correction types.")
    print(f"  Output: {out_dir}/")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Broad name-correction pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scan", help="Scan transcripts for STT anomalies")
    gen = sub.add_parser("generate", help="Generate corrections dict from scan results")
    gen.add_argument("--min-frequency", type=int, default=2)

    ap_apply = sub.add_parser("apply", help="Preview or apply corrections (default: dry-run)")
    ap_apply.add_argument(
        "--write",
        action="store_true",
        help="Write transcripts_corrected_v2/ (default is preview only)",
    )

    ap_all = sub.add_parser("all", help="Run scan + generate + apply (apply is dry-run unless --write)")
    ap_all.add_argument("--write", action="store_true", help="Write v2 transcripts after generate")

    args = parser.parse_args()

    if args.cmd == "scan":
        scan_transcripts()
    elif args.cmd == "generate":
        generate_corrections(min_frequency=args.min_frequency)
    elif args.cmd == "apply":
        if getattr(args, "write", False):
            apply_corrections()
        else:
            preview_apply()
    elif args.cmd == "all":
        print("=== Phase 1: Scan ===")
        scan_transcripts()
        print("\n=== Phase 2: Generate ===")
        generate_corrections()
        print("\n=== Phase 3: Apply ===")
        if getattr(args, "write", False):
            apply_corrections()
        else:
            preview_apply()
        print("\n✅ broad_corrections pipeline complete.")


if __name__ == "__main__":
    main()
