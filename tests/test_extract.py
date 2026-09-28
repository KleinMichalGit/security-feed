from extract import clean_html, looks_like_article

BASE = "https://example.com/blog/post"


def test_keeps_tables_and_wraps_them():
    html = "<table><tr><th>CVE</th><th>CVSS</th></tr><tr><td>CVE-2026-1</td><td>9.8</td></tr></table>"
    out = clean_html(html, BASE)
    assert '<div class="table-wrap"><table>' in out
    assert "<th>CVSS</th>" in out and "<td>9.8</td>" in out


def test_images_are_absolute_and_lazy():
    out = clean_html('<p>x</p><img src="/img/a.png" alt="diagram">', BASE)
    assert 'src="https://example.com/img/a.png"' in out
    assert 'loading="lazy"' in out and 'referrerpolicy="no-referrer"' in out


def test_lazy_loaded_image_uses_data_src():
    out = clean_html('<img src="data:image/gif;base64,R0l" data-src="https://cdn.example.com/b.png">', BASE)
    assert 'src="https://cdn.example.com/b.png"' in out


def test_strips_scripts_and_event_handlers():
    out = clean_html('<p onclick="x()">hi</p><script>alert(1)</script><img src="a.png" onerror="alert(1)">', BASE)
    assert "script" not in out and "alert" not in out and "onclick" not in out and "onerror" not in out


def test_rejects_javascript_links():
    out = clean_html('<a href="javascript:alert(1)">x</a>', BASE)
    assert "javascript" not in out


def test_links_open_in_new_tab():
    out = clean_html('<a href="/other">x</a>', BASE)
    assert 'href="https://example.com/other"' in out
    assert 'target="_blank"' in out and 'rel="noopener noreferrer"' in out


def test_full_document_input():
    out = clean_html("<html><body><p>Hello</p></body></html>", BASE)
    assert "<p>Hello</p>" in out


def test_empty_input():
    assert clean_html("", BASE) == ""
    assert clean_html(None, BASE) == ""


def test_lead_image_added_only_when_content_has_none():
    out = clean_html("<p>Body text</p>", BASE, lead_image="https://example.com/hero.jpg")
    assert out.index("hero.jpg") < out.index("Body text")
    out = clean_html('<p>Body</p><img src="/own.png">', BASE, lead_image="https://example.com/hero.jpg")
    assert "hero.jpg" not in out and "own.png" in out


def test_single_line_pre_becomes_inline_code():
    out = clean_html("<p>request <pre>/%50SEMHUB/</pre> path</p><pre>line one\nline two</pre>", BASE)
    assert "<code>/%50SEMHUB/</code>" in out
    assert "<pre>line one\nline two</pre>" in out


def test_multiline_code_outside_pre_is_wrapped():
    out = clean_html("<p>Example:</p><code>def f():\n    return 1</code><p>after</p>", BASE)
    assert "<pre><code>def f():\n    return 1</code></pre>" in out
    assert "<pre><code>" not in clean_html("<p>Use <code>gateMode</code> here</p>", BASE)


def test_placeholder_image_without_real_source_is_dropped():
    out = clean_html('<p>x</p><img src="data:image/png;base64,AAAA">', BASE)
    assert "<img" not in out


def test_looks_like_article_rejects_consent_page():
    consent = "<p>" + "We value your privacy. Manage cookie preferences and consent. " * 20 + "</p>"
    article = "<p>" + "Citrix confirmed two NetScaler zero-days exploited in attacks. " * 20 + "</p>"
    title = "Citrix confirms two NetScaler RCE zero-days exploited in attacks"
    assert not looks_like_article(consent, title)
    assert looks_like_article(article, title)
