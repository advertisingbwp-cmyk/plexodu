"""
Phase 4 — SEO, Vercel & Legal Disclosure Tests
"""

import json
import os
import re
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND = os.path.join(REPO_ROOT, "frontend")

INDEX_HTML = os.path.join(FRONTEND, "index.html")
BLOG_INDEX_HTML = os.path.join(FRONTEND, "blog", "index.html")
BLOG_POST_HTML = os.path.join(FRONTEND, "blog", "google-gemini-student-offer-pakistan-2026", "index.html")
PRIVACY_HTML = os.path.join(FRONTEND, "privacy.html")
TERMS_HTML = os.path.join(FRONTEND, "terms.html")
SITEMAP_XML = os.path.join(FRONTEND, "sitemap.xml")
ROBOTS_TXT = os.path.join(FRONTEND, "robots.txt")
VERCEL_JSON = os.path.join(REPO_ROOT, "vercel.json")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestIndexHtml:
    def test_canonical_points_to_root(self):
        c = read(INDEX_HTML)
        assert 'href="https://plexudo.vercel.app/"' in c
    def test_adsense_tag_present(self):
        assert "ca-pub-3168330263525370" in read(INDEX_HTML)
    def test_og_url_is_root(self):
        assert 'og:url" content="https://plexudo.vercel.app/"' in read(INDEX_HTML)

class TestBlogIndexHtml:
    def test_canonical_is_blog_not_root(self):
        c = read(BLOG_INDEX_HTML)
        assert 'href="https://plexudo.vercel.app/blog/"' in c
        assert 'rel="canonical" href="https://plexudo.vercel.app/"' not in c
    def test_title_is_blog_specific(self):
        c = read(BLOG_INDEX_HTML)
        title = c.split("<title>")[1].split("</title>")[0]
        assert "Blog" in title
        assert "YouTube Creator SEO, Keyword" not in title
    def test_schema_is_collection_page(self):
        c = read(BLOG_INDEX_HTML)
        assert '"CollectionPage"' in c
        assert '"https://plexudo.vercel.app/blog/#webpage"' in c
    def test_no_software_application_schema(self):
        assert '"SoftwareApplication"' not in read(BLOG_INDEX_HTML)

class TestBlogPostHtml:
    def test_canonical_is_article_url(self):
        expected = "https://plexudo.vercel.app/blog/google-gemini-student-offer-pakistan-2026/"
        assert f'href="{expected}"' in read(BLOG_POST_HTML)
    def test_canonical_not_root(self):
        assert 'rel="canonical" href="https://plexudo.vercel.app/"' not in read(BLOG_POST_HTML)
    def test_schema_is_article(self):
        assert '"Article"' in read(BLOG_POST_HTML)
    def test_schema_webpage_id_is_article_url(self):
        expected_id = "https://plexudo.vercel.app/blog/google-gemini-student-offer-pakistan-2026/#webpage"
        assert expected_id in read(BLOG_POST_HTML)
    def test_keywords_meta_is_article_relevant(self):
        c = read(BLOG_POST_HTML)
        match = re.search(r'<meta name="keywords" content="([^"]+)"', c)
        assert match
        kw = match.group(1)
        assert "YouTube SEO Tool" not in kw
        assert "Gemini" in kw or "Pakistan" in kw

class TestSitemapXml:
    def test_includes_homepage(self):
        assert "https://plexudo.vercel.app/" in read(SITEMAP_XML)
    def test_includes_blog_index(self):
        assert "https://plexudo.vercel.app/blog/" in read(SITEMAP_XML)
    def test_includes_blog_post(self):
        assert "google-gemini-student-offer-pakistan-2026" in read(SITEMAP_XML)
    def test_includes_privacy_and_terms(self):
        c = read(SITEMAP_XML)
        assert "privacy.html" in c
        assert "terms.html" in c
    def test_valid_xml_structure(self):
        import xml.etree.ElementTree as ET
        tree = ET.parse(SITEMAP_XML)
        assert "urlset" in tree.getroot().tag

class TestRobotsTxt:
    def test_disallows_api(self):
        assert "Disallow: /api/" in read(ROBOTS_TXT)
    def test_disallows_dashboard(self):
        assert "Disallow: /dashboard" in read(ROBOTS_TXT)
    def test_disallows_dashboard_html(self):
        assert "Disallow: /dashboard.html" in read(ROBOTS_TXT)
    def test_has_sitemap_directive(self):
        assert "Sitemap: https://plexudo.vercel.app/sitemap.xml" in read(ROBOTS_TXT)

class TestVercelJson:
    def _config(self):
        with open(VERCEL_JSON, encoding="utf-8") as f:
            return json.load(f)
    def test_has_global_x_content_type_options(self):
        config = self._config()
        found = False
        for block in config.get("headers", []):
            if block.get("source") in ("/(.*)", "/"):
                for h in block.get("headers", []):
                    if h["key"] == "X-Content-Type-Options" and h["value"] == "nosniff":
                        found = True
        assert found
    def test_has_global_referrer_policy(self):
        config = self._config()
        found = False
        for block in config.get("headers", []):
            if block.get("source") in ("/(.*)", "/"):
                for h in block.get("headers", []):
                    if h["key"] == "Referrer-Policy":
                        found = True
        assert found
    def test_has_global_x_frame_options(self):
        config = self._config()
        found = False
        for block in config.get("headers", []):
            if block.get("source") in ("/(.*)", "/"):
                for h in block.get("headers", []):
                    if h["key"] == "X-Frame-Options":
                        found = True
        assert found
    def test_tool_redirects_use_301(self):
        for route in self._config().get("routes", []):
            if "youtube-seo-tool" in route.get("src", ""):
                assert route.get("status") == 301
    def test_has_blog_index_dest(self):
        found = any(r.get("dest", "").endswith("blog/index.html") for r in self._config().get("routes", []))
        assert found

class TestPrivacyHtml:
    def test_adsense_advertising_disclosure(self):
        c = read(PRIVACY_HTML)
        assert "Google AdSense" in c
        assert "dvertising" in c
    def test_google_ads_opt_out_link(self):
        assert "google.com/settings/ads" in read(PRIVACY_HTML)
    def test_groq_ai_disclosure(self):
        c = read(PRIVACY_HTML)
        assert "Groq" in c
        assert "groq.com" in c.lower()

class TestTermsHtml:
    def test_adsense_disclosure(self):
        assert "Google AdSense" in read(TERMS_HTML)
    def test_groq_disclosure(self):
        assert "Groq" in read(TERMS_HTML)
