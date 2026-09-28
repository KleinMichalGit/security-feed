"""Builds index.html: fetch feeds -> select articles -> extract bodies -> render -> save state."""
import argparse
import calendar
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from jinja2 import Environment, FileSystemLoader

import state as state_store
from extract import USER_AGENT, PageFetcher, article_body, text_length
from selection import normalize_url, select
from sources import SOURCES

LIMIT = 10
OUTPUT_FILE = "index.html"
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
FEED_TIMEOUT = 20
# SANS ISC appends the date to titles: "Wireshark 4.6.9 Released, (Sun, Sep 27th)"
_DATE_SUFFIX = re.compile(r",?\s*\((Mon|Tue|Wed|Thu|Fri|Sat|Sun), \w{3} \d{1,2}(st|nd|rd|th)\)$")


def fetch_feed(source):
    """Download and parse one feed. Returns (source, parsed feed or None, error)."""
    try:
        resp = requests.get(source["url"], headers={"User-Agent": USER_AGENT}, timeout=FEED_TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        if not feed.entries and feed.bozo:
            return source, None, str(feed.bozo_exception)
        return source, feed, None
    except Exception as e:
        return source, None, str(e)


def fetch_all():
    with ThreadPoolExecutor(max_workers=12) as ex:
        return list(ex.map(fetch_feed, SOURCES))


def entry_date(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    try:
        return datetime.fromtimestamp(calendar.timegm(parsed), timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None  # nonsense dates such as year 0 are treated as missing


def entry_content(entry):
    contents = entry.get("content") or []
    return max((c.get("value", "") for c in contents), key=len, default="")


def collect_items(results, state, now):
    """Turn feed entries into items. Undated entries get the time they first appeared."""
    bootstrap = not state
    items = []
    for source, feed, error in results:
        if error:
            print(f"  [!] {source['name']}: {error}")
            continue
        exclude = re.compile(source["exclude"], re.I) if source.get("exclude") else None
        for entry in feed.entries:
            link = entry.get("link")
            title = _DATE_SUFFIX.sub("", (entry.get("title") or "").strip())
            if not link or not title or (exclude and exclude.search(title)):
                continue
            date = entry_date(entry)
            if date and date > now + timedelta(days=1):
                continue  # announcements of future events, not news
            if date is None:
                if bootstrap:
                    # First run: no way to tell old undated posts from new ones, so record
                    # them as old and skip them.
                    state_store.first_seen(state, normalize_url(link), now, first=now - timedelta(days=30))
                    continue
                date = state_store.first_seen(state, normalize_url(link), now)
            items.append({
                "title": title,
                "link": link,
                "date": min(date, now),
                "summary": entry.get("summary", ""),
                "content": entry_content(entry),
                "source": source["name"],
                "category": source["category"],
                "weight": source.get("weight", 1.0),
            })
    return items


def check_sources():
    ok = True
    for source, feed, error in fetch_all():
        if error:
            ok = False
            print(f"FAIL  {source['name']:<28} {error[:80]}")
            continue
        dates = [d for d in map(entry_date, feed.entries) if d]
        newest = max(dates).strftime("%Y-%m-%d") if dates else "no dates"
        full = sum(1 for e in feed.entries if text_length(entry_content(e)) >= 1500)
        print(f"ok    {source['name']:<28} {len(feed.entries):3d} entries  newest {newest}  "
              f"full-text {full}/{len(feed.entries)}")
    return ok


def render(articles, now):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    html = env.get_template("index.html.j2").render(articles=articles, generated=now.date().isoformat())
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def generate_site(limit, use_state):
    now = datetime.now(timezone.utc)
    state = state_store.load() if use_state else {}

    print("Step 1: Fetching feeds...")
    items = collect_items(fetch_all(), state, now)
    print(f"  {len(items)} entries from {len({i['source'] for i in items})} sources")

    picked = select(items, state_store.shown_urls(state), limit, now)
    if len(picked) < limit:
        print(f"  [!] Only {len(picked)} unseen articles in the last 14 days")

    print(f"Step 2: Extracting {len(picked)} articles...")
    articles = []
    with PageFetcher() as fetcher:
        for n, choice in enumerate(picked, 1):
            item = choice["item"]
            body, origin = article_body(item, fetcher)
            print(f"[{n}/{len(picked)}] {item['source']}: {item['title'][:60]} "
                  f"(score {choice['score']:.2f}, from {origin})")
            also = sorted({m["source"] for m in choice["members"]} - {item["source"]})
            articles.append({
                **item,
                "date": item["date"].strftime("%Y-%m-%d"),
                "body": body,
                "origin": origin,
                "also": also,
            })

    render(articles, now)
    if use_state:
        state_store.mark_shown(
            state, [normalize_url(m["link"]) for c in picked for m in c["members"]], now)
        state_store.save(state, now)
    print(f"\nWrote {OUTPUT_FILE} with {len(articles)} articles.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-sources", action="store_true", help="fetch every feed and report its status")
    parser.add_argument("--no-state", action="store_true",
                        help="ignore data/state.json and do not mark articles as shown (dry run)")
    parser.add_argument("--limit", type=int, default=LIMIT, help=f"number of articles (default {LIMIT})")
    args = parser.parse_args()
    if args.check_sources:
        raise SystemExit(0 if check_sources() else 1)
    generate_site(args.limit, use_state=not args.no_state)


if __name__ == "__main__":
    main()
