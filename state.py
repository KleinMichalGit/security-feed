"""Persistent record of shown articles and of when undated feed entries first appeared.

Format of data/state.json:
    {normalized_url: {"first_seen": iso, "last_seen": iso, "shown": iso | null}}
Only two kinds of URLs are recorded: articles that were shown on the page, and
feed entries without a publication date (their `first_seen` is used as their date).
"""
import json
import os
from datetime import datetime, timedelta

STATE_FILE = os.path.join("data", "state.json")
KEEP_DAYS = 90


def load(path=STATE_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _latest(rec):
    return max(datetime.fromisoformat(v) for v in rec.values() if v)


def save(state, now, path=STATE_FILE):
    cutoff = now - timedelta(days=KEEP_DAYS)
    kept = {url: rec for url, rec in state.items() if _latest(rec) >= cutoff}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kept, f, indent=1, sort_keys=True)


def shown_urls(state):
    return {url for url, rec in state.items() if rec.get("shown")}


def _record(state, url, now, first=None):
    stamp = now.isoformat()
    rec = state.setdefault(url, {"first_seen": (first or now).isoformat(), "last_seen": stamp, "shown": None})
    rec["last_seen"] = stamp
    return rec


def first_seen(state, url, now, first=None):
    """Return when `url` first appeared in a feed. A new URL is recorded with `first`
    (default `now`); pass an old time to mark entries found on the first run as old."""
    return datetime.fromisoformat(_record(state, url, now, first)["first_seen"])


def mark_shown(state, urls, now):
    for url in urls:
        _record(state, url, now)["shown"] = now.isoformat()
