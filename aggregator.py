import feedparser
import datetime
import time
import collections
from playwright.sync_api import sync_playwright
import trafilatura

# --- CONFIGURATION ---
SOURCES = [
    "https://thehackernews.com/rss.xml",
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.cisa.gov/cybersecurity-advisories/all.xml",
    "https://www.microsoft.com/en-us/security/blog/feed/",    
    "https://trustedsec.com/feed.rss",
    "https://specterops.io/blog/category/research/feed/",
    "https://cloudblog.withgoogle.com/topics/threat-intelligence/rss/"
]

LIMIT = 10
OUTPUT_FILE = "index.html"

def fetch_full_text_with_browser(url):
    """Opens a headless browser, waits for content, and extracts it."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2) 
            html = page.content()
            browser.close()
            content = trafilatura.extract(html, include_links=True)
            return content
    except Exception as e:
        print(f"  [!] Error fetching {url}: {e}")
        return None

def calculate_score(entry, all_titles):
    """Ranks articles based on Freshness and 'Popularity' Proxy."""
    score = 0
    # 1. Freshness (Newer = Higher Score)
    hours_old = (datetime.datetime.now() - entry['date']).total_seconds() / 3600
    score += max(0, 100 - hours_old) 

    # 2. Popularity Proxy (Is this trending across other feeds?)
    for other_title in all_titles:
        if entry['title'] != other_title:
            common_words = set(entry['title'].lower().split()) & set(other_title.lower().split())
            if len(common_words) > 3: 
                score += 25
    
    # 3. High-Value Keyword Bonus
    keywords = ['zero-day', 'exploit', 'critical', 'vulnerability', 'ransomware', 'breach']
    if any(k in entry['title'].lower() for k in keywords):
        score += 20

    return score

def generate_site():
    print("Step 1: Fetching and Balancing Sources...")
    source_buckets = collections.defaultdict(list)
    all_titles = []

    for url in SOURCES:
        try:
            feed = feedparser.parse(url)
            # Get clean source name from feed or URL
            source_name = feed.feed.get('title', url.split('/')[2])
            for entry in feed.entries:
                p_time = entry.get('published_parsed', entry.get('updated_parsed'))
                dt = datetime.datetime.fromtimestamp(time.mktime(p_time)) if p_time else datetime.datetime.min
                
                item = {
                    'title': entry.title, 
                    'link': entry.link, 
                    'date': dt, 
                    'summary': entry.get('summary', ''),
                    'source': source_name
                }
                source_buckets[source_name].append(item)
                all_titles.append(entry.title)
        except Exception as e:
            print(f"  [!] Failed to parse {url}: {e}")

    # Step 2: Smart Selection (Round-Robin)
    selected_articles = []
    for name in source_buckets:
        source_buckets[name].sort(key=lambda x: calculate_score(x, all_titles), reverse=True)

    while len(selected_articles) < LIMIT and any(source_buckets.values()):
        for name in list(source_buckets.keys()):
            if source_buckets[name]:
                selected_articles.append(source_buckets[name].pop(0))
            if len(selected_articles) == LIMIT:
                break

    # Final sort by date for display
    selected_articles.sort(key=lambda x: x['date'], reverse=True)

    article_html = ""
    menu_html = ""

    print(f"Step 2: Deep-Scraping {len(selected_articles)} Balanced Articles...")

    for i, item in enumerate(selected_articles):
        print(f"[{i+1}/10] From {item['source']}: {item['title'][:40]}...")
        full_text = fetch_full_text_with_browser(item['link'])
        
        if full_text and len(full_text) > 400:
            final_body = full_text
        else:
            final_body = item['summary'] + "\n\n[Full content could not be extracted. Visit source for details.]"
        
        art_id = f"art-{i}"
        menu_html += f"<li><button onclick=\"show('{art_id}')\">{item['title']}</button></li>"
        article_html += f"""
        <div id="{art_id}" class="article-body">
            <h2 class="article-title">{item['title']}</h2>
            <p class="source-link">Source: {item['source']} | <a href="{item['link']}" target="_blank">Original Link</a></p>
            <div class="content-text">{final_body}</div>
            <br>
            <button class="back-btn" onclick="window.scrollTo(0,0)">[ Back to Menu ]</button>
            <hr class="separator">
        </div>"""

    # Final HTML Construction
    full_page = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Security Briefing</title>
        <style>
            body {{ 
                background-color: #012456; 
                color: #F2F2F2; 
                font-family: 'Consolas', 'Lucida Console', monospace; 
                padding: 20px; 
                line-height: 1.6; 
                max-width: 1000px; 
                margin: auto; 
            }}
            h1 {{ color: #FFFFFF; font-size: 1.4em; border-bottom: 2px solid #F2F2F2; padding-bottom: 10px; margin-bottom: 30px; }}
            .menu {{ margin-bottom: 40px; }}
            ul {{ list-style-type: decimal-leading-zero; padding-left: 25px; }}
            li {{ margin-bottom: 12px; color: #EBCB8B; }}
            button {{ 
                background: none; border: none; color: #F2F2F2; 
                text-align: left; cursor: pointer; font-family: inherit; 
                font-size: 1.05em; padding: 0;
            }}
            button:hover {{ color: #FFFF00; text-decoration: underline; }}
            .article-body {{ display: none; margin-top: 20px; }}
            .article-title {{ color: #FFFFFF; font-size: 1.3em; margin-bottom: 5px; }}
            .source-link {{ color: #A3BE8C; font-size: 0.9em; }}
            .source-link a {{ color: #A3BE8C; text-decoration: none; }}
            .source-link a:hover {{ text-decoration: underline; }}
            .content-text {{ 
                white-space: pre-wrap; 
                padding: 15px 0;
                font-size: 1em;
                border-top: 1px solid #4C566A;
                margin-top: 15px;
            }}
            .back-btn {{ color: #FFFF00; border: 1px solid #FFFF00; padding: 6px 12px; margin-top: 15px; transition: 0.2s; }}
            .back-btn:hover {{ background: #FFFF00; color: #012456; }}
            .separator {{ border: 0; border-top: 1px dashed #4C566A; margin: 50px 0; }}
            .active {{ display: block; }}
            footer {{ 
                text-align: center; 
                margin-top: 60px; 
                padding: 30px; 
                border-top: 1px solid #4C566A; 
                font-size: 0.85em; 
                color: #A3BE8C;
            }}
            footer a {{ color: #A3BE8C; text-decoration: underline; }}
            .disclaimer {{ opacity: 0.8; font-size: 0.9em; max-width: 700px; margin: 15px auto; line-height: 1.4; }}
            @media (max-width: 600px) {{
                body {{ padding: 15px; font-size: 15px; }}
                h1 {{ font-size: 1.2em; }}
                ul {{ padding-left: 20px; }}
            }}
        </style>
    </head>
    <body>
        <h1>Security Briefing // {datetime.date.today()}</h1>
        <div class="menu">
            <ul>{menu_html}</ul>
        </div>
        {article_html}
        <script>
            function show(id) {{
                document.querySelectorAll('.article-body').forEach(el => el.classList.remove('active'));
                const target = document.getElementById(id);
                target.classList.add('active');
                target.scrollIntoView({{behavior: 'smooth'}});
            }}
        </script>
        <footer>
            <p>News aggregator designed and maintained by <a href="https://github.com/KleinMichalGit/security-feed" target="_blank">Michal Klein</a></p>
            <div class="disclaimer">
                <p>This is an <strong>open-source educational project</strong> intended for research and personal productivity. The aggregator is available on <a href="https://github.com/KleinMichalGit/security-feed" target="_blank">GitHub</a>.</p>
                <p><em>Notice: The articles above are automated scrapes from third-party RSS feeds. Full credit belongs to the original authors and publications linked in each source. This site does not claim ownership of the reported content.</em></p>
            </div>
        </footer>
    </body>
    </html>
    """
    
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        f.write(full_page)
    print(f"\nSuccess! index.html generated with balanced sources.")

if __name__ == "__main__":
    generate_site()