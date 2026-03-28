import feedparser
import datetime
import time

SOURCES = [
    "https://thehackernews.com/rss.xml",                # General Security News
    "https://www.darkreading.com/rss.xml",              # Enterprise Security & Trends
    "https://www.schneier.com/blog/index.rdf",          # Cryptography & Security Policy
    "https://krebsonsecurity.com/feed/",                # Cybercrime & Investigative Journalism
    "https://www.bleepingcomputer.com/feed/",           # Latest Threats & Patches
    "https://portswigger.net/daily-swig/rss",           # Web App Security & Bug Bounty
    "https://www.mandiant.com/resources/blog/rss.xml",  # Advanced Threat Intel & Exploits
    "https://linuxsecurity.com/features?format=feed",   # Linux-specific hardening & news
    "https://clintgibler.com/rss.xml",                  # tl;dr sec (Excellent AppSec summaries)
    "https://unit42.paloaltonetworks.com/feed/"         # Deep technical malware/threat analysis
]

LIMIT = 10
OUTPUT_FILE = "index.html"

def generate_site():
    all_entries = []
    for url in SOURCES:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            content = ""
            if 'content' in entry:
                content = entry.content[0].value
            elif 'summary' in entry:
                content = entry.summary
            
            # Convert struct_time to datetime object
            published_time = entry.get('published_parsed', entry.get('updated_parsed'))
            if published_time:
                # Convert time.struct_time to datetime.datetime
                dt = datetime.datetime.fromtimestamp(time.mktime(published_time))
            else:
                dt = datetime.datetime.min

            all_entries.append({
                'title': entry.title,
                'link': entry.link,
                'content': content,
                'date': dt
            })

    all_entries.sort(key=lambda x: x['date'], reverse=True)
    top_10 = all_entries[:LIMIT]

    html_start = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Daily Security Brief</title>
        <style>
            body {{ background-color: black; color: white; font-family: monospace; padding: 50px; line-height: 1.6; max-width: 800px; margin: auto; }}
            h1 {{ border-bottom: 1px solid white; padding-bottom: 10px; }}
            .menu {{ margin-bottom: 40px; border-bottom: 1px double #444; padding-bottom: 20px; }}
            ul {{ list-style-type: decimal-leading-zero; padding: 0; }}
            li {{ margin-bottom: 10px; }}
            button {{ background: none; border: none; color: white; text-decoration: underline; cursor: pointer; font-family: monospace; font-size: 1em; text-align: left; padding: 0; }}
            button:hover {{ background-color: white; color: black; }}
            .article-body {{ display: none; border-top: 1px solid #444; margin-top: 20px; padding-top: 20px; }}
            .article-body.active {{ display: block; }}
            .article-body img {{ max-width: 100%; height: auto; filter: grayscale(100%); }}
            a {{ color: #aaa; }}
            .meta {{ color: #666; font-size: 0.8em; margin-top: 50px; }}
        </style>
    </head>
    <body>
        <h1>SECURITY BRIEF - {datetime.date.today()}</h1>
        <div class="menu">
            <ul>"""

    menu_items = ""
    article_contents = ""

    for i, item in enumerate(top_10):
        # Create unique ID for each article
        article_id = f"article-{i}"
        menu_items += f"<li><button onclick=\"showArticle('{article_id}')\">{item['title']}</button></li>"
        
        article_contents += f"""
        <div id="{article_id}" class="article-body">
            <h2>{item['title']}</h2>
            <a href="{item['link']}" target="_blank">[View Original Source]</a>
            <hr>
            <div>{item['content']}</div>
            <br><button onclick="window.scrollTo(0,0)">↑ Back to Top</button>
        </div>"""

    html_end = """
        </div>
        <div id="reader-area">
            </div>
        <p class="meta">End of list. No distractions.</p>

        <script>
            function showArticle(id) {
                // Hide all articles
                const bodies = document.querySelectorAll('.article-body');
                bodies.forEach(b => b.classList.remove('active'));
                
                // Show the selected one
                const target = document.getElementById(id);
                target.classList.add('active');
                
                // Move view to the content
                target.scrollIntoView({behavior: "smooth"});
            }
        </script>
    </body>
    </html>
    """

    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        f.write(html_start + menu_items + "</ul></div>" + article_contents + html_end)

if __name__ == "__main__":
    generate_site()