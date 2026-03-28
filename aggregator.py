import feedparser
import datetime
import time
from playwright.sync_api import sync_playwright
import trafilatura

# --- CONFIGURATION ---
SOURCES = [
    "https://thehackernews.com/rss.xml",
    "https://www.darkreading.com/rss.xml",
    "https://www.schneier.com/blog/index.rdf",
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://portswigger.net/daily-swig/rss",
    "https://www.mandiant.com/resources/blog/rss.xml",
    "https://linuxsecurity.com/features?format=feed",
    "https://clintgibler.com/rss.xml",
    "https://unit42.paloaltonetworks.com/feed/"
]
LIMIT = 10
OUTPUT_FILE = "index.html"

def fetch_full_text_with_browser(url):
    """Opens a headless browser, waits for content, and extracts it."""
    try:
        with sync_playwright() as p:
            # Launching browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Navigate and wait for content to actually load
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Some sites need a extra second for JS to render the article body
            time.sleep(2) 
            
            html = page.content()
            browser.close()
            
            # Extract clean text from the rendered HTML
            content = trafilatura.extract(html, include_links=True)
            return content
    except Exception as e:
        print(f"  [!] Error fetching {url}: {e}")
        return None

def generate_site():
    print("Step 1: Fetching RSS Feeds...")
    all_entries = []
    for url in SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                p_time = entry.get('published_parsed', entry.get('updated_parsed'))
                dt = datetime.datetime.fromtimestamp(time.mktime(p_time)) if p_time else datetime.datetime.min
                all_entries.append({
                    'title': entry.title, 
                    'link': entry.link, 
                    'date': dt, 
                    'summary': entry.get('summary', '')
                })
        except Exception as e:
            print(f"  [!] Failed to parse feed {url}: {e}")

    # Sort and slice to top 10
    all_entries.sort(key=lambda x: x['date'], reverse=True)
    top_10 = all_entries[:LIMIT]

    article_html = ""
    menu_html = ""

    print(f"Step 2: Deep-Scraping {len(top_10)} articles (this will take a minute)...")

    for i, item in enumerate(top_10):
        print(f"[{i+1}/10] Extracting: {item['title'][:50]}...")
        
        # Corrected function call
        full_text = fetch_full_text_with_browser(item['link'])
        
        # Fallback logic: if deep scrape fails or is too short, use RSS summary
        if full_text and len(full_text) > 400:
            final_body = full_text
        else:
            final_body = item['summary'] + "\n\n[Full content could not be extracted. Visit source for details.]"
        
        art_id = f"art-{i}"
        menu_html += f"<li><button onclick=\"show('{art_id}')\">{item['title']}</button></li>"
        article_html += f"""
        <div id="{art_id}" class="article-body">
            <h2 style="color:#00FF00">>>> {item['title']}</h2>
            <p style="color:#666">Source: <a href="{item['link']}" target="_blank" style="color:#666;">{item['link']}</a></p>
            <div class="content-text">{final_body}</div>
            <button onclick="window.scrollTo(0,0)" style="margin-top:20px; color:#888; border:1px solid #444; padding:5px;">[↑ Back to Menu]</button>
            <hr style="border:0; border-top:1px dashed #333; margin:40px 0;">
        </div>"""

    # Final HTML Construction
    full_page = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Cyber-Security Daily</title>
        <style>
            body {{ background:#000; color:#eee; font-family: 'Courier New', monospace; padding: 40px; line-height: 1.6; max-width: 900px; margin: auto; }}
            h1 {{ border-bottom: 2px solid #00FF00; color: #00FF00; padding-bottom: 10px; }}
            .menu {{ margin-bottom: 50px; background: #111; padding: 20px; border: 1px solid #333; }}
            ul {{ list-style: decimal-leading-zero; padding-left: 25px; }}
            li {{ margin-bottom: 15px; border-bottom: 1px solid #222; padding-bottom: 5px; color:#00FF00; }}
            button {{ background:none; border:none; color:#eee; text-align:left; cursor:pointer; font-family:inherit; font-size: 1.1em; }}
            button:hover {{ color: #00FF00; text-decoration: underline; }}
            .article-body {{ display:none; padding: 20px; border: 1px solid #333; margin-top: 20px; }}
            .content-text {{ white-space: pre-wrap; font-size: 1.1em; }}
            .active {{ display:block; }}
        </style>
    </head>
    <body>
        <h1>CYBER-SECURITY DAILY DEBRIEF // {datetime.date.today()}</h1>
        <div class="menu">
            <p style="color:#888; font-size:0.8em;">[TOP {LIMIT} ARTICLES SELECTED]</p>
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
        <p style="text-align:center; color:#444; margin-top:100px;">--- End of Data ---</p>
    </body>
    </html>
    """
    
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        f.write(full_page)
    print(f"\nSuccess! Open {OUTPUT_FILE} to read your news.")

if __name__ == "__main__":
    generate_site()