#!/usr/bin/env python3
"""CKA source model (ROADMAP 3.0): episode JSON is the master copy; Markdown drafts are rendered from it.

An episode source file (source/episode_NNN.json) is an ordered list of blocks:
- {"kind": "text", "lines": [...]}: anything that is not a register item, kept verbatim;
- {"kind": "claim" | "artifact" | "node" | "meme", "id": "C-12", "header": "**C-12** label", "label": "label",
   "lines": [entry, ...]}: one register item. An entry is {"k": key, "v": value} for a `Key: value` field line (plus
   "sep" when the separator is not ": "), or {"raw": line} for anything else (blank lines, separators, prose,
   *Related:* lines, meme occurrence headings).
Rendering joins the lines back with "\\n", so render(parse(md)) == md byte for byte (checked for every draft in CI).

Library: parse_md(text, episode) -> doc; render(doc) -> text; items(doc, kind); field(item, key);
set_field(item, key, value); load(seq); save(doc) (writes the JSON and re-renders the draft).
CLI (from agent-lab root):
  python3 projects/monuments/cka/scripts/source/cka_source.py sync     # drafts -> source JSON (Phase A)
  python3 projects/monuments/cka/scripts/source/cka_source.py render   # source JSON -> drafts
  python3 projects/monuments/cka/scripts/source/cka_source.py check    # round trip and freshness; non-zero on drift
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
SRC = CKA / "source"
DRAFTS = CKA / "drafts"
FORMAT = "cka-source/1"
ITEM_RE = re.compile(r"^\*\*((C|A|N|M)-\d+(?:\.\d+)?)\*\*[:\s]?(.*)$")
KIND = {"C": "claim", "A": "artifact", "N": "node", "M": "meme"}
FIELD_RE = re.compile(r"^([A-Z][A-Za-z0-9 /()'&-]{1,48}?)(:\s?)(.*)$")


def _entry(line: str) -> dict:
    m = FIELD_RE.match(line)
    if m and not line.startswith("**"):
        e = {"k": m.group(1), "v": m.group(3)}
        if m.group(2) != ": ":
            e["sep"] = m.group(2)
        if f"{e['k']}{m.group(2)}{e['v']}" == line:
            return e
    return {"raw": line}


def _entry_text(e: dict) -> str:
    return e["raw"] if "raw" in e else f"{e['k']}{e.get('sep', ': ')}{e['v']}"


def parse_md(text: str, episode: int) -> dict:
    lines = text.split("\n")
    blocks: list[dict] = []
    cur: dict | None = None
    for line in lines:
        m = ITEM_RE.match(line)
        if m:
            cur = {"kind": KIND[m.group(2)], "id": m.group(1), "header": line, "label": m.group(3).strip(), "lines": []}
            blocks.append(cur)
            continue
        if line.startswith("#") and not line.startswith("### Occurrence"):
            cur = None
        if cur is None:
            if not blocks or blocks[-1]["kind"] != "text":
                blocks.append({"kind": "text", "lines": []})
            blocks[-1]["lines"].append(line)
        else:
            cur["lines"].append(_entry(line))
    return {"format": FORMAT, "episode": episode, "blocks": blocks}


def render(doc: dict) -> str:
    out: list[str] = []
    for b in doc["blocks"]:
        if b["kind"] == "text":
            out.extend(b["lines"])
        else:
            out.append(b["header"])
            out.extend(_entry_text(e) for e in b["lines"])
    return "\n".join(out)


def items(doc: dict, kind: str | None = None):
    return [b for b in doc["blocks"] if b["kind"] != "text" and (kind is None or b["kind"] == kind)]


def field(item: dict, key: str) -> str | None:
    for e in item["lines"]:
        if e.get("k") == key:
            return e["v"]
    return None


def set_field(item: dict, key: str, value: str) -> None:
    for e in item["lines"]:
        if e.get("k") == key:
            e["v"] = value
            return
    raise KeyError(f"{item.get('id')}: no field {key!r}")


def src_path(seq: int) -> Path:
    return SRC / f"episode_{seq:03d}.json"


def load(seq: int) -> dict:
    return json.loads(src_path(seq).read_text(encoding="utf-8"))


def dump(doc: dict) -> str:
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def save(doc: dict) -> None:
    seq = doc["episode"]
    src_path(seq).write_text(dump(doc), encoding="utf-8")
    (DRAFTS / f"episode_{seq:03d}.md").write_text(render(doc), encoding="utf-8")


REQUIRED = {"claim": ("Claim Timestamp", "Claim", "Anchored Artifacts")}
ID_KIND = {"claim": "C-", "artifact": "A-", "node": "N-", "meme": "M-"}


def validate(doc: dict) -> list[str]:
    """Schema checks for one episode source: block shapes, item kinds and id prefixes, required claim fields,
    claim ids unique within the episode."""
    errs, seen = [], set()
    if doc.get("format") != FORMAT or not isinstance(doc.get("episode"), int) or not isinstance(doc.get("blocks"), list):
        return ["bad top-level shape"]
    for b in doc["blocks"]:
        k = b.get("kind")
        if k == "text":
            if not isinstance(b.get("lines"), list) or not all(isinstance(x, str) for x in b["lines"]):
                errs.append("text block with non-string lines")
            continue
        if k not in ID_KIND or not str(b.get("id", "")).startswith(ID_KIND[k]):
            errs.append(f"bad item {b.get('id')} ({k})")
            continue
        for e in b.get("lines", []):
            if not (("raw" in e and isinstance(e["raw"], str)) or ("k" in e and "v" in e)):
                errs.append(f"{b['id']}: bad line entry")
        if k == "claim":
            if b["id"] in seen:
                errs.append(f"{b['id']}: duplicate claim")
            seen.add(b["id"])
            keys = {e.get("k") for e in b["lines"]}
            errs += [f"{b['id']}: missing {f}" for f in REQUIRED["claim"] if f not in keys]
    return errs


def _drafts():
    for p in sorted(DRAFTS.glob("episode_*.md")):
        m = re.fullmatch(r"episode_(\d+)\.md", p.name)
        if m:
            yield int(m.group(1)), p


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "check"
    SRC.mkdir(exist_ok=True)
    bad = []
    for seq, p in _drafts():
        md = p.read_text(encoding="utf-8")
        if cmd == "sync":
            doc = parse_md(md, seq)
            if render(doc) != md:
                bad.append(f"{p.name}: round trip differs")
                continue
            src_path(seq).write_text(dump(doc), encoding="utf-8")
        elif cmd == "render":
            p.write_text(render(load(seq)), encoding="utf-8")
        elif cmd == "check":
            if not src_path(seq).exists():
                bad.append(f"{p.name}: no source JSON")
                continue
            doc = load(seq)
            bad += [f"{p.name}: {e}" for e in validate(doc)]
            if render(doc) != md:
                bad.append(f"{p.name}: draft is not the render of source/episode_{seq:03d}.json")
    extra = [p.name for p in SRC.glob("episode_*.json") if not (DRAFTS / p.name.replace(".json", ".md")).exists()]
    bad += [f"{x}: source without a draft" for x in extra]
    print(f"{cmd}: {len(list(_drafts()))} episodes, {len(bad)} problems")
    for b in bad[:30]:
        print("  ", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
