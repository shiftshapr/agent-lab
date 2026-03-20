"""
Neo4j Name Correction Dictionary
Stores verified name corrections and auto-applies them to transcripts.

Usage:
    # Add correction
    python scripts/neo4j_corrections.py add "Tyler Boyer" "Tyler Bowyer" --confidence high
    
    # List corrections
    python scripts/neo4j_corrections.py list
    
    # Apply corrections to transcript
    python scripts/neo4j_corrections.py apply transcripts/episode_001.txt
    
    # Import from verify_drafts results
    python scripts/neo4j_corrections.py import-from-verify
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j driver not installed. Run: uv add neo4j")
    sys.exit(1)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:17687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")


class CorrectionManager:
    """Manages name corrections in Neo4j."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    def close(self):
        self.driver.close()
    
    def add_correction(self, incorrect: str, correct: str, confidence: str = "high", 
                      source: str = "manual", context: str = ""):
        """
        Add a name correction to the dictionary.
        Idempotent: MERGE on `incorrect` updates the same node; re-importing the same
        pair or re-running apply-dir on already-corrected transcripts is safe (no duplicate
        rewrites when the wrong string no longer appears).
        """
        inc = (incorrect or "").strip()
        cor = (correct or "").strip()
        if not inc or inc == cor:
            return
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
                
                if incorrect in text:
                    text = text.replace(incorrect, correct)
                    corrections_applied.append(f"{incorrect} → {correct}")
        
        return text, corrections_applied
    
    def apply_to_file(self, filepath: Path, output_path: Path | None = None, 
                     confidence_threshold: str = "medium") -> int:
        """
        Apply corrections to a file.
        Returns: number of corrections applied
        """
        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}")
            return 0
        
        text = filepath.read_text(encoding="utf-8")
        corrected_text, corrections = self.apply_to_text(text, confidence_threshold)
        
        if not corrections:
            print(f"No corrections needed for {filepath.name}")
            return 0
        
        # Write to output file or overwrite original
        output = output_path or filepath
        output.write_text(corrected_text, encoding="utf-8")
        
        print(f"✓ Applied {len(corrections)} correction(s) to {filepath.name}:")
        for correction in corrections:
            print(f"  - {correction}")
        
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
            
            count = 0
            for record in result:
                inc = (record["incorrect"] or "").strip()
                cor = (record["correct"] or "").strip()
                if not inc or inc == cor:
                    continue
                self.add_correction(
                    inc,
                    cor,
                    record["confidence"] or "medium",
                    record["source"] or "verify_drafts.py"
                )
                count += 1
            
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
                self.add_correction(
                    inc,
                    cor,
                    record["confidence"],
                    record["source"]
                )
                count += 1
            
            print(f"\n✓ Imported {count} correction(s) from Neo4j")


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
    
    # Apply to file
    apply_parser = subparsers.add_parser("apply", help="Apply corrections to a file")
    apply_parser.add_argument("file", type=Path, help="File to correct")
    apply_parser.add_argument("--output", type=Path, help="Output file (default: overwrite input)")
    apply_parser.add_argument("--threshold", choices=["high", "medium", "low"], default="medium")
    
    # Apply to directory
    apply_dir_parser = subparsers.add_parser("apply-dir", help="Apply corrections to all files in directory")
    apply_dir_parser.add_argument("directory", type=Path, help="Directory containing files")
    apply_dir_parser.add_argument("--pattern", default="*.txt", help="File pattern (default: *.txt)")
    apply_dir_parser.add_argument("--threshold", choices=["high", "medium", "low"], default="medium")
    
    # Import from verify results
    import_parser = subparsers.add_parser("import-from-verify", help="Import corrections from Neo4j Person nodes")
    import_parser.add_argument("--drafts-dir", type=Path, help="Drafts directory (for context)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = CorrectionManager()
    
    try:
        if args.command == "add":
            manager.add_correction(
                args.incorrect,
                args.correct,
                args.confidence,
                args.source,
                args.context
            )
        
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
        
        elif args.command == "apply":
            manager.apply_to_file(args.file, args.output, args.threshold)
        
        elif args.command == "apply-dir":
            if not args.directory.exists():
                print(f"ERROR: Directory not found: {args.directory}")
                return
            
            files = list(args.directory.glob(args.pattern))
            if not files:
                print(f"No files matching '{args.pattern}' in {args.directory}")
                return
            
            print(f"Applying corrections to {len(files)} file(s)...\n")
            total_corrections = 0
            for filepath in files:
                count = manager.apply_to_file(filepath, None, args.threshold)
                total_corrections += count
            
            print(f"\n✓ Total: {total_corrections} correction(s) across {len(files)} file(s)")
        
        elif args.command == "import-from-verify":
            manager.import_from_verify_results(args.drafts_dir)
    
    finally:
        manager.close()


if __name__ == "__main__":
    main()
