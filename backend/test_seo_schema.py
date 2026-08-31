"""
Automated Test Suite for Plexudo Schema.org & Technical SEO Compliance
Validates JSON-LD structures, canonical graph connections, entity integrity,
and indexing protection across all pages.
"""

import os
import re
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


class TestSeoAndSchemaCompliance(unittest.TestCase):

    def setUp(self):
        self.index_path = os.path.join(FRONTEND_DIR, "index.html")
        self.privacy_path = os.path.join(FRONTEND_DIR, "privacy.html")
        self.terms_path = os.path.join(FRONTEND_DIR, "terms.html")
        self.dashboard_path = os.path.join(FRONTEND_DIR, "dashboard.html")
        self.sitemap_path = os.path.join(FRONTEND_DIR, "sitemap.xml")
        self.robots_path = os.path.join(FRONTEND_DIR, "robots.txt")

    def _extract_json_ld(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        matches = re.findall(r'<script type=["\']application/ld\+json["\']>(.*?)</script>', content, re.DOTALL)
        self.assertTrue(len(matches) > 0, f"No JSON-LD script found in {file_path}")
        schemas = []
        for m in matches:
            data = json.loads(m.strip())
            schemas.append(data)
        return schemas

    def test_homepage_schema_graph(self):
        """Validates homepage unified Schema.org entity graph."""
        schemas = self._extract_json_ld(self.index_path)
        graph = schemas[0].get("@graph", [])
        self.assertTrue(len(graph) >= 5, "Homepage @graph must contain Organization, WebSite, SoftwareApplication, WebPage, and FAQPage.")

        type_map = {item.get("@type"): item for item in graph if isinstance(item, dict)}

        # 1. Organization
        self.assertIn("Organization", type_map)
        org = type_map["Organization"]
        self.assertEqual(org.get("@id"), "https://plexudo.vercel.app/#organization")
        self.assertEqual(org.get("name"), "Plexudo")
        self.assertEqual(org.get("url"), "https://plexudo.vercel.app/")

        # 2. WebSite
        self.assertIn("WebSite", type_map)
        site = type_map["WebSite"]
        self.assertEqual(site.get("@id"), "https://plexudo.vercel.app/#website")
        self.assertEqual(site.get("publisher", {}).get("@id"), "https://plexudo.vercel.app/#organization")

        # 3. SoftwareApplication
        self.assertIn("SoftwareApplication", type_map)
        app = type_map["SoftwareApplication"]
        self.assertEqual(app.get("@id"), "https://plexudo.vercel.app/#software")
        self.assertEqual(app.get("publisher", {}).get("@id"), "https://plexudo.vercel.app/#organization")

        # 4. WebPage
        self.assertIn("WebPage", type_map)
        page = type_map["WebPage"]
        self.assertEqual(page.get("@id"), "https://plexudo.vercel.app/#webpage")
        self.assertEqual(page.get("isPartOf", {}).get("@id"), "https://plexudo.vercel.app/#website")
        self.assertEqual(page.get("about", {}).get("@id"), "https://plexudo.vercel.app/#software")

        # 5. FAQPage
        self.assertIn("FAQPage", type_map)
        faq = type_map["FAQPage"]
        self.assertEqual(faq.get("@id"), "https://plexudo.vercel.app/#faq")
        self.assertTrue(len(faq.get("mainEntity", [])) == 5, "FAQPage must contain exactly 5 visible questions.")

    def test_privacy_and_terms_schema(self):
        """Validates legal pages WebPage schema & Breadcrumbs."""
        for path, page_name in [(self.privacy_path, "Privacy Policy"), (self.terms_path, "Terms of Service")]:
            schemas = self._extract_json_ld(path)
            graph = schemas[0].get("@graph", [])
            page = graph[0]
            self.assertEqual(page.get("@type"), "WebPage")
            self.assertEqual(page.get("isPartOf", {}).get("@id"), "https://plexudo.vercel.app/#website")
            self.assertEqual(page.get("publisher", {}).get("@id"), "https://plexudo.vercel.app/#organization")
            self.assertIn("breadcrumb", page)
            self.assertEqual(page["breadcrumb"].get("@type"), "BreadcrumbList")

    def test_zero_staging_urls_in_metadata(self):
        """Ensures zero staging or localhost URLs in public HTML/XML/TXT files."""
        files = [self.index_path, self.privacy_path, self.terms_path, self.sitemap_path, self.robots_path]
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
            self.assertNotIn("smtas-trend.netlify.app", text, f"Staging URL found in {fpath}")
            self.assertNotIn("localhost", text, f"Localhost URL found in {fpath}")
            self.assertNotIn("127.0.0.1", text, f"Local IP found in {fpath}")

    def test_dashboard_indexing_protection(self):
        """Ensures dashboard.html has strict noindex, nofollow, noarchive."""
        with open(self.dashboard_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn('name="robots" content="noindex, nofollow, noarchive"', text)
        self.assertIn('name="googlebot" content="noindex, nofollow, noarchive"', text)

    def test_sitemap_contains_only_public_pages(self):
        """Ensures sitemap.xml does NOT contain private routes."""
        with open(self.sitemap_path, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("dashboard.html", text)
        self.assertIn("https://plexudo.vercel.app/", text)
        self.assertIn("https://plexudo.vercel.app/privacy.html", text)
        self.assertIn("https://plexudo.vercel.app/terms.html", text)


if __name__ == "__main__":
    unittest.main()
