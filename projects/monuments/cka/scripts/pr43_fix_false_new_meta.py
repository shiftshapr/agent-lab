#!/usr/bin/env python3
"""PR43 fix-all: FALSE_NEW + META_NAME_LIE on catch-up drafts (seq 21-156).

Moves Batch1-2 / earlier-catch-up ledger IDs from New Nodes -> Existing/Reused.
Scrubs META_NAME_LIE parentheticals against canonical/nodes.json.
Drops mistaken new register rows for FALSE_NEW ids (re-registered batch ledger nodes).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[1]
DRAFTS = CKA / "drafts"
CANON = CKA / "canonical" / "nodes.json"

NID_RE = re.compile(r"\bN-(\d+)\b")
RANGE_RE = re.compile(r"N-(\d+)\s+through\s+N-(\d+)", re.I)
# Capture N-id with optional parenthetical name on same token neighborhood
NID_WITH_NAME = re.compile(
    r"(N-(\d+))(\s*\(([^)]*)\))?"
)

YAML_NEW = re.compile(
    r"(^  - New Nodes Introduced:\s*)(.*)$", re.M
)
YAML_REUSED = re.compile(
    r"(^  - Reused Nodes Appearing:\s*)(.*)$", re.M
)
YAML_EXISTING = re.compile(
    r"(^  - Existing Nodes Reused:\s*)(.*)$", re.M
)

# Body one-line variants
BODY_NEW_LINE = re.compile(
    r"(^([ \t]*[-*]?\s*\*{0,2}New Nodes Introduced\*{0,2}:\s*))(.+)$",
    re.M,
)
BODY_EXISTING_LINE = re.compile(
    r"(^([ \t]*[-*]?\s*\*{0,2}Existing Nodes Reused\*{0,2}:\s*))(.+)$",
    re.M,
)
BODY_REUSED_LINE = re.compile(
    r"(^([ \t]*[-*]?\s*\*{0,2}Reused Nodes Appearing\*{0,2}:\s*))(.+)$",
    re.M,
)

# Multi-line block starting at "New Nodes Introduced:" then bullet lines until blank/other header
MULTILINE_NEW_START = re.compile(
    r"(?m)^(#{1,3}\s*)?New Nodes Introduced:\s*$"
)

NODE_HEADER = re.compile(r"(?m)^\*\*(N-(\d+))\*\*\s+(.+)$")


def load_canon_names() -> dict[str, str]:
    doc = json.loads(CANON.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for nid, meta in doc.get("nodes", {}).items():
        name = (meta or {}).get("canonical_name") or ""
        if name:
            out[nid] = name
    return out


def expand_ids_from_text(chunk: str) -> list[str]:
    """Ordered unique N-ids from a New-nodes chunk (supports through-ranges)."""
    ids: list[str] = []
    seen: set[str] = set()
    # ranges first
    for a, b in RANGE_RE.findall(chunk):
        for i in range(int(a), int(b) + 1):
            nid = f"N-{i}"
            if nid not in seen:
                seen.add(nid)
                ids.append(nid)
    for m in NID_RE.finditer(chunk):
        nid = f"N-{m.group(1)}"
        if nid not in seen:
            seen.add(nid)
            ids.append(nid)
    return ids


def parse_named_entries(chunk: str) -> list[tuple[str, str | None]]:
    """Return (nid, parenthetical_or_None) in order; ranges expand without names."""
    entries: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    # Work on text before Existing/Reused/Cross-Episode if present
    stop = re.search(
        r"(?i)\b(Existing Nodes Reused|Reused Nodes Appearing|Cross-Episode)\b",
        chunk,
    )
    text = chunk[: stop.start()] if stop else chunk

    # Expand ranges as unnamed
    for a, b in RANGE_RE.findall(text):
        for i in range(int(a), int(b) + 1):
            nid = f"N-{i}"
            if nid not in seen:
                seen.add(nid)
                entries.append((nid, None))

    for m in NID_WITH_NAME.finditer(text):
        nid = m.group(1)
        if nid in seen:
            # update name if we now see a parenthetical and previous was None
            if m.group(4) is not None:
                for i, (n, nm) in enumerate(entries):
                    if n == nid and nm is None:
                        entries[i] = (nid, m.group(4).strip())
                        break
            continue
        # skip if this N- was only the start/end of a through-range already counted
        # (already in seen from ranges)
        seen.add(nid)
        name = m.group(4).strip() if m.group(4) is not None else None
        entries.append((nid, name))
    return entries


def format_id_list(ids: list[str], names: dict[str, str] | None = None, with_names: bool = False) -> str:
    if not ids:
        return ""
    if with_names and names is not None:
        parts = []
        for nid in ids:
            nm = names.get(nid)
            parts.append(f"{nid} ({nm})" if nm else nid)
        return ", ".join(parts)
    return ", ".join(ids)


def merge_unique(primary: list[str], extra: list[str]) -> list[str]:
    seen = set(primary)
    out = list(primary)
    for x in extra:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_ids_from_ledger_value(val: str) -> list[str]:
    return expand_ids_from_text(val)


def multiline_new_span(text: str, start_idx: int) -> tuple[int, int, str]:
    """Return (abs_start, abs_end, block_text) for multi-line New Nodes block."""
    # from start of line to before Existing Nodes / Cross-Episode / --- / next ##
    rest = text[start_idx:]
    m_end = re.search(
        r"(?m)^(Existing Nodes Reused:|Cross-Episode|\*\*Existing|---$|##\s)",
        rest[1:],  # skip first line
    )
    if m_end:
        end = start_idx + 1 + m_end.start()
    else:
        # blank line after content
        m_blank = re.search(r"\n\n", rest[1:])
        end = start_idx + 1 + m_blank.start() if m_blank else len(text)
    return start_idx, end, text[start_idx:end]


def build_batch12_baseline(drafts: Path) -> dict[str, int]:
    """nid -> first intro ep from New Nodes in seq 1-20."""
    first: dict[str, int] = {}
    for ep in range(1, 21):
        path = drafts / f"episode_{ep:03d}.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"New Nodes Introduced:\s*", text):
            # take following chunk
            chunk = text[m.end() : m.end() + 2500]
            # stop at Existing/Reused if on same structural area
            for nid in expand_ids_from_text(
                chunk.split("Existing Nodes")[0].split("Reused Nodes")[0]
            ):
                first.setdefault(nid, ep)
    return first


def find_register_block_spans(text: str) -> list[tuple[str, int, int, str]]:
    """List (nid, start, end, header_name) for **N-#** register blocks."""
    headers = list(NODE_HEADER.finditer(text))
    out = []
    for i, h in enumerate(headers):
        start = h.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        # trim trailing --- separators belonging to block
        out.append((h.group(1), start, end, h.group(3).strip()))
    return out


def drop_false_new_register_rows(
    text: str, false_ids: set[str], intro: dict[str, int], ep: int
) -> tuple[str, int]:
    """Drop register blocks for FALSE_NEW ids introduced in an earlier episode.

    Keeps blocks that already mark Existing. Returns (new_text, dropped_count).
    """
    if not false_ids:
        return text, 0
    blocks = find_register_block_spans(text)
    # delete from end to start
    dropped = 0
    pieces = []
    last = len(text)
    # we'll rebuild by skipping spans
    keep_ranges = []
    skip_spans = []
    for nid, start, end, name in blocks:
        if nid not in false_ids:
            continue
        first_ep = intro.get(nid)
        if first_ep is None or first_ep >= ep:
            continue  # this ep is the intro; keep
        block = text[start:end]
        if re.search(r"(?i)\(Existing", block[:400]):
            continue  # already marked existing
        # mistaken re-register of earlier ledger node
        skip_spans.append((start, end))
        dropped += 1

    if not skip_spans:
        return text, 0

    skip_spans.sort()
    out = []
    cursor = 0
    for start, end in skip_spans:
        out.append(text[cursor:start])
        # if block preceded by blank lines, collapse extras later
        cursor = end
    out.append(text[cursor:])
    new_text = "".join(out)
    # tidy triple newlines
    new_text = re.sub(r"\n{4,}", "\n\n\n", new_text)
    return new_text, dropped


def rewrite_new_value(
    raw_value: str,
    false_set: set[str],
    true_ids: list[str],
    canon: dict[str, str],
    style_with_names: bool,
) -> str:
    """Rewrite a New Nodes value string keeping only true_ids; fix META names."""
    entries = parse_named_entries(raw_value)
    # preserve order of true ids as in original where possible
    kept = []
    for nid, nm in entries:
        if nid in false_set:
            continue
        if nid not in true_ids and nid not in {t for t, _ in entries}:
            continue
        if nid in false_set:
            continue
        kept.append((nid, nm))

    # If parsing missed ordering, fall back to true_ids list
    if not kept and true_ids:
        kept = [(nid, None) for nid in true_ids]
    else:
        # ensure all true_ids present
        have = {n for n, _ in kept}
        for nid in true_ids:
            if nid not in have:
                kept.append((nid, None))
                have.add(nid)
        # filter to true only
        kept = [(n, nm) for n, nm in kept if n not in false_set]

    # Fix META parentheticals for kept (true new) entries
    parts = []
    for nid, nm in kept:
        truth = canon.get(nid)
        if nm is not None:
            # if parenthetical is a lie vs canon, replace
            if truth and nm.strip().lower() != truth.strip().lower():
                # special case: notes like "investigation targets only"
                parts.append(f"{nid} ({truth})")
            else:
                parts.append(f"{nid} ({nm})" if nm else nid)
        elif style_with_names and truth:
            parts.append(f"{nid} ({truth})")
        else:
            parts.append(nid)
    return ", ".join(parts)


def fix_multiline_new_block(
    block: str, false_set: set[str], true_ids: list[str], canon: dict[str, str]
) -> str:
    """Rewrite multi-line New Nodes Introduced block."""
    lines = block.splitlines(keepends=True)
    if not lines:
        return block
    out_lines = [lines[0]]  # header
    any_content = False
    for line in lines[1:]:
        if not line.strip():
            out_lines.append(line)
            continue
        # bullet category line like "- People: N-1 (x), N-2"
        m = re.match(r"^(\s*[-*]\s*[^:]+:\s*)(.*)$", line.rstrip("\n"))
        if m:
            prefix, rest = m.group(1), m.group(2)
            entries = parse_named_entries(rest)
            kept = []
            for nid, nm in entries:
                if nid in false_set:
                    continue
                truth = canon.get(nid)
                if nm is not None and truth and nm.strip().lower() != truth.strip().lower():
                    kept.append(f"{nid} ({truth})")
                elif nm is not None:
                    kept.append(f"{nid} ({nm})")
                else:
                    kept.append(nid)
            if kept:
                nl = "\n" if line.endswith("\n") else ""
                out_lines.append(f"{prefix}{', '.join(kept)}{nl}")
                any_content = True
            # else drop the category line entirely
            continue
        # plain id line
        entries = parse_named_entries(line)
        if entries:
            kept = [nid for nid, _ in entries if nid not in false_set]
            if kept:
                nl = "\n" if line.endswith("\n") else ""
                out_lines.append(", ".join(kept) + nl)
                any_content = True
            continue
        out_lines.append(line)

    if not any_content and true_ids:
        # ensure at least one content line
        out_lines.append(", ".join(true_ids) + "\n")
    elif not true_ids and not any_content:
        # empty new nodes - keep header only with (none)
        if len(out_lines) == 1:
            out_lines.append("(none)\n")
    return "".join(out_lines)


def ensure_existing_line(
    text: str, false_ids: list[str], canon: dict[str, str], prefer_yaml: bool
) -> str:
    """Add false_ids into Existing/Reused lines with canon names where useful."""
    if not false_ids:
        return text

    # Prefer YAML Reused Nodes Appearing
    m = YAML_REUSED.search(text)
    if m:
        existing = extract_ids_from_ledger_value(m.group(2))
        merged = merge_unique(existing, false_ids)
        new_val = format_id_list(merged)
        text = text[: m.start(2)] + new_val + text[m.end(2) :]
    elif YAML_EXISTING.search(text):
        m = YAML_EXISTING.search(text)
        assert m
        existing = extract_ids_from_ledger_value(m.group(2))
        merged = merge_unique(existing, false_ids)
        # keep name style if present
        has_names = "(" in m.group(2)
        new_val = format_id_list(merged, canon if has_names else None, with_names=has_names)
        text = text[: m.start(2)] + new_val + text[m.end(2) :]
    elif prefer_yaml and YAML_NEW.search(text):
        # insert Reused line after New
        m = YAML_NEW.search(text)
        assert m
        insert_at = m.end()
        line = f"\n  - Reused Nodes Appearing: {format_id_list(false_ids)}"
        text = text[:insert_at] + line + text[insert_at:]

    # Body Existing Nodes Reused line(s) - update first body occurrence if present
    # Avoid double-updating YAML by requiring not starting with "  - "
    body_existing = list(BODY_EXISTING_LINE.finditer(text))
    updated_body = False
    for m in body_existing:
        # skip yaml-style already handled
        if m.group(0).startswith("  - "):
            continue
        existing = extract_ids_from_ledger_value(m.group(3))
        merged = merge_unique(existing, false_ids)
        has_names = "(" in m.group(3) or bool(re.search(r"N-\d+\s+\S", m.group(3)))
        if has_names:
            parts = []
            # keep prior named forms
            prior = {}
            for mm in re.finditer(r"(N-\d+)(?:\s*\(([^)]*)\)|\s+([^,;]+))?", m.group(3)):
                nid = mm.group(1)
                nm = (mm.group(2) or mm.group(3) or "").strip() or None
                prior[nid] = nm
            for nid in merged:
                nm = prior.get(nid) or canon.get(nid)
                parts.append(f"{nid} ({nm})" if nm else nid)
            new_val = ", ".join(parts)
        else:
            new_val = format_id_list(merged)
        text = text[: m.start(3)] + new_val + text[m.end(3) :]
        updated_body = True
        break

    if not updated_body:
        # try body reused
        for m in BODY_REUSED_LINE.finditer(text):
            if m.group(0).startswith("  - "):
                continue
            existing = extract_ids_from_ledger_value(m.group(3))
            merged = merge_unique(existing, false_ids)
            new_val = format_id_list(merged)
            text = text[: m.start(3)] + new_val + text[m.end(3) :]
            updated_body = True
            break

    if not updated_body:
        # Insert an Existing Nodes Reused line after first body New Nodes line/block
        m = re.search(r"(?m)^New Nodes Introduced:.*$", text)
        if m:
            # if multi-line block, insert after block
            insert_at = m.end()
            if m.group(0).rstrip().endswith(":") and len(m.group(0).strip()) < 30:
                # multi-line - find end
                _, end, _ = multiline_new_span(text, m.start())
                insert_at = end
            names_bits = ", ".join(
                f"{nid} ({canon[nid]})" if nid in canon else nid for nid in false_ids
            )
            text = (
                text[:insert_at]
                + f"\nExisting Nodes Reused: {names_bits}\n"
                + text[insert_at:]
            )
        else:
            m2 = BODY_NEW_LINE.search(text)
            if m2 and not m2.group(0).startswith("  - "):
                names_bits = ", ".join(
                    f"{nid} ({canon[nid]})" if nid in canon else nid for nid in false_ids
                )
                text = (
                    text[: m2.end()]
                    + f"\nExisting Nodes Reused: {names_bits}"
                    + text[m2.end() :]
                )

    return text


def collect_new_listings(text: str) -> list[tuple[str, int, int, str]]:
    """Return list of (kind, start, end, value) for New Nodes regions.

    kind: 'yaml' | 'line' | 'multiline'
    """
    hits: list[tuple[str, int, int, str]] = []
    seen_spans: list[tuple[int, int]] = []

    def overlaps(a: int, b: int) -> bool:
        for s, e in seen_spans:
            if a < e and b > s:
                return True
        return False

    for m in YAML_NEW.finditer(text):
        hits.append(("yaml", m.start(2), m.end(2), m.group(2)))
        seen_spans.append((m.start(), m.end()))

    for m in MULTILINE_NEW_START.finditer(text):
        if overlaps(m.start(), m.start() + 10):
            continue
        s, e, block = multiline_new_span(text, m.start())
        # only treat as multiline if next non-empty line looks like bullets/ids
        rest = block.split("\n", 1)
        if len(rest) == 1 or not rest[1].strip():
            continue
        second = rest[1].lstrip().split("\n", 1)[0]
        if second.startswith("-") or second.startswith("*") or second.startswith("N-"):
            hits.append(("multiline", s, e, block))
            seen_spans.append((s, e))

    for m in BODY_NEW_LINE.finditer(text):
        if overlaps(m.start(), m.end()):
            continue
        # skip pure header of multiline already handled
        if m.group(3).strip() == "" or m.group(0).rstrip().endswith(":"):
            continue
        hits.append(("line", m.start(3), m.end(3), m.group(3)))
        seen_spans.append((m.start(), m.end()))

    return hits


def fix_episode(
    ep: int, text: str, intro: dict[str, int], canon: dict[str, str]
) -> tuple[str, list[str], list[str], int]:
    """Fix one episode. Returns (new_text, false_ids, true_new_ids, dropped_reg)."""
    listings = collect_new_listings(text)
    # Union of all ids claimed New in this episode
    claimed: list[str] = []
    claimed_set: set[str] = set()
    for kind, s, e, val in listings:
        ids = expand_ids_from_text(val)
        for nid in ids:
            if nid not in claimed_set:
                claimed_set.add(nid)
                claimed.append(nid)

    false_ids = [nid for nid in claimed if nid in intro and intro[nid] < ep]
    true_ids = [nid for nid in claimed if nid not in set(false_ids)]
    false_set = set(false_ids)

    if not false_ids and not any(
        # still may need META fix on true news
        True
        for kind, s, e, val in listings
        for nid, nm in parse_named_entries(val)
        if nm and canon.get(nid) and nm.strip().lower() != canon[nid].strip().lower() and nid not in false_set
    ):
        # still run META-only path below via rewrite
        pass

    # Rewrite from end to start so offsets stay valid
    listings_sorted = sorted(listings, key=lambda x: x[1], reverse=True)
    for kind, s, e, val in listings_sorted:
        if kind == "multiline":
            new_block = fix_multiline_new_block(val, false_set, true_ids, canon)
            text = text[:s] + new_block + text[e:]
        else:
            # detect if original used names
            style_with_names = bool(re.search(r"N-\d+\s*\(", val))
            new_val = rewrite_new_value(val, false_set, true_ids, canon, style_with_names)
            # If this listing is a partial body list (subset), only keep intersection
            local_ids = expand_ids_from_text(val)
            local_true = [n for n in local_ids if n not in false_set]
            # For YAML, use episode-level true_ids that appear in this listing OR all true that were in yaml
            if kind == "yaml":
                local_true = [n for n in true_ids if n in set(local_ids)]
                # also keep true ids that were only in yaml
                for n in true_ids:
                    if n in set(local_ids) and n not in local_true:
                        local_true.append(n)
            new_val = rewrite_new_value(
                ", ".join(
                    (
                        f"{n} ({parse_named_entries(val) and dict(parse_named_entries(val)).get(n)})"
                        if False
                        else n
                    )
                    for n in local_true
                )
                if False
                else val,
                false_set,
                local_true,
                canon,
                style_with_names,
            )
            # Simpler: rebuild from local entries
            entries = parse_named_entries(val)
            parts = []
            seen = set()
            for nid, nm in entries:
                if nid in false_set:
                    continue
                if nid in seen:
                    continue
                seen.add(nid)
                truth = canon.get(nid)
                if nm is not None:
                    if truth and nm.strip().lower() != truth.strip().lower():
                        parts.append(f"{nid} ({truth})")
                    else:
                        parts.append(f"{nid} ({nm})")
                else:
                    parts.append(nid)
            # ranges may have put ids without going through entries names - ensure local_true
            for nid in local_true:
                if nid not in seen:
                    seen.add(nid)
                    parts.append(nid)
            new_val = ", ".join(parts)
            text = text[:s] + new_val + text[e:]

    # Merge false into Existing/Reused
    text = ensure_existing_line(text, false_ids, canon, prefer_yaml=True)

    # Drop mistaken register rows
    text, dropped = drop_false_new_register_rows(text, false_set, intro, ep)

    # Update intro baseline with true news first-seen this ep
    for nid in true_ids:
        intro.setdefault(nid, ep)

    return text, false_ids, true_ids, dropped


def main() -> int:
    canon = load_canon_names()
    intro = build_batch12_baseline(DRAFTS)
    print(f"Batch1-2 baseline size: {len(intro)}")

    total_false = 0
    total_dropped = 0
    touched = []

    for ep in range(21, 157):
        path = DRAFTS / f"episode_{ep:03d}.md"
        if not path.is_file():
            continue
        original = path.read_text(encoding="utf-8")
        new_text, false_ids, true_ids, dropped = fix_episode(ep, original, intro, canon)
        # Also handle META on leftover New parentheticals even if no false
        if new_text != original:
            path.write_text(new_text, encoding="utf-8")
            touched.append(ep)
            total_false += len(false_ids)
            total_dropped += dropped
            if false_ids or dropped:
                print(
                    f"ep{ep}: moved {len(false_ids)} FALSE_NEW -> Existing/Reused; "
                    f"dropped_reg={dropped}; true_new={len(true_ids)}"
                )
                if false_ids:
                    print(f"  false: {', '.join(false_ids)}")
        else:
            # still record true new intros from unchanged files
            listings = collect_new_listings(original)
            claimed = []
            seen = set()
            for kind, s, e, val in listings:
                for nid in expand_ids_from_text(val):
                    if nid not in seen:
                        seen.add(nid)
                        claimed.append(nid)
            for nid in claimed:
                if nid not in intro:
                    intro[nid] = ep

    print(f"Touched episodes: {len(touched)} -> {touched}")
    print(f"Total FALSE_NEW moves (sum over eps): {total_false}")
    print(f"Total register rows dropped: {total_dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
