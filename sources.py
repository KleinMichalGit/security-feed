"""Feeds the aggregator reads.

category: news | threat-intel | red-team (shown as a tag on the page)
weight:   multiplier on the article score; defaults to 1.0. Low-volume research
          sources get a little more so a single post can compete with news sites.
exclude:  optional regex; entries whose title matches it are skipped.
Run `python aggregator.py --check-sources` after editing this list.
"""

SOURCES = [
    # News
    {"name": "The Hacker News", "url": "https://thehackernews.com/rss.xml", "category": "news"},
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/", "category": "news"},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "category": "news", "weight": 1.2},
    {"name": "The Record", "url": "https://therecord.media/feed", "category": "news"},
    {"name": "SecurityWeek", "url": "https://www.securityweek.com/feed/", "category": "news"},
    {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml", "category": "news"},
    {"name": "The Register", "url": "https://www.theregister.com/security/headlines.atom", "category": "news"},
    {"name": "Schneier on Security", "url": "https://www.schneier.com/feed/atom/", "category": "news",
     "exclude": r"Squid Blogging"},

    # Threat intelligence
    {"name": "Microsoft Security Blog", "url": "https://www.microsoft.com/en-us/security/blog/feed/", "category": "threat-intel"},
    {"name": "Google Threat Intelligence", "url": "https://cloudblog.withgoogle.com/topics/threat-intelligence/rss/", "category": "threat-intel", "weight": 1.2},
    {"name": "Unit 42", "url": "https://unit42.paloaltonetworks.com/feed/", "category": "threat-intel", "weight": 1.2},
    {"name": "Cisco Talos", "url": "https://blog.talosintelligence.com/rss/", "category": "threat-intel", "weight": 1.2},
    {"name": "Securelist", "url": "https://securelist.com/feed/", "category": "threat-intel", "weight": 1.2},
    {"name": "The DFIR Report", "url": "https://thedfirreport.com/feed/", "category": "threat-intel", "weight": 1.3},
    {"name": "ESET WeLiveSecurity", "url": "https://www.welivesecurity.com/en/rss/feed/", "category": "threat-intel"},
    {"name": "Elastic Security Labs", "url": "https://www.elastic.co/security-labs/rss/feed.xml", "category": "threat-intel", "weight": 1.2},
    {"name": "SANS ISC", "url": "https://isc.sans.edu/rssfeed_full.xml", "category": "threat-intel",
     "exclude": r"^ISC Stormcast"},

    # Red team / offensive research
    {"name": "SpecterOps", "url": "https://specterops.io/blog/category/research/feed/", "category": "red-team", "weight": 1.3},
    {"name": "TrustedSec", "url": "https://trustedsec.com/feed.rss", "category": "red-team", "weight": 1.3},
    {"name": "Outflank", "url": "https://www.outflank.nl/blog/feed/", "category": "red-team", "weight": 1.3},
    {"name": "MDSec", "url": "https://www.mdsec.co.uk/feed/", "category": "red-team", "weight": 1.3},
    {"name": "XPN InfoSec", "url": "https://blog.xpnsec.com/rss.xml", "category": "red-team", "weight": 1.3},
    {"name": "watchTowr Labs", "url": "https://labs.watchtowr.com/rss/", "category": "red-team", "weight": 1.3},
    {"name": "Horizon3.ai", "url": "https://www.horizon3.ai/feed/", "category": "red-team", "weight": 1.2},
    {"name": "PortSwigger Research", "url": "https://portswigger.net/research/rss", "category": "red-team", "weight": 1.3},
    {"name": "Project Zero", "url": "https://googleprojectzero.blogspot.com/feeds/posts/default", "category": "red-team", "weight": 1.3},
    {"name": "ZDI", "url": "https://www.thezdi.com/blog?format=rss", "category": "red-team", "weight": 1.2},
    {"name": "Pen Test Partners", "url": "https://www.pentestpartners.com/feed/", "category": "red-team", "weight": 1.2},
]
