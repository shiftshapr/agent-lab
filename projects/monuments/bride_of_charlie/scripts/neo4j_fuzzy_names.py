"""
Shared fuzzy person-name matching for Neo4j ingest and merge tools.

Multi-token names require first-token Levenshtein <= 1 before full-name
Levenshtein <= threshold — blocks same-surname false positives (e.g.
Tony Erpenbeck vs Gary Erpenbeck at distance 3).
"""

from __future__ import annotations


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalize_name(name: str) -> str:
    """Normalize name for comparison (lowercase, remove extra spaces)."""
    return " ".join(name.lower().split())


def _name_tokens(name: str) -> list[str]:
    return normalize_name(name).split()


def _first_tokens_fuzzy_compatible(
    name_a: str,
    name_b: str,
    max_distance: int = 1,
) -> bool:
    """
    Block fuzzy merges when both sides look like multi-word person/org names
    but the first tokens differ beyond typo tolerance (e.g. Tony vs Gary Erpenbeck).
    Single-token names skip this guard so short labels still fuzzy-match.
    """
    tokens_a = _name_tokens(name_a)
    tokens_b = _name_tokens(name_b)
    if len(tokens_a) < 2 or len(tokens_b) < 2:
        return True
    return levenshtein_distance(tokens_a[0], tokens_b[0]) <= max_distance


def fuzzy_name_distance(name_a: str, name_b: str) -> int:
    return levenshtein_distance(normalize_name(name_a), normalize_name(name_b))


def fuzzy_names_match(
    name_a: str,
    name_b: str,
    threshold: int = 3,
    first_token_threshold: int = 1,
) -> bool:
    """True when names are within Levenshtein threshold and first-token guard passes."""
    if not _first_tokens_fuzzy_compatible(name_a, name_b, first_token_threshold):
        return False
    return fuzzy_name_distance(name_a, name_b) <= threshold


def fuzzy_duplicate_distance(
    name_a: str,
    name_b: str,
    threshold: int = 3,
    first_token_threshold: int = 1,
) -> int | None:
    """Return full-name distance when pair qualifies as fuzzy duplicate, else None."""
    if not fuzzy_names_match(
        name_a,
        name_b,
        threshold=threshold,
        first_token_threshold=first_token_threshold,
    ):
        return None
    return fuzzy_name_distance(name_a, name_b)
