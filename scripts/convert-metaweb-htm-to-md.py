#!/usr/bin/env python3
"""Convert Metaweb book HTML exports under knowledge/docs/*.htm to Markdown.

Each output file gets, directly under the # title:
  **On-chain:** https://ordinals.com/content/<inscriptionId>

If `knowledge/docs/metaweb_inscriptions.csv` exists (columns: inscriptionId, address,
filename), the **On-chain** id comes from that file; otherwise the first `/content/...`
id in the HTML (cover image) is used. See knowledge/README.md.
"""

from __future__ import annotations

import csv
import re
import sys
from html import unescape
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

AGENT_LAB = Path(__file__).resolve().parents[1]
DOCS = AGENT_LAB / "knowledge" / "docs"

CONTENT_ID_RE = re.compile(r"/content/([a-fA-F0-9]+i\d+)")
INSCRIPTIONS_CSV = DOCS / "metaweb_inscriptions.csv"


def load_inscription_map() -> dict[str, str]:
    """Map `ch01.htm` -> inscription id from CSV."""
    if not INSCRIPTIONS_CSV.is_file():
        return {}
    out: dict[str, str] = {}
    with INSCRIPTIONS_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fn = (row.get("filename") or "").strip()
            iid = (row.get("inscriptionId") or "").strip()
            if fn and iid:
                out[fn] = iid
    return out


def _extract_cover_inscription(html: str) -> str | None:
    m = CONTENT_ID_RE.search(html)
    return m.group(1) if m else None


def _escape_md_inline(text: str) -> str:
    return text.replace("\\", "\\\\")


def inline_to_md(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        t = str(node)
        return _escape_md_inline(unescape(t))
    if not isinstance(node, Tag):
        return ""
    name = node.name.lower()
    if name == "a":
        href = (node.get("href") or "").strip()
        inner = "".join(inline_to_md(c) for c in node.children)
        if not href:
            return inner
        return f"[{inner}]({href})"
    if name in ("em", "i"):
        inner = "".join(inline_to_md(c) for c in node.children)
        return f"*{inner}*" if inner else ""
    if name in ("strong", "b"):
        inner = "".join(inline_to_md(c) for c in node.children)
        return f"**{inner}**" if inner else ""
    if name == "span" and "endnote" in (node.get("class") or []):
        n = node.get_text(strip=True)
        return f"[^{n}]" if n else ""
    if name == "br":
        return "\n"
    return "".join(inline_to_md(c) for c in node.children)


def block_feature_box(box: Tag, lines: list[str]) -> None:
    inner: list[str] = []
    for child in box.children:
        if isinstance(child, NavigableString):
            t = unescape(str(child)).strip()
            if t:
                inner.append(t)
        elif isinstance(child, Tag):
            if child.name.lower() == "p":
                inner.append(inline_to_md(child).strip())
            elif child.name.lower() in ("em", "i", "strong", "b"):
                inner.append(inline_to_md(child).strip())
            else:
                inner.append(child.get_text(" ", strip=True))
    text = "\n\n".join(s for s in inner if s)
    if text:
        for para in text.split("\n\n"):
            lines.append("\n".join(f"> {ln}" for ln in para.split("\n")) + "\n\n")


def block_quote(div: Tag, lines: list[str]) -> None:
    q = inline_to_md(div).strip()
    if q:
        lines.append(f"> {q}\n\n")


def walk_children(
    parent: Tag,
    lines: list[str],
    *,
    skip_leading_cover_img: list[bool],
    inscription: str | None,
    on_chain_emitted: list[bool],
) -> None:
    for child in parent.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name.lower()
        classes = child.get("class") or []

        if name == "img":
            src = (child.get("src") or "").strip()
            m = CONTENT_ID_RE.search(src)
            if m and skip_leading_cover_img[0]:
                skip_leading_cover_img[0] = False
                continue
            alt = (child.get("alt") or "Figure").strip()
            if m:
                url = f"https://ordinals.com/content/{m.group(1)}"
                lines.append(f"![{alt}]({url})\n\n")
            continue

        if name == "div" and "heading1" in classes:
            title = child.get_text(" ", strip=True)
            if title:
                lines.append(f"# {title}\n\n")
                if not on_chain_emitted[0]:
                    ins = inscription if inscription else "<inscriptionId>"
                    lines.append(f"**On-chain:** https://ordinals.com/content/{ins}\n\n")
                    on_chain_emitted[0] = True
            continue

        if name == "div" and "heading2" in classes:
            t = child.get_text(" ", strip=True)
            if t:
                lines.append(f"## {t}\n\n")
            continue

        if name == "div" and "quote" in classes:
            block_quote(child, lines)
            continue

        if name == "div" and "quotedby" in classes:
            t = child.get_text(" ", strip=True)
            if t:
                lines.append(f"— {t}\n\n")
            continue

        if name == "div" and "feature-box" in classes:
            block_feature_box(child, lines)
            continue

        if name == "div" and "centeredbody" in classes:
            walk_children(
                child,
                lines,
                skip_leading_cover_img=skip_leading_cover_img,
                inscription=inscription,
                on_chain_emitted=on_chain_emitted,
            )
            continue

        if name == "p":
            raw = "".join(inline_to_md(c) for c in child.children).strip()
            if raw:
                lines.append(raw + "\n\n")
            continue

        if name == "ul":
            for li in child.find_all("li", recursive=False):
                item = inline_to_md(li).strip()
                if item:
                    lines.append(f"- {item}\n")
            lines.append("\n")
            continue

        if name == "div":
            walk_children(
                child,
                lines,
                skip_leading_cover_img=skip_leading_cover_img,
                inscription=inscription,
                on_chain_emitted=on_chain_emitted,
            )


def htm_to_md(path: Path, inscription_by_htm: dict[str, str] | None = None) -> str:
    html = path.read_text(encoding="utf-8", errors="replace")
    if inscription_by_htm and path.name in inscription_by_htm:
        inscription = inscription_by_htm[path.name]
    else:
        inscription = _extract_cover_inscription(html)
    soup = BeautifulSoup(html, "html.parser")
    body = soup.body
    if not body:
        return ""
    root = body.find("div") or body
    lines: list[str] = []
    skip_flag = [True]
    on_chain_emitted = [False]
    walk_children(
        root,
        lines,
        skip_leading_cover_img=skip_flag,
        inscription=inscription,
        on_chain_emitted=on_chain_emitted,
    )
    text = "".join(lines).strip() + "\n"
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main() -> int:
    if not DOCS.is_dir():
        print(f"Missing {DOCS}", file=sys.stderr)
        return 1
    paths = sorted(DOCS.glob("*.htm"))
    if not paths:
        print("No .htm files in knowledge/docs", file=sys.stderr)
        return 1
    inscription_by_htm = load_inscription_map()
    if inscription_by_htm:
        print(f"Loaded {len(inscription_by_htm)} inscription(s) from {INSCRIPTIONS_CSV.name}")
    for htm in paths:
        md_path = htm.with_suffix(".md")
        md_path.write_text(htm_to_md(htm, inscription_by_htm), encoding="utf-8")
        print(f"Wrote {md_path.relative_to(AGENT_LAB)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
