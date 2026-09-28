"""Article body extraction and HTML sanitizing.

Order for each article:
  1. full HTML shipped in the feed (content:encoded), if it is long enough;
  2. the article page fetched over plain HTTP;
  3. the article page loaded in headless Chromium (only started if needed);
  4. the feed summary.
A page is parsed with Readability (keeps the original markup: images, tables, code),
falling back to trafilatura. Whatever is kept is reduced to a safe subset of HTML.
"""
import re

import lxml.html
import nh3
import requests
import trafilatura
from readability import Document

from selection import title_tokens

MIN_FEED_TEXT = 1500   # feed content longer than this (as text) is used without scraping
MIN_PAGE_TEXT = 400    # extracted page text shorter than this is treated as a failure
MIN_TITLE_MATCH = 0.5  # share of title words that must appear in the extracted text

ALLOWED_TAGS = {
    "p", "h2", "h3", "h4", "ul", "ol", "li", "a", "strong", "b", "em", "i", "code", "pre",
    "blockquote", "table", "thead", "tbody", "tr", "th", "td", "img", "figure", "figcaption",
    "br", "hr",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
}
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
           "Accept-Language": "en-US,en;q=0.9"}


def text_of(html):
    if not html:
        return ""
    try:
        return lxml.html.fromstring(html).text_content().strip()
    except (lxml.etree.ParserError, ValueError):
        return ""


def text_length(html):
    return len(text_of(html))


def looks_like_article(html, title):
    """True if `html` has enough text and mentions most of the title's words.
    Rejects cookie-consent pages, bot challenges and 'page not found' templates."""
    text = text_of(html)
    if len(text) < MIN_PAGE_TEXT:
        return False
    words = title_tokens(title)
    if not words:
        return True
    lower = text.lower()
    return sum(w in lower for w in words) / len(words) >= MIN_TITLE_MATCH


def _fix_images(root):
    for img in list(root.iter("img")):
        src = img.get("src") or ""
        if not src or src.startswith("data:"):
            lazy = img.get("data-src") or img.get("data-lazy-src") or img.get("data-original")
            if not lazy and img.get("srcset"):
                lazy = img.get("srcset").split(",")[0].split()[0]
            if lazy:
                img.set("src", lazy)
            else:
                img.drop_tree()


def _fix_code(root):
    # trafilatura turns inline <code> into <pre>; turn short single-line blocks back.
    for pre in list(root.iter("pre")):
        if pre.getparent() is not None and pre.getparent().tag == "pre":
            pre.drop_tag()
            continue
        text = pre.text_content()
        if "\n" not in text.strip() and len(text) < 80 and len(pre) == 0:
            pre.tag = "code"
    # Some sites use a bare multi-line <code> styled with white-space: pre.
    for code in list(root.iter("code")):
        if "\n" in code.text_content().strip() and not any(a.tag == "pre" for a in code.iterancestors()):
            pre = lxml.html.Element("pre")
            code.addprevious(pre)
            pre.tail, code.tail = code.tail, None
            pre.append(code)


def _parse(html):
    if re.search(r"<(html|body)[\s>]", html, re.I):
        body = lxml.html.document_fromstring(html).find("body")
        root = lxml.html.Element("div")
        if body is not None:
            root.text = body.text
            root.extend(list(body))
        return root
    return lxml.html.fragment_fromstring(html, create_parent="div")


def clean_html(html, base_url, lead_image=None):
    """Resolve relative URLs, fix lazy images, and reduce the markup to a safe subset.
    `lead_image` is put at the top if the content has no image of its own."""
    if not html or not html.strip():
        return ""
    root = _parse(html)
    _fix_images(root)
    _fix_code(root)
    root.make_links_absolute(base_url, resolve_base_href=False)
    if lead_image and root.find(".//img") is None:
        root.insert(0, lxml.html.Element("img", src=lead_image, alt=""))
        root[0].tail, root.text = root.text, None
    html = lxml.html.tostring(root, encoding="unicode")

    html = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https"},
        link_rel="noopener noreferrer",
    )
    # nh3 has no hook for adding attributes, so add the fixed ones here.
    html = html.replace("<img ", '<img loading="lazy" referrerpolicy="no-referrer" ')
    html = html.replace("<a ", '<a target="_blank" ')
    html = html.replace("<table>", '<div class="table-wrap"><table>')
    html = html.replace("</table>", "</table></div>")
    return html


class PageFetcher:
    """Fetches article pages: plain HTTP first, then one shared headless Chromium
    (started on first use) for pages that need JavaScript or block plain clients."""

    def __init__(self):
        self._pw = self._browser = self._context = None
        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self._browser:
            self._browser.close()
            self._pw.stop()

    def fetch_http(self, url):
        resp = self._session.get(url, timeout=20)
        resp.raise_for_status()
        return resp.text

    def fetch_browser(self, url):
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._context = self._browser.new_context(user_agent=USER_AGENT)
        page = self._context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass  # pages with endless background requests; use what has loaded
            return page.content()
        finally:
            page.close()


def og_image(html):
    try:
        found = lxml.html.fromstring(html).xpath(
            '//meta[@property="og:image" or @name="twitter:image"]/@content')
    except (lxml.etree.ParserError, ValueError):
        return None
    return found[0] if found and found[0].startswith("http") else None


def extract_page(html, url, title):
    """Main content of a page as HTML, or None if nothing article-like was found."""
    try:
        content = Document(html).summary(html_partial=True)
    except Exception:
        content = None
    if looks_like_article(content, title):
        return content
    content = trafilatura.extract(
        html, url=url, output_format="html",
        include_tables=True, include_images=True, include_links=True, include_formatting=True,
    )
    return content if looks_like_article(content, title) else None


def article_body(item, fetcher):
    """Return (sanitized HTML, how it was obtained) for a feed item."""
    link, title = item["link"], item["title"]
    if text_length(item.get("content")) >= MIN_FEED_TEXT:
        return clean_html(item["content"], link), "feed"

    for method in (fetcher.fetch_http, fetcher.fetch_browser):
        try:
            html = method(link)
        except Exception as e:
            print(f"  [!] {method.__name__} failed for {link}: {str(e)[:120]}")
            continue
        content = extract_page(html, link, title)
        if content:
            return clean_html(content, link, lead_image=og_image(html)), "page"

    # content:encoded is the complete post even when it is short; the summary is an excerpt.
    if item.get("content"):
        return clean_html(item["content"], link), "feed"
    return clean_html(item.get("summary") or "", link), "summary"
