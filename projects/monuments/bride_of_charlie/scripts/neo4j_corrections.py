"""
Neo4j Name Correction Dictionary
Stores verified name corrections and writes corrected transcript copies.

Raw transcripts in transcripts/ are never modified. Outputs go to transcripts_corrected/
(by default) so fetch/source text stays canonical.

Usage:
    # Add correction
    python scripts/neo4j_corrections.py add "Tyler Boyer" "Tyler Bowyer" --confidence high

    # List corrections
    python scripts/neo4j_corrections.py list

    # Apply corrections: writes transcripts_corrected/episode_*.txt (never overwrites raw)
    python scripts/neo4j_corrections.py apply transcripts/episode_001.txt

    # Apply all raw -> corrected directory
    python scripts/neo4j_corrections.py apply-dir transcripts/

    # Import from verify_drafts results
    python scripts/neo4j_corrections.py import-from-verify

    # Remove one bad pair (exact incorrect string)
    python scripts/neo4j_corrections.py remove "Kent France"

    # Wipe bad dictionary (then re-import / re-apply)
    python scripts/neo4j_corrections.py clear-all --yes
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")


def default_corrected_path(raw_path: Path) -> Path:
    """Map raw transcript path to default output path (never the raw file)."""
    if raw_path.parent.name == "transcripts":
        return raw_path.parent.parent / "transcripts_corrected" / raw_path.name
    return raw_path.parent / f"{raw_path.stem}_corrected{raw_path.suffix}"


def default_output_dir_for_apply_dir(input_dir: Path) -> Path:
    """Sibling transcripts_corrected/ when input is .../transcripts/."""
    if input_dir.name == "transcripts":
        return input_dir.parent / "transcripts_corrected"
    return input_dir.parent / f"{input_dir.name}_corrected"


def is_sane_name_correction(incorrect: str, correct: str) -> tuple[bool, str]:
    """
    Block pathological incorrect→correct pairs that destroy transcripts
    (e.g. short name → long draft fragment, stutter phrases).
    """
    inc = (incorrect or "").strip()
    cor = (correct or "").strip()
    if len(cor) > max(100, len(inc) * 5):
        return False, "correct text far longer than incorrect (likely non-name fragment)"
    tp = len(re.findall(r"turning\s+point", cor, re.I))
    if tp >= 3 and len(inc) <= 24:
        return False, "too many 'Turning Point' mentions for a short incorrect string"
    # Detect stutter: same 3-word phrase repeated
    w = cor.split()
    if len(w) >= 9:
        for i in range(len(w) - 2):
            tri = " ".join(w[i : i + 3]).lower()
            if len(tri) < 8:
                continue
            if cor.lower().count(tri) >= 4:
                return False, "repeated 3-word phrase in correct (stutter)"
    return True, ""


class CorrectionManager:
    """Manages name corrections in Neo4j."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def close(self):
        self.driver.close()
    
    def add_correction(
        self,
        incorrect: str,
        correct: str,
        confidence: str = "high",
        source: str = "manual",
        context: str = "",
        *,
        skip_sanity: bool = False,
    ) -> bool:
        """
        Add a name correction to the dictionary.
        Returns True if stored, False if skipped (unsafe pair or empty).
        """
        inc = (incorrect or "").strip()
        cor = (correct or "").strip()
        if not inc or inc == cor:
            return False
        if not skip_sanity:
            ok, reason = is_sane_name_correction(inc, cor)
            if not ok:
                preview = cor if len(cor) <= 80 else cor[:80] + "..."
                print(f"✗ Skipped unsafe correction: '{inc}' → '{preview}' ({reason})")
                return False
        with self.driver.session() as session:
            session.run("""
                MERGE (nc:NameCorrection {incorrect: $incorrect})
                SET nc.correct = $correct,
                    nc.confidence = $confidence,
                    nc.source = $source,
                    nc.context = $context,
                    nc.added_date = date(),
                    nc.updated_at = datetime()
            """, incorrect=inc, correct=cor, confidence=confidence,
                source=source, context=context)

            print(f"✓ Added correction: '{inc}' → '{cor}' (confidence: {confidence})")
        return True
    
    def list_corrections(self, confidence_filter: str | None = None) -> list[dict]:
        """List all corrections, optionally filtered by confidence."""
        with self.driver.session() as session:
            query = "MATCH (nc:NameCorrection) "
            if confidence_filter:
                query += f"WHERE nc.confidence = '{confidence_filter}' "
            query += (
                "RETURN nc.incorrect AS incorrect, nc.correct AS correct, "
                "nc.confidence AS confidence, nc.source AS source, nc.added_date AS added_date "
                "ORDER BY added_date DESC"
            )
            
            result = session.run(query)
            return [dict(record) for record in result]
    
    def apply_to_text(self, text: str, confidence_threshold: str = "medium") -> tuple[str, list[str]]:
        """
        Apply all corrections to text.
        Returns: (corrected_text, list of corrections applied)
        """
        confidence_levels = {"high": 3, "medium": 2, "low": 1}
        threshold = confidence_levels.get(confidence_threshold, 2)
        
        corrections_applied = []
        
        try:
            self.driver.verify_connectivity()
        except Exception:
            return text, []
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (nc:NameCorrection)
                WHERE CASE nc.confidence
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 1
                    ELSE 0
                END >= $threshold
                RETURN nc.incorrect AS incorrect, nc.correct AS correct, nc.confidence AS confidence
                ORDER BY size(nc.incorrect) DESC
            """, threshold=threshold)
            
            for record in result:
                incorrect = record["incorrect"]
                correct = record["correct"]
                if not incorrect or not correct:
                    continue
                if not is_sane_name_correction(str(incorrect), str(correct))[0]:
                    continue
                if incorrect in text:
                    text = text.replace(incorrect, correct)
                    corrections_applied.append(f"{incorrect} → {correct}")
        
        return text, corrections_applied

    def remove_correction(self, incorrect: str) -> int:
        """Delete NameCorrection node(s) with this exact `incorrect` string. Returns count removed."""
        inc = (incorrect or "").strip()
        if not inc:
            return 0
        with self.driver.session() as session:
            rec = session.run(
                "MATCH (nc:NameCorrection {incorrect: $i}) RETURN count(nc) AS c",
                i=inc,
            ).single()
            n = int(rec["c"]) if rec and rec["c"] is not None else 0
            if n == 0:
                print(f"(no NameCorrection for incorrect={inc!r})")
                return 0
            session.run(
                "MATCH (nc:NameCorrection {incorrect: $i}) DETACH DELETE nc",
                i=inc,
            )
            print(f"✓ Removed {n} NameCorrection node(s): {inc!r}")
            return n

    def clear_all_corrections(self) -> int:
        """Delete all NameCorrection nodes. Returns how many were removed."""
        with self.driver.session() as session:
            rec = session.run("MATCH (nc:NameCorrection) RETURN count(nc) AS c").single()
            n = int(rec["c"]) if rec else 0
            session.run("MATCH (nc:NameCorrection) DETACH DELETE nc")
        return n

    def apply_to_file(
        self,
        filepath: Path,
        output_path: Path | None = None,
        confidence_threshold: str = "medium",
        *,
        in_place: bool = False,
    ) -> int:
        """
        Read raw transcript, apply corrections, write to output path.
        Never overwrites raw files under transcripts/ unless in_place=True.

        Returns: number of substring replacements recorded (0 if none).
        """
        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}")
            return 0

        text = filepath.read_text(encoding="utf-8")
        corrected_text, corrections = self.apply_to_text(text, confidence_threshold)

        output = output_path if output_path is not None else default_corrected_path(filepath)
        if (
            not in_place
            and filepath.parent.name == "transcripts"
            and output.resolve() == filepath.resolve()
        ):
            print(
                "ERROR: refusing to overwrite raw transcript in transcripts/. "
                "Omit --output to write to transcripts_corrected/, or pass --in-place to force."
            )
            return 0

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(corrected_text, encoding="utf-8")

        if corrections:
            print(f"✓ Applied {len(corrections)} correction(s) {filepath.name} → {output.name}:")
            for correction in corrections:
                print(f"  - {correction}")
        else:
            print(f"✓ Wrote {output.name} (no dictionary replacements; copy of {filepath.name})")

        return len(corrections)
    
    def import_from_verify_results(self, drafts_dir: Path):
        """
        Import corrections from Person nodes that have verified_spelling.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Person)
                WHERE p.verified_spelling IS NOT NULL
                  AND p.canonical_name <> p.verified_spelling
                RETURN p.canonical_name AS incorrect,
                       p.verified_spelling AS correct,
                       p.verification_source AS source,
                       p.verification_confidence AS confidence
            """)
            
            added = 0
            for record in result:
                inc = (record["incorrect"] or "").strip()
                cor = (record["correct"] or "").strip()
                if not inc or inc == cor:
                    continue
                if self.add_correction(
                    inc,
                    cor,
                    record["confidence"] or "medium",
                    record["source"] or "verify_drafts.py",
                ):
                    added += 1

            # Also import from aliases (WITH required between UNWIND and filtering WHERE)
            result = session.run("""
                MATCH (p:Person)
                WHERE p.aliases IS NOT NULL AND size(p.aliases) > 0
                UNWIND p.aliases AS alias
                WITH p, alias
                WHERE alias IS NOT NULL AND trim(toString(alias)) <> ''
                  AND alias <> p.canonical_name
                RETURN alias AS incorrect,
                       p.canonical_name AS correct,
                       'alias_merge' AS source,
                       'high' AS confidence
            """)

            for record in result:
                inc = (record["incorrect"] or "").strip()
                cor = (record["correct"] or "").strip()
                if not inc or inc == cor:
                    continue
                if self.add_correction(
                    inc,
                    cor,
                    record["confidence"],
                    record["source"],
                ):
                    added += 1

            print(f"\n✓ Imported {added} correction(s) from Neo4j (unsafe pairs skipped)")


def main():
    parser = argparse.ArgumentParser(description="Manage name correction dictionary")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add correction
    add_parser = subparsers.add_parser("add", help="Add a correction")
    add_parser.add_argument("incorrect", help="Incorrect spelling")
    add_parser.add_argument("correct", help="Correct spelling")
    add_parser.add_argument("--confidence", choices=["high", "medium", "low"], default="high")
    add_parser.add_argument("--source", default="manual")
    add_parser.add_argument("--context", default="")
    
    # List corrections
    list_parser = subparsers.add_parser("list", help="List all corrections")
    list_parser.add_argument("--confidence", choices=["high", "medium", "low"], help="Filter by confidence")

    remove_parser = subparsers.add_parser(
        "remove",
        help="Delete one NameCorrection by exact incorrect string (e.g. bad verify import)",
    )
    remove_parser.add_argument("incorrect", help="The incorrect string as stored on NameCorrection.incorrect")
    
    # Apply to file
    apply_parser = subparsers.add_parser("apply", help="Apply corrections; writes corrected copy (default: transcripts_corrected/)")
    apply_parser.add_argument("file", type=Path, help="Raw transcript file to read")
    apply_parser.add_argument(
        "--output",
        type=Path,
        help="Output file (default: transcripts_corrected/<basename> if input is under transcripts/)",
    )
    apply_parser.add_argument("--threshold", choices=["high", "medium", "low"], default="medium")
    apply_parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file (not recommended for transcripts/)",
    )

    # Apply to directory
    apply_dir_parser = subparsers.add_parser(
        "apply-dir", help="Read raw directory, write corrected files to output-dir"
    )
    apply_dir_parser.add_argument("directory", type=Path, help="Directory containing raw .txt files (e.g. transcripts/)")
    apply_dir_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Where to write corrected files (default: sibling transcripts_corrected/ if directory is transcripts/)",
    )
    apply_dir_parser.add_argument("--pattern", default="*.txt", help="File pattern (default: *.txt)")
    apply_dir_parser.add_argument("--threshold", choices=["high", "medium", "low"], default="medium")
    
    # Import from verify results
    import_parser = subparsers.add_parser("import-from-verify", help="Import corrections from Neo4j Person nodes")
    import_parser.add_argument("--drafts-dir", type=Path, help="Drafts directory (for context)")

    clear_parser = subparsers.add_parser(
        "clear-all",
        help="Delete all NameCorrection nodes (after bad imports; re-run apply-dir after)",
    )
    clear_parser.add_argument("--yes", action="store_true", help="Required confirmation flag")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = CorrectionManager()
    
    try:
        if args.command == "add":
            if not manager.add_correction(
                args.incorrect,
                args.correct,
                args.confidence,
                args.source,
                args.context,
            ):
                sys.exit(1)
        
        elif args.command == "list":
            corrections = manager.list_corrections(args.confidence)
            if not corrections:
                print("No corrections found")
            else:
                print(f"Name Corrections ({len(corrections)}):\n")
                for c in corrections:
                    print(f"  '{c['incorrect']}' → '{c['correct']}'")
                    print(f"    Confidence: {c['confidence']}, Source: {c['source']}")
                    print()

        elif args.command == "remove":
            manager.remove_correction(args.incorrect)
        
        elif args.command == "apply":
            if args.in_place:
                manager.apply_to_file(args.file, args.file, args.threshold, in_place=True)
            else:
                manager.apply_to_file(args.file, args.output, args.threshold, in_place=False)

        elif args.command == "apply-dir":
            if not args.directory.exists():
                print(f"ERROR: Directory not found: {args.directory}")
                return

            out_dir = args.output_dir or default_output_dir_for_apply_dir(args.directory)

            files = list(args.directory.glob(args.pattern))
            if not files:
                print(f"No files matching '{args.pattern}' in {args.directory}")
                return

            print(f"Reading {args.directory} → writing {out_dir} ({len(files)} file(s))...\n")
            total_corrections = 0
            for filepath in sorted(files):
                dest = out_dir / filepath.name
                count = manager.apply_to_file(filepath, dest, args.threshold)
                total_corrections += count

            print(f"\n✓ Total: {total_corrections} correction(s) across {len(files)} file(s)")
        
        elif args.command == "import-from-verify":
            manager.import_from_verify_results(args.drafts_dir)

        elif args.command == "clear-all":
            if not args.yes:
                print("Refusing to clear: pass --yes to delete all NameCorrection nodes")
                sys.exit(1)
            n = manager.clear_all_corrections()
            print(f"✓ Removed {n} NameCorrection node(s)")

    finally:
        manager.close()


if __name__ == "__main__":
    main()
