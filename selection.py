"""Article selection: story clustering, scoring and per-source balancing.

Everything here is pure (no network, no file I/O) and takes `now` explicitly,
so it can be unit-tested.
"""
import math
import re
from collections import Counter, defaultdict
from datetime import timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_AGE_DAYS = 14
# Score halves every N hours. Research write-ups stay relevant longer than news.
HALF_LIFE_HOURS = {'news': 36, 'threat-intel': 72, 'red-team': 96}
DEFAULT_HALF_LIFE_HOURS = 36
PER_SOURCE_CAP = 3
SIMILARITY_THRESHOLD = 0.5          # share of the shorter title's word weight
SIMILARITY_THRESHOLD_LONGER = 0.3   # share of the longer title's word weight
MIN_SHARED_WORDS = 2
TOPIC_MAX_SHARE = 0.015             # a word in at most 1.5% of titles counts as a topic word
RECENT_TOPIC_DAYS = 3               # stories shown this recently still penalize their topic

KEYWORDS = [
    'zero-day', '0-day', 'exploit', 'critical', 'vulnerability', 'ransomware', 'breach',
    'red team', 'c2', 'edr', 'bypass', 'initial access', 'lateral movement', 'poc', 'rce',
]
_KEYWORD_RE = re.compile(r'\b(' + '|'.join(re.escape(k) for k in KEYWORDS) + r')\b', re.I)

STOPWORDS = set("""
a an and are as at be been by for from has have how in into is it its new of on or over
the their this to under up via was what when where which who why will with after about
than that more most not now out says say can could may might all any our your you we let
january february march april may june july august september october november december
monday tuesday wednesday thursday friday saturday sunday
flaw vulnerability vuln bug issue exploit exploited exploitation actively active attack
attacker hacker threat actor wild security cyber cybersecurity patch patched fix fixed
warn warning critical update released report found use user customer
""".split())
_NUMBER_WORDS = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5'}

_CVE_RE = re.compile(r'cve-\d{4}-\d{4,}', re.I)
_TOKEN_RE = re.compile(r'[a-z0-9][a-z0-9\-\.]*[a-z0-9]|[a-z0-9]')
_TRACKING_PARAMS = ('utm_', 'fbclid', 'gclid', 'mc_cid', 'mc_eid')


def normalize_url(url):
    """Canonical form of an article URL, used as the key in the state file."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith(_TRACKING_PARAMS)]
    path = parts.path.rstrip('/') or '/'
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ''))


def _stem(word):
    word = _NUMBER_WORDS.get(word, word)
    if word.endswith(('xes', 'shes', 'ches', 'sses')):
        word = word[:-2]
    elif len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
        word = word[:-1]
    return word


def title_tokens(title):
    """Content words of a title, lightly stemmed. CVE IDs are kept as single tokens;
    dates, bare numbers and generic security vocabulary are dropped."""
    text = title.lower().replace('’', "'")
    cves = set(_CVE_RE.findall(text))
    text = _CVE_RE.sub(' ', text)
    words = set()
    for w in _TOKEN_RE.findall(text):
        w = _stem(w.removesuffix("'s"))
        if len(w) > 1 and w not in STOPWORDS and _stem(w) not in STOPWORDS and not w.isdigit():
            words.add(w)
    return words | cves


def word_weights(token_sets):
    """Inverse document frequency of each word over a collection of titles."""
    counts = Counter(w for toks in token_sets for w in toks)
    n = max(len(token_sets), 1)
    return {w: math.log((n + 1) / c) for w, c in counts.items()}


def same_story(tokens_a, tokens_b, idf=None):
    """Titles are one story if they share a CVE ID, or if the rare words they share make up
    at least SIMILARITY_THRESHOLD of the shorter title's total word weight and
    SIMILARITY_THRESHOLD_LONGER of the longer one's."""
    if {t for t in tokens_a if t.startswith('cve-')} & tokens_b:
        return True
    shared = tokens_a & tokens_b
    if len(shared) < MIN_SHARED_WORDS:
        return False
    weight = lambda toks: sum((idf or {}).get(w, 1.0) for w in toks)
    smaller, larger = sorted((weight(tokens_a), weight(tokens_b)))
    return (smaller > 0
            and weight(shared) / smaller >= SIMILARITY_THRESHOLD
            and weight(shared) / larger >= SIMILARITY_THRESHOLD_LONGER)


def cluster(items, idf=None):
    """Group items that report the same story. Returns a list of clusters (lists of items)."""
    token_map = {id(i): title_tokens(i['title']) for i in items}
    if idf is None:
        idf = word_weights(list(token_map.values()))
    clusters = []  # list of (tokens_list, items)
    for item in sorted(items, key=lambda x: x['date']):
        tokens = token_map[id(item)]
        for toks, members in clusters:
            if any(same_story(tokens, t, idf) for t in toks):
                toks.append(tokens)
                members.append(item)
                break
        else:
            clusters.append(([tokens], [item]))
    return [members for _, members in clusters]


def score(item, coverage, now):
    age_hours = max(0.0, (now - item['date']).total_seconds() / 3600)
    value = item.get('weight', 1.0)
    value *= 0.5 ** (age_hours / HALF_LIFE_HOURS.get(item.get('category'), DEFAULT_HALF_LIFE_HOURS))
    value *= 1 + 0.3 * min(coverage - 1, 3)
    if _KEYWORD_RE.search(item['title']):
        value *= 1.2
    return value


def _representative(members):
    # Highest-weighted source first, then the earliest report.
    return min(members, key=lambda x: (-x.get('weight', 1.0), x['date']))


def _pick(scored, limit, recent_topics=()):
    """Greedy pick. A candidate's score is halved for every article already picked from
    the same source, and for every story (picked now, or shown in the last few days)
    that shares one of its topic words.
    At most PER_SOURCE_CAP per source; the cap is raised only if the limit can't be met."""
    picked = []
    remaining = list(scored)
    cap = PER_SOURCE_CAP
    counts = defaultdict(int)

    def adjusted(c):
        overlaps = sum(1 for p in picked if c['topics'] & p['topics'])
        overlaps += sum(1 for t in recent_topics if c['topics'] & t)
        return c['score'] * 0.5 ** (counts[c['item']['source']] + overlaps)

    while len(picked) < limit and remaining:
        eligible = [c for c in remaining if counts[c['item']['source']] < cap]
        if not eligible:
            cap += 1
            continue
        best = max(eligible, key=adjusted)
        remaining.remove(best)
        picked.append(best)
        counts[best['item']['source']] += 1
    return picked


def select(items, shown_urls, limit, now):
    """Choose up to `limit` stories that were not shown before.

    items: dicts with title, link, date (aware UTC datetime), source, weight.
    shown_urls: set of normalized URLs already displayed on earlier days.
    Returns a list of dicts: {item, members, score}, newest first.
    """
    idf = word_weights([title_tokens(i['title']) for i in items])
    # Topic words: names like "citrix" or "bitget" that appear in few of the day's titles.
    rare_idf = math.log((len(items) + 1) / max(1.0, TOPIC_MAX_SHARE * len(items)))

    def topics(members):
        return {w for m in members for w in title_tokens(m['title'])
                if idf.get(w, 0) >= rare_idf and len(w) > 2}

    unseen = [i for i in items if normalize_url(i['link']) not in shown_urls]
    # Drop whole stories if any outlet's version of them was already shown.
    blocked = set()
    recent_topics = []
    for members in cluster(items, idf):
        shown = [m for m in members if normalize_url(m['link']) in shown_urls]
        if shown:
            blocked.update(id(m) for m in members)
            if max(m['date'] for m in shown) >= now - timedelta(days=RECENT_TOPIC_DAYS):
                recent_topics.append(topics(members))
    unseen = [i for i in unseen if id(i) not in blocked]

    pool = [i for i in unseen if i['date'] >= now - timedelta(days=MAX_AGE_DAYS)]
    candidates = []
    for members in cluster(pool, idf):
        rep = _representative(members)
        coverage = len({m['source'] for m in members})
        candidates.append({'item': rep, 'members': members, 'topics': topics(members),
                           'score': score(rep, coverage, now)})

    picked = _pick(candidates, limit, recent_topics)
    picked.sort(key=lambda c: c['item']['date'], reverse=True)
    return picked
