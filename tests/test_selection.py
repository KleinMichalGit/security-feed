from datetime import datetime, timedelta, timezone

from selection import cluster, normalize_url, same_story, select, title_tokens

NOW = datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc)


def item(title, source, hours_old=1, link=None, weight=1.0):
    return {
        "title": title,
        "link": link or f"https://{source.lower().replace(' ', '')}.example/{abs(hash(title))}",
        "date": NOW - timedelta(hours=hours_old),
        "source": source,
        "weight": weight,
    }


def test_normalize_url_strips_tracking_and_trailing_slash():
    a = normalize_url("https://Example.com/post/1/?utm_source=rss&utm_medium=feed#comments")
    b = normalize_url("https://example.com/post/1")
    assert a == b
    assert normalize_url("https://example.com/p?id=5&fbclid=x") == "https://example.com/p?id=5"


def test_title_tokens_drop_stopwords_keep_cves():
    toks = title_tokens("CISA adds CVE-2026-12345 to the KEV catalog")
    assert "cve-2026-12345" in toks
    assert "the" not in toks and "to" not in toks


def test_shared_cve_is_same_story():
    a = title_tokens("CISA warns of SharePoint flaw CVE-2026-1111 exploited in attacks")
    b = title_tokens("SharePoint RCE (CVE-2026-1111) actively exploited in the wild")
    assert same_story(a, b)


def test_unrelated_titles_are_different_stories():
    a = title_tokens("Roundcube pre-auth SQL injection flaw actively exploited")
    b = title_tokens("U.S. soldier gets 70 months in prison for extortion")
    assert not same_story(a, b)


def test_cluster_merges_near_duplicate_titles():
    items = [
        item("Microsoft patches nearly 1,000 security holes", "Krebs"),
        item("Microsoft patches nearly 1,000 security holes in September", "BleepingComputer"),
        item("New Outlook phishing kit spotted", "The Record"),
    ]
    sizes = sorted(len(c) for c in cluster(items))
    assert sizes == [1, 2]


def test_cluster_real_headlines():
    titles = {
        "citrix": [
            ("Warning: Two Unpatched Citrix NetScaler RCE Zero-Days Under Active Exploitation", "The Hacker News"),
            ("Citrix confirms two NetScaler RCE zero-days exploited in attacks", "BleepingComputer"),
            ("Citrix Confirms 2 NetScaler Zero-Days After Admins Pulled the Plug", "SecurityWeek"),
        ],
        "bitget": [
            ("North Korea Suspected in $351 Million Bitget Crypto Heist", "SecurityWeek"),
            ("Crypto CEO accuses North Korea of stealing $387 million from Bitget platform", "The Record"),
            ("Bitget blames North Korea for $387.5M crypto wallet raid", "The Register"),
        ],
        "anthropic-market": [("Anthropic turns Claude into an AI marketplace with 2,000+ plugins and connectors",
                              "BleepingComputer")],
        "anthropic-report": [("On Anthropic's AI Misuse Report", "Schneier on Security")],
        "sharepoint": [("SharePoint RCE and MikroTik RouterOS Flaws Actively Exploited in the Wild", "The Hacker News")],
        "roundcube": [("Roundcube Pre-Auth SQL Injection Flaw Actively Exploited in the Wild", "The Hacker News")],
        "ms-news": [("What's new in Microsoft Security: September 2026", "Microsoft Security Blog")],
        "wireshark": [("Wireshark 4.6.9 Released, (Sun, Sep 27th)", "SANS ISC")],
    }
    items = []
    for story, entries in titles.items():
        for title, source in entries:
            items.append(dict(item(title, source), story=story))
    # Word weights come from the whole day's feed in production (~1000 titles), so
    # add unrelated filler to keep the story words rare, as they are in practice.
    filler = [dict(item(f"Filler{i} headline{i} text{i}", "Filler"), story=None) for i in range(300)]
    groups = sorted(sorted(m["story"] for m in c) for c in cluster(items + filler) if c[0]["story"])
    assert groups == sorted([[s] * len(e) for s, e in titles.items()])


def test_shown_urls_are_never_selected():
    items = [item(f"Story number {i} about topic{i}", "News", hours_old=i) for i in range(5)]
    shown = {normalize_url(items[0]["link"])}
    picked = select(items, shown, limit=5, now=NOW)
    links = {c["item"]["link"] for c in picked}
    assert items[0]["link"] not in links
    assert len(picked) == 4


def test_story_shown_by_another_outlet_is_blocked():
    a = item("Oracle PeopleSoft CVE-2026-2222 exploited by ShinyHunters", "The Hacker News")
    b = item("ShinyHunters target PeopleSoft via CVE-2026-2222", "BleepingComputer")
    picked = select([a, b], {normalize_url(a["link"])}, limit=5, now=NOW)
    assert picked == []


def test_high_volume_source_is_capped():
    busy = [item(f"Busy headline {i} word{i} other{i}", "Busy", hours_old=i * 0.1) for i in range(20)]
    quiet = [item(f"Quiet research post {i} term{i} more{i}", f"Blog{i}", hours_old=30) for i in range(8)]
    picked = select(busy + quiet, set(), limit=10, now=NOW)
    assert len(picked) == 10
    assert sum(c["item"]["source"] == "Busy" for c in picked) <= 3


def test_follow_up_on_same_topic_is_deprioritized():
    citrix = [item("Citrix NetScaler zero-days under attack", "A", hours_old=1),
              item("CISA orders agencies to patch Citrix by Wednesday", "B", hours_old=1)]
    others = [item(t, f"S{i}", hours_old=6) for i, t in enumerate(
        ["Airline discloses data breach", "Fortinet VPN flaw under attack", "New Android spyware found"])]
    filler = [item(f"Filler{i} headline{i} text{i}", f"F{i}", hours_old=24 * 13) for i in range(300)]
    picked = select(citrix + others + filler, set(), limit=3, now=NOW)
    titles = [c["item"]["title"] for c in picked]
    assert sum("Citrix" in t for t in titles) == 1


def test_topic_shown_yesterday_is_deprioritized():
    shown_story = item("Citrix NetScaler zero-days under attack", "A", hours_old=20)
    follow_up = item("Certainties in life: death, taxes and Citrix vulns", "B", hours_old=2)
    others = [item(t, f"S{i}", hours_old=10) for i, t in enumerate(
        ["Airline discloses data breach", "Fortinet VPN flaw under attack"])]
    filler = [item(f"Filler{i} headline{i} text{i}", f"F{i}", hours_old=24 * 13) for i in range(300)]
    picked = select([shown_story, follow_up] + others + filler,
                    {normalize_url(shown_story["link"])}, limit=2, now=NOW)
    assert "Citrix" not in " ".join(c["item"]["title"] for c in picked)


def test_cap_relaxes_to_fill_limit():
    busy = [item(f"Busy headline {i} word{i} other{i}", "Busy") for i in range(12)]
    picked = select(busy, set(), limit=10, now=NOW)
    assert len(picked) == 10


def test_nothing_older_than_14_days():
    items = [item(f"Old post {i} alpha{i} beta{i}", f"S{i}", hours_old=24 * 5 + i) for i in range(4)]
    items += [item(f"Ancient post {i} gamma{i} delta{i}", f"T{i}", hours_old=24 * 20) for i in range(4)]
    picked = select(items, set(), limit=10, now=NOW)
    assert len(picked) == 4
    assert all("Old post" in c["item"]["title"] for c in picked)


def test_old_post_from_rare_source_not_repeated():
    # The round-robin version picked a rare source's latest post every day.
    rare = item("Deep dive into EDR bypass techniques", "RareBlog", hours_old=24 * 6, weight=1.3)
    day1 = [item(t, f"News{i}", hours_old=2) for i, t in enumerate(
        ["Ransomware gang hits hospital chain", "Chrome zero-day patched", "Police seize botnet servers"])]
    first = select([rare] + day1, set(), limit=10, now=NOW)
    assert rare["link"] in {c["item"]["link"] for c in first}

    shown = {normalize_url(c["item"]["link"]) for c in first}
    later = NOW + timedelta(days=1)
    day2 = [dict(item(t, f"News{i}"), date=later) for i, t in enumerate(
        ["Airline discloses data breach", "Fortinet VPN flaw under attack", "New Android spyware found"])]
    second = select([rare] + day1 + day2, shown, limit=10, now=later)
    assert {c["item"]["link"] for c in second} == {i["link"] for i in day2}


def test_results_sorted_newest_first():
    items = [item(f"Post {i} unique{i} words{i}", f"S{i}", hours_old=i * 3) for i in range(5)]
    picked = select(items, set(), limit=5, now=NOW)
    dates = [c["item"]["date"] for c in picked]
    assert dates == sorted(dates, reverse=True)


def test_research_post_outlives_routine_news():
    research = dict(item("Abusing Kerberos delegation for lateral movement", "SpecterOps", hours_old=96,
                         weight=1.3), category="red-team")
    news = [dict(item(f"Routine story {i} alpha{i} beta{i}", f"News{i}", hours_old=60), category="news")
            for i in range(10)]
    picked = select([research] + news, set(), limit=5, now=NOW)
    assert research["link"] in {c["item"]["link"] for c in picked}
