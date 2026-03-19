"""
Fix ID Collisions in Episode Drafts

Post-processing: After generation, scan drafts for A- and C- ID collisions
and rewrite IDs programmatically so each episode uses unique, sequential IDs.

Nodes (N-) are NOT rewritten — reuse across episodes is by design.

Usage:
  cd ~/workspace/agent-lab
  uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/fix_collisions.py

  --drafts DIR    Drafts directory (default: project drafts/)
  --dry-run       Report collisions and proposed fixes without writing
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_DIR / "drafts"

# Only match DEFINITIONS (headers), not references in Related/Anchored lines
ARTIFACT_FAMILY_DEF_RE = re.compile(r"^\s*\*\*A-(\d+)(?:\.\d+)?\*\*", re.MULTILINE)
CLAIM_DEF_RE = re.compile(r"^\s*\*\*C-(\d+)\*\*", re.MULTILINE)
# For collision detection we also need all occurrences (audit)
ARTIFACT_FAMILY_RE = re.compile(r"A-(\d+)(?:\.\d+)?")
CLAIM_RE = re.compile(r"C-(\d+)")


def load_drafts(drafts_dir: Path) -> list[tuple[str, str, str]]:
    """Load (episode_name, content, file_path) for each episode."""
    out = []
    for p in sorted(drafts_dir.glob("episode_*.md")):
        if "cross_episode" in p.name:
            continue
        out.append((p.name, p.read_text(encoding="utf-8"), str(p)))
    return out


def find_episode_num(name: str) -> int:
    m = re.search(r"episode_(\d+)", name, re.I)
    return int(m.group(1)) if m else 0


def extract_artifact_families(content: str) -> set[int]:
    """Extract artifact family IDs that are DEFINED (headers) in this episode."""
    families = set()
    for m in ARTIFACT_FAMILY_DEF_RE.finditer(content):
        families.add(int(m.group(1)))
    return families


def extract_claims(content: str) -> set[int]:
    """Extract claim IDs that are DEFINED (headers in Claim Register) in this episode."""
    claims = set()
    for m in CLAIM_DEF_RE.finditer(content):
        claims.add(int(m.group(1)))
    return claims


def fix_collisions(drafts: list[tuple[str, str, str]], dry_run: bool = False) -> tuple[bool, list[str]]:
    """
    Scan drafts for collisions and rewrite IDs. Returns (success, log_lines).
    """
    # Sort by episode number
    drafts_sorted = sorted(drafts, key=lambda x: find_episode_num(x[0]))
    used_artifact_families: set[int] = set()
    next_claim = 1000
    log: list[str] = []
    any_fixed = False

    for ep_name, content, path in drafts_sorted:
        ep_num = find_episode_num(ep_name)
        families = extract_artifact_families(content)
        claims = extract_claims(content)

        art_remap: dict[int, int] = {}
        claim_remap: dict[int, int] = {}

        # Artifact collisions: any family already used?
        for f in sorted(families):
            if f in used_artifact_families:
                next_art = max(used_artifact_families) + 1
                while next_art in used_artifact_families:
                    next_art += 1
                art_remap[f] = next_art
                used_artifact_families.add(next_art)
                log.append(f"  {ep_name}: A-{f} -> A-{next_art} (collision)")
            else:
                used_artifact_families.add(f)

        # Claim collisions: any claim ID < next_claim?
        for c in sorted(claims):
            if c < next_claim:
                claim_remap[c] = next_claim
                next_claim += 1
                log.append(f"  {ep_name}: C-{c} -> C-{claim_remap[c]} (collision)")
            else:
                next_claim = max(next_claim, c + 1)

        if not art_remap and not claim_remap:
            continue

        any_fixed = True

        if dry_run:
            continue

        # Apply remappings
        new_content = content

        # Artifact: replace A-OLD and A-OLD.N with A-NEW and A-NEW.N
        # Order by descending length so A-1000.1 is replaced before A-1000
        for old_f, new_f in sorted(art_remap.items(), key=lambda x: -len(str(x[0]))):
            # Match A-{old_f} or A-{old_f}.{sub}
            pattern = re.compile(rf"A-{old_f}(\.\d+)?(?=\D|$)")
            new_content = pattern.sub(lambda m: f"A-{new_f}{m.group(1) or ''}", new_content)

        # Claim: replace C-OLD with C-NEW
        for old_c, new_c in sorted(claim_remap.items(), reverse=True):
            # Avoid replacing C-1000 when we mean C-1000 (e.g. don't replace in C-10000)
            pattern = re.compile(rf"\bC-{old_c}\b")
            new_content = pattern.sub(f"C-{new_c}", new_content)

        Path(path).write_text(new_content, encoding="utf-8")
        log.append(f"  Wrote {ep_name}")

    return any_fixed, log


def main() -> int:
    ap = argparse.ArgumentParser(description="Fix ID collisions in episode drafts")
    ap.add_argument("--drafts", type=Path, default=DRAFTS_DIR, help="Drafts directory")
    ap.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    args = ap.parse_args()

    drafts_dir = args.drafts
    if not drafts_dir.exists():
        print(f"[fix_collisions] Drafts dir not found: {drafts_dir}")
        return 1

    drafts = load_drafts(drafts_dir)
    if not drafts:
        print(f"[fix_collisions] No episode drafts in {drafts_dir}")
        return 1

    print(f"[fix_collisions] Scanning {len(drafts)} episode(s)...")

    # Quick collision check: only DEFINITIONS (headers) count as "used in episode"
    artifacts: dict[int, list[str]] = defaultdict(list)
    claims: dict[int, list[str]] = defaultdict(list)
    for ep_name, content, _ in drafts:
        for m in ARTIFACT_FAMILY_DEF_RE.finditer(content):
            artifacts[int(m.group(1))].append(ep_name)
        for m in CLAIM_DEF_RE.finditer(content):
            claims[int(m.group(1))].append(ep_name)

    def dedupe(d: dict) -> dict:
        return {k: list(dict.fromkeys(v)) for k, v in d.items()}

    artifacts = dedupe(artifacts)
    claims = dedupe(claims)
    art_collisions = [(k, v) for k, v in artifacts.items() if len(v) > 1]
    claim_collisions = [(k, v) for k, v in claims.items() if len(v) > 1]

    if not art_collisions and not claim_collisions:
        print("[fix_collisions] No collisions found. Nothing to fix.")
        return 0

    print("\nCollisions detected:")
    for fam, eps in sorted(art_collisions):
        print(f"  A-{fam}: {', '.join(eps)}")
    for c, eps in sorted(claim_collisions):
        print(f"  C-{c}: {', '.join(eps)}")

    if args.dry_run:
        print("\n[fix_collisions] Dry run — would fix collisions (run without --dry-run to apply)")
        return 0

    print("\nFixing...")
    fixed, log = fix_collisions(drafts, dry_run=False)
    for line in log:
        print(line)

    if fixed:
        print("\n[fix_collisions] Done. Re-run verify_drafts to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
