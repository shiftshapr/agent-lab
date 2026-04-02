"""Fetch Substack comments from published posts — Playwright."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .substack_cache import load as load_cache

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
REPLIES_CACHE = AGENT_LAB_ROOT / "data" / "replies_cache.json"
COMMENTS_MAX_PER_POST = 20


def _get_storage_state() -> Path | None:
    import os
    state = os.environ.get("LINKEDIN_STORAGE_STATE")
    if state:
        p = Path(state)
        if p.exists():
            return p
    default = AGENT_LAB_ROOT / "data" / "linkedin_state.json"
    return default if default.exists() else None


def _comment_id(post_url: str, author: str, text: str, date: str) -> str:
    raw = f"{post_url}|{author}|{text[:100]}|{date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def fetch_comments_for_post(post_url: str, post_title: str) -> list[dict]:
    """Fetch comments from a single Substack post page."""
    state_path = _get_storage_state()
    if not state_path:
        return []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    comments = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(state_path))
            context.set_default_timeout(15000)
            page = context.new_page()
            page.goto(post_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(3000)
            # Substack comments: various possible structures
            # Try common patterns
            els = page.query_selector_all(
                '[class*="comment"], [data-testid*="comment"], .comments .Comment, [class*="Comment"]'
            )
            if not els:
                els = page.query_selector_all('[class*="substack-comments"] [class*="comment"], article ~ div [class*="comment"]')
            seen_texts = set()
            for el in els[:COMMENTS_MAX_PER_POST]:
                try:
                    text_el = el.query_selector("[class*='content'], [class*='body'], [class*='text'], p")
                    text = (text_el.inner_text() if text_el else el.inner_text()).strip() if text_el else (el.inner_text() or "").strip()
                    if not text or len(text) < 3 or text in seen_texts:
                        continue
                    author_el = el.query_selector("[class*='author'], [class*='name'], a[href*='substack.com']")
                    author = (author_el.inner_text() if author_el else "").strip() or "Anonymous"
                    seen_texts.add(text)
                    cid = _comment_id(post_url, author, text, "")
                    comments.append({
                        "id": cid,
                        "post_url": post_url,
                        "post_title": post_title,
                        "author": author,
                        "text": text[:500],
                        "date": "",
                    })
                except Exception:
                    pass
            context.close()
            browser.close()
    except Exception:
        pass
    return comments


def fetch_all_comments(publication_id: str = "metaweb") -> list[dict]:
    """Fetch comments from published posts in cache. Returns flat list of comments."""
    cache = load_cache(publication_id)
    published = cache.get("published", [])[:10]  # Limit to 10 most recent posts
    all_comments = []
    for p in published:
        url = p.get("url", "")
        title = p.get("title", "") or url
        if url and "/p/" in url:
            comments = fetch_comments_for_post(url, title)
            all_comments.extend(comments)
    return all_comments


def load_replies_cache() -> dict:
    """Load cached comments and replied IDs."""
    if not REPLIES_CACHE.exists():
        return {"comments": [], "replied_ids": [], "updated_at": None}
    try:
        return json.loads(REPLIES_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {"comments": [], "replied_ids": [], "updated_at": None}


def save_replies_cache(comments: list[dict], replied_ids: list[str]) -> None:
    """Save comments cache."""
    REPLIES_CACHE.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    REPLIES_CACHE.write_text(
        json.dumps({
            "comments": comments,
            "replied_ids": replied_ids,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2),
        encoding="utf-8",
    )
