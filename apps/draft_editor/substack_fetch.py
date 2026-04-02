"""Fetch Substack drafts and published posts — Playwright for drafts, RSS for published."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

AGENT_LAB_ROOT = Path(__file__).resolve().parent.parent.parent
RSS_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DraftEditor/1.0)"}


def _get_storage_state() -> Path | None:
    state = os.environ.get("LINKEDIN_STORAGE_STATE")
    if state:
        p = Path(state)
        if p.exists():
            return p
    default = AGENT_LAB_ROOT / "data" / "linkedin_state.json"
    return default if default.exists() else None


def _urls_for_domain(domain: str) -> tuple[str, str, str, str]:
    base = f"https://{domain}"
    return (f"{base}/feed", f"{base}/publish/posts/drafts", f"{base}/publish/posts/scheduled", base)


def fetch_published(domain: str) -> list[dict[str, str]]:
    """Fetch published posts from RSS feed. No auth needed."""
    rss_url, _, _, _ = _urls_for_domain(domain)
    items = []
    try:
        req = Request(rss_url, headers=RSS_HEADERS)
        with urlopen(req, timeout=15) as resp:
            tree = ET.parse(resp)
            root = tree.getroot()
            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                url = (link_el.text or "").strip() if link_el is not None and link_el.text else ""
                title = (title_el.text or "").strip() if title_el is not None else ""
                pub_date = (pub_el.text or "").strip() if pub_el is not None and pub_el.text else ""
                if pub_date:
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(pub_date[:25], "%a, %d %b %Y %H:%M:%S")
                        pub_date = dt.strftime("%b ") + str(dt.day) + dt.strftime(", %Y")
                    except Exception:
                        pass
                if url and "/p/" in url:
                    items.append({"url": url, "title": title or url, "date": pub_date})
    except Exception:
        pass
    return items[:50]  # Limit


def fetch_drafts(domain: str) -> list[dict[str, str]]:
    """Fetch drafts via Playwright with saved session."""
    state_path = _get_storage_state()
    if not state_path:
        return []

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    _, drafts_url, _, base_url = _urls_for_domain(domain)
    items = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(state_path))
            context.set_default_timeout(20000)
            page = context.new_page()
            page.goto(drafts_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(4000)
            items = _scrape_post_links(page, base_url, drafts_url)
            context.close()
            browser.close()
    except Exception:
        pass
    return items


def fetch_scheduled(domain: str) -> list[dict[str, str]]:
    """Fetch scheduled posts via Playwright."""
    state_path = _get_storage_state()
    if not state_path:
        return []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    _, _, scheduled_url, base_url = _urls_for_domain(domain)
    items = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(state_path))
            context.set_default_timeout(20000)
            page = context.new_page()
            page.goto(scheduled_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(4000)
            items = _scrape_post_links(page, base_url, scheduled_url)
            context.close()
            browser.close()
    except Exception:
        pass
    return items


def _scrape_post_links(page, base_url: str, skip_url: str) -> list[dict[str, str]]:
    """Scrape /publish/post/ links from a Substack list page."""
    links = page.query_selector_all('a[href*="/publish/post/"]')
    seen: set[str] = set()
    out = []
    for el in links:
        href = (el.get_attribute("href") or "").strip()
        if not href or href in seen:
            continue
        if "login" in href or "signin" in href or href.endswith("/drafts") or href.endswith("/scheduled"):
            continue
        if not href.startswith("http"):
            href = base_url + (href.split("?")[0] if "?" in href else href)
        if href == skip_url:
            continue
        text = (el.inner_text() or "").strip().split("\n")[0] or href
        seen.add(href)
        item = {"url": href, "title": text[:80]}
        if "Schedule" in text or "schedule" in text.lower() or len(text.split("•")) > 1:
            parts = text.split("•")
            if len(parts) >= 2:
                item["date"] = parts[-1].strip()[:30]
        out.append(item)
    return out


def fetch_all(domain: str) -> dict[str, Any]:
    """Return drafts, scheduled, and published for a given Substack domain."""
    return {
        "drafts": fetch_drafts(domain),
        "scheduled": fetch_scheduled(domain),
        "published": fetch_published(domain),
    }


def run_refresh_background(publication_id: str, domain: str) -> None:
    """Fetch and merge new items into cache. Call in a thread."""
    from .substack_cache import clear_refreshing, merge_and_save, mark_refreshing

    mark_refreshing(publication_id)
    try:
        data = fetch_all(domain)
        merge_and_save(publication_id, data["drafts"], data["scheduled"], data["published"])
    except Exception:
        clear_refreshing(publication_id)
