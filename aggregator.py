import feedparser
import datetime

# --- CONFIGURATION (Edit your sources here) ---
SOURCES = [
    "https://krebsonsecurity.com/feed/",
    "https://www.darkreading.com/rss.xml",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.schneier.com/blog/index.rdf",
    "https://threatpost.com/feed/",
    "https://linuxsecurity.com/features?format=feed&type=rss"
]

LIMIT = 10
OUTPUT_FILE = "index.html"

def generate_site():
    all_entries = []
    
    for url in SOURCES:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            # Store title, link, and published date for sorting
            all_entries.append({
                'title': entry.title,
                'link': entry.link,
                'date': entry.get('published_parsed', entry.get('updated_parsed'))
            })

    # Sort by date (newest first) and take the top 10
    all_entries.sort(key=lambda x: x['date'] if x['date'] else datetime.datetime.min, reverse=True)
    top_10 = all_entries[:LIMIT]

    # Generate the minimal HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Daily Security Brief</title>
        <style>
            body {{ background-color: black; color: white; font-family: monospace; padding: 50px; line-height: 1.6; }}
            h1 {{ border-bottom: 1px solid white; padding-bottom: 10px; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ margin-bottom: 20px; }}
            a {{ color: white; text-decoration: underline; font-weight: bold; }}
            a:hover {{ background-color: white; color: black; }}
            .meta {{ color: #888; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <h1>TOP 10 SECURITY UPDATES - {datetime.date.today()}</h1>
        <ul>
    """

    for item in top_10:
        html_content += f"<li><a href='{item['link']}' target='_blank'>{item['title']}</a></li>"

    html_content += """
        </ul>
        <p class="meta">No more articles. Go back to work.</p>
    </body>
    </html>
    """

    with open(OUTPUT_FILE, "w") as f:
        f.write(html_content)

if __name__ == "__main__":
    generate_site()