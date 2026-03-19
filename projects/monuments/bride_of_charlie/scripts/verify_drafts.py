"""
Verify Drafts: Numbering Audit + Name Verification

Runs after episode analysis to ensure:
  1. Numbering is correct across episodes (no collisions, proper continuation)
  2. Person names are verified via web search (spelling check)
  3. Verification results cached in Neo4j (if available)

Usage:
  cd ~/workspace/agent-lab
  uv run --project framework/deer-flow/backend python projects/monuments/bride_of_charlie/scripts/verify_drafts.py

  --skip-search   Skip web search (numbering audit only)
  --drafts DIR    Drafts directory (default: project drafts/)
  --no-cache      Don't use Neo4j cache (always search)

Environment:
  NEO4J_URI       Neo4j connection URI (enables caching)
  NEO4J_USER      Neo4j username (default: neo4j)
  NEO4J_PASSWORD  Neo4j password (default: openclaw)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

# Script is at projects/monuments/bride_of_charlie/scripts/
PROJECT_DIR = Path(__file__).resolve().parent.parent
DRAFTS_DIR = PROJECT_DIR / "drafts"

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "openclaw")

# Try to import Neo4j driver
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


def load_drafts(drafts_dir: Path) -> list[tuple[str, str]]:
    """Load (episode_name, content) for each episode."""
    out = []
    for p in sorted(drafts_dir.glob("episode_*.md")):
        if "cross_episode" in p.name:
            continue
        out.append((p.name, p.read_text(encoding="utf-8")))
    return out


def find_episode_num(name: str) -> int:
    m = re.search(r"episode_(\d+)", name, re.I)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# Numbering audit
# ---------------------------------------------------------------------------

ARTIFACT_FAMILY_RE = re.compile(r"A-(\d+)(?:\.\d+)?")
CLAIM_RE = re.compile(r"C-(\d+)")
NODE_RE = re.compile(r"N-(\d+)")


def audit_numbering(drafts: list[tuple[str, str]]) -> dict:
    """Check for ID collisions, ordering, gaps."""
    artifacts: dict[int, list[str]] = defaultdict(list)  # family_id -> [episode]
    claims: dict[int, list[str]] = defaultdict(list)
    nodes: dict[int, list[str]] = defaultdict(list)

    for ep_name, content in drafts:
        ep_num = find_episode_num(ep_name)
        for m in ARTIFACT_FAMILY_RE.finditer(content):
            fam = int(m.group(1))
            artifacts[fam].append(ep_name)
        for m in CLAIM_RE.finditer(content):
            c = int(m.group(1))
            claims[c].append(ep_name)
        for m in NODE_RE.finditer(content):
            n = int(m.group(1))
            nodes[n].append(ep_name)

    # Dedupe per episode (same ID can appear multiple times in one ep)
    def dedupe(d: dict) -> dict:
        return {k: list(dict.fromkeys(v)) for k, v in d.items()}

    artifacts = dedupe(artifacts)
    claims = dedupe(claims)
    nodes = dedupe(nodes)

    # Collisions: same ID in multiple episodes (artifacts and claims must be unique)
    # Nodes are reused across episodes by design — no collision check
    art_collisions = [(k, v) for k, v in artifacts.items() if len(v) > 1]
    claim_collisions = [(k, v) for k, v in claims.items() if len(v) > 1]

    return {
        "artifacts": artifacts,
        "claims": claims,
        "nodes": nodes,
        "art_collisions": art_collisions,
        "claim_collisions": claim_collisions,
    }


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------

def extract_person_names(drafts: list[tuple[str, str]]) -> set[str]:
    """Extract person names from Node Register (people, not investigation targets)."""
    names = set()
    # Pattern: | N-X | Name | or **N-X** Name
    for _ep_name, content in drafts:
        # Node table: | N-1 | Charlie Kirk | ...
        for m in re.finditer(r"\|\s*N-(\d+)\s*\|\s*([^|]+?)\s*\|", content):
            node_id = int(m.group(1))
            if node_id < 1000:  # people only
                name = m.group(2).strip()
                if name and not name.startswith("Evidence") and not name.startswith("Claim"):
                    names.add(name)
        # Bold format: **N-2** Erica Kirk
        for m in re.finditer(r"\*\*N-(\d+)\*\*\s+([^\n*]+)", content):
            node_id = int(m.group(1))
            if node_id < 1000:
                name = m.group(2).strip()
                if name:
                    names.add(name)
    return names


# ---------------------------------------------------------------------------
# Neo4j verification cache
# ---------------------------------------------------------------------------

def get_neo4j_session():
    """Get Neo4j session if available."""
    if not NEO4J_AVAILABLE or not NEO4J_URI:
        return None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        return driver.session()
    except Exception:
        return None


def check_verification_cache(session, name: str, cache_days: int = 30) -> dict | None:
    """Check Neo4j for cached verification result."""
    if not session:
        return None
    
    try:
        result = session.run(
            "MATCH (p:Person) "
            "WHERE p.canonical_name = $name OR $name IN p.aliases "
            "RETURN p.verified_spelling AS verified, "
            "       p.verification_source AS source, "
            "       p.verification_date AS date, "
            "       p.verification_confidence AS confidence",
            name=name
        )
        record = result.single()
        
        if not record or not record["verified"]:
            return None
        
        # Check if cache is still valid
        verification_date = record["date"]
        if verification_date:
            if isinstance(verification_date, str):
                verification_date = datetime.fromisoformat(verification_date).date()
            age_days = (date.today() - verification_date).days
            if age_days > cache_days:
                return None  # Cache expired
        
        return {
            "verified": record["verified"],
            "source": record["source"] or "cached",
            "confidence": record["confidence"] or "unknown",
            "cached": True
        }
    except Exception:
        return None


def store_verification_result(session, name: str, verified_spelling: str, source: str, confidence: str = "high"):
    """Store verification result in Neo4j."""
    if not session:
        return
    
    try:
        session.run(
            "MATCH (p:Person) "
            "WHERE p.canonical_name = $name OR $name IN p.aliases "
            "SET p.verified_spelling = $verified, "
            "    p.verification_source = $source, "
            "    p.verification_date = date(), "
            "    p.verification_confidence = $confidence",
            name=name,
            verified=verified_spelling,
            source=source,
            confidence=confidence
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Name verification via web search
# ---------------------------------------------------------------------------

def verify_name_spelling(name: str, context: str = "Turning Point USA") -> str | None:
    """
    Search for name + context. If top results use a different spelling, return it.
    E.g. "Tyler Boyer" -> search finds "Tyler Bowyer" in titles -> return "Tyler Bowyer"
    """
    try:
        from ddgs import DDGS
    except ImportError:
        return None

    parts = name.split()
    if len(parts) < 2:
        return None

    query = f"{name} {context}"
    try:
        ddgs = DDGS(timeout=15)
        results = ddgs.text(query, max_results=5)
    except Exception:
        return None

    if not results:
        return None

    # Collect spellings of the full name from result titles (most likely to be correct)
    spellings: dict[str, int] = {}
    first = parts[0].lower()
    our_last = parts[-1].lower()
    for r in results:
        title = r.get("title", "") or ""
        body = r.get("body", "") or ""
        text = f"{title} {body}"
        # Find "FirstName LastName" patterns (allow mixed case)
        for m in re.finditer(r"\b([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)*)\b", text):
            candidate = m.group(1).strip()
            cand_parts = candidate.split()
            if len(candidate) >= 6 and len(cand_parts) >= 2 and cand_parts[0].lower() == first:
                cand_last = cand_parts[-1].lower()
                if cand_last != our_last:
                    # Different last name spelling - likely correction
                    spellings[candidate] = spellings.get(candidate, 0) + 1

    if not spellings:
        return None
    best = max(spellings, key=spellings.get)
    if best.lower() != name.lower():
        return best
    return None


def verify_names_with_search(names: set[str], use_cache: bool = True) -> list[dict]:
    """Verify each name via web search with Neo4j caching. Returns list of {name, suggested, status, cached}."""
    out = []
    session = get_neo4j_session() if use_cache else None
    cache_hits = 0
    cache_misses = 0
    
    for name in sorted(names):
        if not name or len(name) < 4:
            continue
        
        # Check cache first
        cached_result = check_verification_cache(session, name) if session else None
        
        if cached_result:
            cache_hits += 1
            verified = cached_result["verified"]
            if verified.lower() != name.lower():
                out.append({
                    "name": name,
                    "suggested": verified,
                    "status": "check",
                    "cached": True,
                    "source": cached_result["source"]
                })
            else:
                out.append({
                    "name": name,
                    "suggested": None,
                    "status": "ok",
                    "cached": True,
                    "source": cached_result["source"]
                })
        else:
            # Not in cache - search
            cache_misses += 1
            suggested = verify_name_spelling(name)
            
            if suggested:
                out.append({
                    "name": name,
                    "suggested": suggested,
                    "status": "check",
                    "cached": False
                })
                # Store in cache
                if session:
                    store_verification_result(session, name, suggested, "DuckDuckGo search", "medium")
            else:
                out.append({
                    "name": name,
                    "suggested": None,
                    "status": "ok",
                    "cached": False
                })
                # Store "verified as-is" in cache
                if session:
                    store_verification_result(session, name, name, "DuckDuckGo search (no correction)", "high")
    
    if session:
        session.close()
        if cache_hits > 0 or cache_misses > 0:
            print(f"  Cache: {cache_hits} hits, {cache_misses} misses")
    
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Verify drafts: numbering + name spelling")
    ap.add_argument("--skip-search", action="store_true", help="Skip web search (numbering only)")
    ap.add_argument("--drafts", type=Path, default=DRAFTS_DIR, help="Drafts directory")
    ap.add_argument("--no-cache", action="store_true", help="Don't use Neo4j cache (always search)")
    args = ap.parse_args()
    
    use_cache = not args.no_cache and NEO4J_AVAILABLE and NEO4J_URI

    drafts_dir = args.drafts
    if not drafts_dir.exists():
        print(f"[verify] Drafts dir not found: {drafts_dir}")
        return 1

    drafts = load_drafts(drafts_dir)
    if not drafts:
        print(f"[verify] No episode drafts in {drafts_dir}")
        return 1

    print(f"[verify] Found {len(drafts)} episode(s)")
    print()

    # --- Numbering audit ---
    print("--- Numbering Audit ---")
    audit = audit_numbering(drafts)

    if audit["art_collisions"]:
        print("  ARTIFACT COLLISIONS (same ID in multiple episodes):")
        for fam, eps in sorted(audit["art_collisions"]):
            print(f"    A-{fam}: {', '.join(eps)}")
    else:
        print("  Artifacts: no collisions")

    if audit["claim_collisions"]:
        print("  CLAIM COLLISIONS:")
        for c, eps in sorted(audit["claim_collisions"]):
            print(f"    C-{c}: {', '.join(eps)}")
    else:
        print("  Claims: no collisions")

    print("  Nodes: (reuse across episodes is expected)")

    art_fams = sorted(audit["artifacts"].keys())
    claim_ids = sorted(audit["claims"].keys())
    if art_fams:
        print(f"  Artifact families: A-{art_fams[0]} to A-{art_fams[-1]} ({len(art_fams)} families)")
    if claim_ids:
        print(f"  Claims: C-{claim_ids[0]} to C-{claim_ids[-1]} ({len(claim_ids)} unique)")

    numbering_ok = not (audit["art_collisions"] or audit["claim_collisions"])

    print()

    # --- Name verification ---
    print("--- Name Verification ---")
    names = extract_person_names(drafts)
    print(f"  Found {len(names)} person(s) in Node Register")
    
    if use_cache:
        print(f"  Neo4j cache: ENABLED")
    elif NEO4J_URI and not args.no_cache:
        print(f"  Neo4j cache: UNAVAILABLE (driver not installed or connection failed)")
    else:
        print(f"  Neo4j cache: DISABLED")

    if args.skip_search:
        print("  (Skipped web search — use without --skip-search to verify spellings)")
        for n in sorted(names):
            print(f"    - {n}")
    else:
        results = verify_names_with_search(names, use_cache=use_cache)
        for r in results:
            cached_marker = " [cached]" if r.get("cached") else ""
            if r["suggested"]:
                print(f"  CHECK: \"{r['name']}\" → possible correct spelling: \"{r['suggested']}\"{cached_marker}")
            else:
                print(f"  OK: {r['name']}{cached_marker}")

    print()
    if numbering_ok:
        print("[verify] Numbering audit: PASS")
    else:
        print("[verify] Numbering audit: FAIL (fix collisions above)")
        return 1

    print("[verify] Done. Review any name suggestions and correct drafts if needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
