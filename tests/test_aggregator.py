import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from aggregator import collect_items

NOW = datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc)
SOURCE = {"name": "Blog", "url": "https://blog.example/feed", "category": "red-team", "exclude": r"^Podcast"}


def feed(*entries):
    return [(SOURCE, SimpleNamespace(entries=list(entries)), None)]


def dated(title, when):
    return {"title": title, "link": f"https://blog.example/{title}", "published_parsed": time.gmtime(when.timestamp())}


def test_undated_entries_from_first_run_are_old_on_later_runs():
    about = {"title": "About Me", "link": "https://blog.example/about"}
    state = {}
    assert collect_items(feed(about), state, NOW) == []

    later = NOW + timedelta(days=1)
    items = collect_items(feed(about), state, later)
    assert items[0]["date"] < later - timedelta(days=14)


def test_undated_entry_appearing_later_uses_first_seen():
    state = {"https://blog.example/old": {"first_seen": NOW.isoformat(), "last_seen": NOW.isoformat(), "shown": None}}
    new = {"title": "Fresh post", "link": "https://blog.example/new"}
    items = collect_items(feed(new), state, NOW)
    assert items[0]["date"] == NOW


def test_future_dated_entries_are_dropped():
    items = collect_items(feed(dated("Virtual event 2027", NOW + timedelta(days=60)),
                               dated("Real post", NOW - timedelta(hours=3))), {"x": {}}, NOW)
    assert [i["title"] for i in items] == ["Real post"]


def test_date_suffix_stripped_from_title():
    items = collect_items(feed(dated("Wireshark 4.6.9 Released, (Sun, Sep 27th)", NOW)), {"x": {}}, NOW)
    assert items[0]["title"] == "Wireshark 4.6.9 Released"


def test_exclude_pattern():
    items = collect_items(feed(dated("Podcast episode 12", NOW), dated("EDR bypass notes", NOW)), {"x": {}}, NOW)
    assert [i["title"] for i in items] == ["EDR bypass notes"]
