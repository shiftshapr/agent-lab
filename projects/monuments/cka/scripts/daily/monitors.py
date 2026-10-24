#!/usr/bin/env python3
"""Daily external monitors (ROADMAP 4.2): court calendar and news alerts for the CKA pipeline.

Polls the sources in config/monitors.json:
- the Utah court calendar for each tracked case (public; hearings in the next ~30 days);
- Google News RSS for each query, keeping items from the last `days` days and marking Tier 2 outlets.
Alerts already seen (state in ~/agent-lab-data/cka_monitor/seen.json, kept outside the repo) are skipped. New alerts
are written to WORK/monitor_alerts.json and appended to ledger/monitor_alerts.json (rendered to .md). Alerts are
leads, never evidence; nothing is downloaded beyond the listing pages.

Usage: monitors.py WORK [--dry-run] [--state PATH] | monitors.py WORK --render
Exit status: 0 with new alerts, 3 when there is nothing new, 1 on error (a source failing is reported, not fatal).
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CKA = Path(__file__).resolve().parents[2]
CONF = CKA / "config" / "monitors.json"
LEDGER = CKA / "ledger" / "monitor_alerts.json"
UA = {"User-Agent": "Mozilla/5.0 (CKA monitor)"}


def get(url: str, timeout: int = 30) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def key(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def court(conf: dict) -> list[dict]:
    out = []
    for c in conf["cases"]:
        page = get(conf["url"].format(case=c["case"]))
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
        if "No results found" in text:
            continue
        # each hearing is a block starting at <div class="col-xs-8"> (time, type, date, court, parties, judge,
        # room and hearing type, "Case # NNN")
        for b in page.split('<div class="col-xs-8"')[1:]:
            if c["case"] not in b:
                continue
            line = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", '<x' + b))).strip()
            line = re.sub(r"\(\s*Hearing location is in [^)]*\)|View Case.*$", "", line).strip()
            out.append({"kind": "court_calendar", "case": c["case"], "title": c["title"], "entry": line[:300],
                        "url": conf["url"].format(case=c["case"]), "id": key("cal", c["case"], line[:300])})
        if not out:  # results exist but the table layout changed: alert on the page text itself
            out.append({"kind": "court_calendar", "case": c["case"], "title": c["title"], "entry": text[:400],
                        "url": conf["url"].format(case=c["case"]), "id": key("cal", c["case"], text[:400])})
    return out


def news(conf: dict) -> list[dict]:
    t2 = set(conf["tier2_domains"])
    seen, out = set(), []
    for q in conf["queries"]:
        root = ET.fromstring(get(conf["url"].format(q=urllib.parse.quote_plus(q), days=conf["days"])))
        for it in root.findall(".//item"):
            title = it.findtext("title") or ""
            src = it.find("source")
            dom = urllib.parse.urlparse(src.get("url", "") if src is not None else "").netloc.removeprefix("www.")
            outlet = (src.text if src is not None else "") or dom
            title = re.sub(r"\s+-\s+" + re.escape(outlet) + r"$", "", title)
            k = key("news", dom, title.lower())
            if k in seen:
                continue
            seen.add(k)
            pub = it.findtext("pubDate")
            date = email.utils.parsedate_to_datetime(pub).date().isoformat() if pub else None
            out.append({"kind": "news", "id": k, "date": date, "outlet": outlet, "domain": dom,
                        "tier2": dom in t2, "title": title, "url": it.findtext("link"), "query": q})
    return out


def render(alerts: list[dict]) -> str:
    md = ["# Monitor alerts (ROADMAP 4.2)", "",
          "Leads from `scripts/daily/monitors.py`, newest first. They are never evidence: a news item becomes a source "
          "only after Daveed approves it, and court calendar entries are scheduling data. `status` is set at triage "
          "(new → triaged / approved / ignored).", ""]
    for a in sorted(alerts, key=lambda a: (a.get("seen"), a.get("date") or ""), reverse=True):
        if a["kind"] == "court_calendar":
            md.append(f"- {a['seen']} · **court calendar** · {a['title']}: {a['entry']} · [search]({a['url']}) · {a.get('status', 'new')}")
        else:
            tier = "Tier 2" if a["tier2"] else "other"
            md.append(f"- {a['seen']} · {tier} · {a['outlet']} · {a.get('date') or ''} · [{a['title']}]({a['url']})"
                      f" · {a.get('status', 'new')}{' · ' + a['triage'] if a.get('triage') else ''}")
    return "\n".join(md) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("work", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--render", action="store_true", help="only re-render ledger/monitor_alerts.md after triage")
    ap.add_argument("--state", type=Path, default=Path.home() / "agent-lab-data" / "cka_monitor" / "seen.json")
    a = ap.parse_args()
    if a.render:
        LEDGER.with_suffix(".md").write_text(render(json.loads(LEDGER.read_text())))
        return 0
    conf = json.loads(CONF.read_text())
    seen = set(json.loads(a.state.read_text())) if a.state.exists() else set()
    found, errors = [], []
    for name, fn, c in (("court calendar", court, conf["court_calendar"]), ("news", news, conf["news"])):
        try:
            found += fn(c)
        except Exception as e:  # one failing source must not stop the others
            errors.append(f"{name}: {type(e).__name__}: {e}")
    today = dt.date.today().isoformat()
    new = [dict(x, seen=today, status="new") for x in found if x["id"] not in seen]
    print(f"monitors: {len(found)} items, {len(new)} new "
          f"({sum(1 for x in new if x['kind'] == 'court_calendar')} court, "
          f"{sum(1 for x in new if x.get('tier2'))} Tier 2 news, "
          f"{sum(1 for x in new if x['kind'] == 'news' and not x['tier2'])} other news)")
    for e in errors:
        print("  source failed:", e)
    if a.dry_run:
        for x in new[:20]:
            print("  ", x.get("outlet", "court"), "|", x.get("title") or x.get("entry"))
        return 0 if new else 3
    if not new:
        return 1 if errors and not found else 3
    a.work.mkdir(parents=True, exist_ok=True)
    (a.work / "monitor_alerts.json").write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    ledger += new
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n")
    LEDGER.with_suffix(".md").write_text(render(ledger))
    a.state.parent.mkdir(parents=True, exist_ok=True)
    a.state.write_text(json.dumps(sorted(seen | {x["id"] for x in new})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
