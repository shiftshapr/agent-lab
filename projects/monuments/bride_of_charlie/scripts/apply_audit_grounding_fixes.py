#!/usr/bin/env python3
"""One-shot grounding repairs for full audit at 3fcfe0b (Daveed inscription held)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PROJECT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import pipeline_gates as pg  # noqa: E402
from repair_grounding_snippets import extract_verbatim_snippet  # noqa: E402

DRAFTS = PROJECT / "drafts"

# claim_id -> fields to set (None = omit)
CLAIM_FIXES: dict[str, dict] = {
    "C-1000": {
        "claim_timestamp": "00:01",
        "anchored_artifacts": "A-1000.2",
        "snippet_hint": (1, 0, 45),
    },
    "C-1005": {
        "claim_timestamp": "37:00",
        "anchored_artifacts": "A-1005.1",
        "snippet_hint": (1, 37 * 60, 37 * 60 + 40),
    },
    "C-1014": {
        "claim_timestamp": "20:03",
        "anchored_artifacts": "A-1010.3",
        "snippet_hint": (2, 20 * 60 + 3, 21 * 60 + 6),
    },
    "C-1016": {
        "claim_timestamp": "32:05",
        "anchored_artifacts": "A-1012.2",
        "snippet_hint": (2, 32 * 60 + 5, 33 * 60 + 0),
    },
    "C-1017": {
        "claim_timestamp": "44:25",
        "anchored_artifacts": "A-1013.2",
        "snippet_hint": (2, 44 * 60 + 25, 46 * 60 + 4),
    },
    "C-1029": {
        "claim_timestamp": "44:10",
        "anchored_artifacts": "A-1021.2",
        "snippet_hint": (3, 43 * 60 + 56, 45 * 60 + 16),
    },
    "C-1063": {
        "claim_timestamp": "36:06",
        "anchored_artifacts": "A-1037.2",
        "snippet_hint": (5, 36 * 60 + 6, 36 * 60 + 28),
    },
    "C-1066": {
        "claim_timestamp": "55:14",
        "anchored_artifacts": "A-1037.3",
        "snippet_hint": (5, 55 * 60 + 14, 55 * 60 + 32),
    },
    "C-1041": {
        "claim_timestamp": "02:10",
        "anchored_artifacts": "A-1035.3",
        "snippet_hint": (5, 2 * 60 + 10, 2 * 60 + 39),
    },
    "C-1058": {
        "claim_timestamp": "26:38",
        "anchored_artifacts": "A-1032.5",
        "snippet_hint": (5, 26 * 60 + 38, 26 * 60 + 55),
    },
    "C-1083": {
        "claim_timestamp": "42:56",
        "anchored_artifacts": "A-1050.1",
        "snippet_hint": (6, 42 * 60 + 56, 43 * 60 + 30),
    },
    "C-1081": {
        "claim_timestamp": "32:59",
        "anchored_artifacts": "A-1049.2",
        "snippet_hint": (6, 32 * 60 + 59, 33 * 60 + 36),
    },
    "C-1088": {
        "claim_timestamp": "02:09",
        "anchored_artifacts": "A-1055.1",
        "snippet_hint": (7, 2 * 60 + 9, 3 * 60 + 48),
    },
    "C-1107": {
        "claim_timestamp": "23:01",
        "anchored_artifacts": "A-1073.1",
        "snippet_hint": (8, 23 * 60 + 1, 23 * 60 + 24),
    },
    "C-1105": {
        "claim_timestamp": "10:54-11:12",
        "anchored_artifacts": "A-1069.4",
        "snippet_hint": (8, 10 * 60 + 54, 11 * 60 + 12),
    },
    "C-1112": {
        "claim_timestamp": "33:14",
        "anchored_artifacts": "A-1071.1",
        "snippet_hint": (8, 33 * 60 + 14, 33 * 60 + 28),
    },
    "C-1100": {
        "claim_timestamp": "00:03",
        "anchored_artifacts": "A-1074.1",
        "snippet_hint": (8, 3, 28),
    },
}

ARTIFACT_INSERTS: dict[int, list[str]] = {
    1: [
        """
**A-1000.2** TPUSA CEO insertion framing (episode opening narration)
Event Timestamp: Undated in episode source
Event Timestamp Note: no calendar date attested in episode transcript; left undated deliberately.
Video Timestamp: 00:01–00:33
*Related: C-1000, N-2, N-1034*
Transcript Snippet: PLACEHOLDER
Confidence: high
""",
    ],
    2: [
        """
**A-1010.3** Jerry Frantzve DuPont employment (narration)
Event Timestamp: 1983
Video Timestamp: 20:03–21:06
*Related: C-1014, N-12, N-1047*
Transcript Snippet: PLACEHOLDER
Confidence: medium
""",
        """
**A-1012.2** Phil Bliss Tesseract board / MK Ultra connection (narration)
Event Timestamp: 1990s
Video Timestamp: 32:05–33:00
*Related: C-1016, N-14, N-1035, N-1037*
Transcript Snippet: PLACEHOLDER
Confidence: medium
""",
        """
**A-1013.2** Tyler Bowyer introduced Erika to Charlie (narration)
Event Timestamp: Undated in episode source
Event Timestamp Note: no calendar date attested in episode transcript; left undated deliberately.
Video Timestamp: 44:25–46:04
*Related: C-1017, N-1, N-2, N-13, N-1046*
Transcript Snippet: PLACEHOLDER
Confidence: medium
""",
    ],
    3: [
        """
**A-1021.2** Erika social posts — Terry Crist / Hillsong connection
Event Timestamp: 2011–2016
Video Timestamp: 43:56–45:16
*Related: C-1029, N-2, N-46, N-47*
Transcript Snippet: PLACEHOLDER
Confidence: medium
""",
    ],
    5: [
        """
**A-1035.3** Radford Eastern Europe gender-research document (1990)
Event Timestamp: 1990
Video Timestamp: 02:10–02:39
*Related: C-1041, N-12, N-1054*
Transcript Snippet: PLACEHOLDER
Confidence: medium
""",
        """
**A-1032.5** Table Four LLC filing (Erika and Tyler Sanford, 2010)
Event Timestamp: 2010
Video Timestamp: 26:38–26:55
*Related: C-1058, N-2, N-58*
Transcript Snippet: PLACEHOLDER
Confidence: high
""",
        """
**A-1037.2** Erika account — Charlie Kirk Israel airport meeting
Event Timestamp: Undated in episode source
Event Timestamp Note: no calendar date attested in episode transcript; left undated deliberately.
Video Timestamp: 36:06–36:28
*Related: C-1063, N-1, N-2, N-3*
Transcript Snippet: PLACEHOLDER
Confidence: medium
""",
        """
**A-1037.3** Tyler Bowyer Romania / Farnsworth connection (narration)
Event Timestamp: 2010
Video Timestamp: 55:14–55:32
*Related: C-1066, N-13, N-1054*
Transcript Snippet: PLACEHOLDER
Confidence: low
""",
    ],
    6: [
        """
**A-1049.2** Erika cannot remember meeting Tyler Bowyer (narration)
Event Timestamp: Undated in episode source
Event Timestamp Note: no calendar date attested in episode transcript; left undated deliberately.
Video Timestamp: 32:59–33:36
*Related: C-1081, N-2, N-13, N-1025*
Transcript Snippet: PLACEHOLDER
Confidence: medium
""",
    ],
    8: [
        """
**A-1069.4** Erika Bible in 365 founding claim (social media)
Event Timestamp: 2016
Video Timestamp: 10:54–11:12
*Related: C-1105, N-2, N-1083*
Transcript Snippet: PLACEHOLDER
Confidence: medium
""",
        """
**A-1074** Andrew Kolvet Interview Clip

**A-1074.1** Andrew Kolvet on Dave Rubin show — Erika spotlight claim
Event Timestamp: Undated in episode source
Event Timestamp Note: no calendar date attested in episode transcript; left undated deliberately.
Video Timestamp: 00:03–00:28
*Related: C-1100, N-2, N-26, N-1*
Transcript Snippet: PLACEHOLDER
Confidence: high

---
""",
    ],
}

RELATED_PATCHES: list[tuple[str, str, str]] = [
    # (file suffix ep, old related line fragment, new)
    ("episode_002.md", "*Related: C-1014, C-1016, N-12, N-1035, N-1045*", "*Related: C-1016, N-12, N-1035, N-1045*"),
    ("episode_002.md", "*Related: C-1018, N-2, N-3*", "*Related: C-1018, C-1017, N-2, N-3*"),
    ("episode_003.md", "*Related: C-1031, N-2, N-1*", "*Related: C-1031, C-1029, N-2, N-1*"),
    ("episode_005.md", "*Related: C-1060, C-1061, N-13, N-1054*", "*Related: C-1060, C-1061, C-1063, C-1066, N-13, N-1054*"),
    ("episode_008.md", "*Related: C-1104, N-3, N-1079*", "*Related: C-1104, C-1105, N-3, N-1079*"),
    ("episode_008.md", "*Related: A-1069.1, A-1069.2, A-1070.1, A-1072.1, A-1073.1, C-1107, C-1106, C-1105", "*Related: A-1069.2, A-1069.4, A-1070.1, A-1072.1, A-1073.1, A-1074.1, C-1107, C-1106, C-1105, C-1100"),
]


def _transcript(ep: int) -> str:
    p = pg.resolve_corrected_transcript(PROJECT, ep)
    if not p:
        raise FileNotFoundError(f"no transcript for ep {ep}")
    return p.read_text(encoding="utf-8")


def _fill_placeholders(block: str, ep: int, start: int, end: int) -> str:
    tx = _transcript(ep)
    snip = extract_verbatim_snippet(tx, start, end, pad_before=0, pad_after=30)
    return block.replace("Transcript Snippet: PLACEHOLDER", f"Transcript Snippet: {snip}")


def _set_claim_field(section: str, field: str, value: str) -> str:
    pat = re.compile(rf"^{re.escape(field)}:\s*.*$", re.MULTILINE)
    line = f"{field}: {value}"
    if pat.search(section):
        return pat.sub(line, section, count=1)
    return section.rstrip() + f"\n{line}\n"


def _extract_claim_blocks(content: str) -> tuple[str, str, str, list[tuple[int, str]]]:
    m = re.search(r"^## 5\. Claim Register\s*$", content, re.MULTILINE)
    if not m:
        raise ValueError("no claim register")
    start = m.end()
    m6 = re.search(r"^## 6\. Meme Register\s*$", content[start:], re.MULTILINE)
    end = start + m6.start() if m6 else len(content)
    prefix = content[:start]
    register = content[start:end]
    suffix = content[end:]
    blocks: list[tuple[int, str]] = []
    for cm in re.finditer(r"^\*\*C-(\d+)\*\*[^\n]*\n", register, re.MULTILINE):
        cid = int(cm.group(1))
        bstart = cm.start()
        nxt = re.search(r"^\*\*C-\d+\*\*", register[cm.end() :], re.MULTILINE)
        bend = cm.end() + nxt.start() if nxt else len(register)
        blocks.append((cid, register[bstart:bend]))
    return prefix, register, suffix, blocks


def _claim_sort_key(block: str) -> tuple[int, int]:
    m = re.search(r"^Claim Timestamp:\s*(.+)$", block, re.MULTILINE)
    if not m:
        return (999999, 0)
    raw = m.group(1).strip().split("-")[0].strip()
    sec = pg._parse_hms_to_seconds(raw) or 999999
    cm = re.search(r"^\*\*C-(\d+)\*\*", block)
    cid = int(cm.group(1)) if cm else 0
    return (sec, cid)


def _apply_claim_fixes(content: str, ep: int) -> str:
    matches = list(re.finditer(r"^\*\*C-(\d+)\*\*[^\n]*\n", content, re.MULTILINE))
    for cm in reversed(matches):
        cid = f"C-{cm.group(1)}"
        if cid not in CLAIM_FIXES:
            continue
        fix = CLAIM_FIXES[cid]
        bstart = cm.start()
        nxt = re.search(r"^\*\*C-\d+\*\*", content[cm.end() :], re.MULTILINE)
        bend = cm.end() + nxt.start() if nxt else len(content)
        section = content[bstart:bend]
        if fix.get("claim_timestamp") is not None:
            section = _set_claim_field(section, "Claim Timestamp", fix["claim_timestamp"])
        if fix.get("anchored_artifacts") is not None:
            section = _set_claim_field(section, "Anchored Artifacts", fix["anchored_artifacts"])
        if "snippet_hint" in fix:
            _, s, e = fix["snippet_hint"]
            tx = _transcript(ep)
            snip = extract_verbatim_snippet(tx, s, e, pad_before=0, pad_after=25)
            section = _set_claim_field(section, "Transcript Snippet", snip)
        content = content[:bstart] + section + content[bend:]
    return content


def _insert_artifacts(content: str, ep: int) -> str:
    inserts = ARTIFACT_INSERTS.get(ep, [])
    if not inserts:
        return content
    m = re.search(r"^## 4\. Node Register\s*$", content, re.MULTILINE)
    if not m:
        raise ValueError(f"ep{ep}: no node register")
    pos = m.start()
    filled = []
    for block in inserts:
        if "PLACEHOLDER" in block:
            # infer window from first Video Timestamp line
            vts = re.search(r"Video Timestamp:\s*([0-9:\-–—]+)", block)
            if vts:
                parts = re.split(r"[–—-]", vts.group(1).strip())
                start = pg._parse_hms_to_seconds(parts[0].strip()) or 0
                end = pg._parse_hms_to_seconds(parts[-1].strip()) if len(parts) > 1 else start
                block = _fill_placeholders(block, ep, start, end)
        filled.append(block.strip() + "\n\n---\n")
    return content[:pos] + "\n".join(filled) + content[pos:]


def _resort_claims(content: str) -> str:
    prefix, register, suffix, blocks = _extract_claim_blocks(content)
    if not blocks:
        return content
    blocks.sort(key=lambda x: _claim_sort_key(x[1]))
    parts = [b.rstrip() for _, b in blocks]
    new_register = "\n\n" + "\n\n---\n\n".join(parts) + "\n\n"
    return prefix + new_register + suffix


def main() -> int:
    for ep in range(1, 9):
        path = DRAFTS / f"episode_{ep:03d}.md"
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        content = _insert_artifacts(content, ep)
        content = _apply_claim_fixes(content, ep)
        content = _resort_claims(content)
        path.write_text(content, encoding="utf-8")
        print(f"[fix] updated {path.name}")

    for fname, old, new in RELATED_PATCHES:
        path = DRAFTS / fname
        text = path.read_text(encoding="utf-8")
        if old in text:
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            print(f"[fix] related patch {fname}")

    # ep8 ledger: new artifact family A-1074
    ep8 = DRAFTS / "episode_008.md"
    t = ep8.read_text(encoding="utf-8")
    if "A-1074" not in t.split("Artifact Families")[1].split("Claim Range")[0]:
        t = t.replace(
            "Artifact Families Introduced: A-1067, A-1068, A-1069, A-1070, A-1071, A-1072, A-1073",
            "Artifact Families Introduced: A-1067, A-1068, A-1069, A-1070, A-1071, A-1072, A-1073, A-1074",
        )
        t = t.replace(
            "New Nodes Introduced: N-64, N-66",
            "New Nodes Introduced: N-64, N-66",
        )
        ep8.write_text(t, encoding="utf-8")

    # Update N-2 related in ep8 for C-1100 anchor cleanup
    t = ep8.read_text(encoding="utf-8")
    t = t.replace(
        "*Related: A-1069.1, A-1069.2, A-1070.1, A-1072.1, A-1073.1, C-1107, C-1106, C-1105, C-1108, C-1109, C-1110, C-1101, C-1112, C-1100*",
        "*Related: A-1069.2, A-1069.4, A-1070.1, A-1072.1, A-1073.1, A-1074.1, C-1107, C-1106, C-1105, C-1108, C-1109, C-1110, C-1101, C-1112, C-1100*",
    )
    t = t.replace(
        "*Related: C-1100*",
        "*Related: A-1074.1, C-1100*",
    )
    ep8.write_text(t, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
