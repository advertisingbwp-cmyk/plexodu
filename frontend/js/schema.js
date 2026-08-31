/**
 * Plexudo Centralized Schema.org & Structured Data Architecture
 * Provides reusable, consistent, validated JSON-LD schema generators.
 * Uses canonical entity IDs and connected graph relationships.
 */

(function (global) {
  const BASE_URL = "https://plexudo.vercel.app";

  const CANONICAL_IDS = {
    organization: `${BASE_URL}/#organization`,
    website: `${BASE_URL}/#website`,
    software: `${BASE_URL}/#software`,
    logo: `${BASE_URL}/#logo`,
  };

  /**
   * Generates Organization Schema Object
   */
  function createOrganizationSchema(custom = {}) {
    return {
      "@type": "Organization",
      "@id": CANONICAL_IDS.organization,
      name: "Plexudo",
      url: `${BASE_URL}/`,
      logo: {
        "@type": "ImageObject",
        "@id": CANONICAL_IDS.logo,
        url: `${BASE_URL}/favicon.png`,
        contentUrl: `${BASE_URL}/favicon.png`,
        caption: "Plexudo Logo",
      },
      description: "Plexudo is a specialized YouTube SEO and channel growth platform providing 50/50 SEO scoring, keyword discovery, competitor analytics, and AI creator titles.",
      email: "advertisingbwp@gmail.com",
      ...custom,
    };
  }

  /**
   * Generates WebSite Schema Object
   */
  function createWebSiteSchema(custom = {}) {
    return {
      "@type": "WebSite",
      "@id": CANONICAL_IDS.website,
      url: `${BASE_URL}/`,
      name: "Plexudo",
      description: "All-in-one YouTube creator SEO, keyword discovery, and channel growth platform.",
      publisher: { "@id": CANONICAL_IDS.organization },
      inLanguage: "en-US",
      ...custom,
    };
  }

  /**
   * Generates SoftwareApplication Schema Object
   */
  function createSoftwareApplicationSchema(custom = {}) {
    return {
      "@type": "SoftwareApplication",
      "@id": CANONICAL_IDS.software,
      name: "Plexudo - YouTube Creator SEO & Growth Platform",
      url: `${BASE_URL}/`,
      description: "Comprehensive YouTube creator suite with 50/50 SEO Scoring, keyword discovery, competitor audits, and Groq AI title generators.",
      applicationCategory: "BusinessApplication",
      applicationSubCategory: "Video SEO & Creator Analytics",
      operatingSystem: "Web Browser (All Platforms)",
      browserRequirements: "Requires JavaScript. Requires HTML5.",
      publisher: { "@id": CANONICAL_IDS.organization },
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "USD",
        description: "Free welcome credits and sponsored reward passes.",
      },
      ...custom,
    };
  }

  /**
   * Generates WebPage Schema Object
   */
  function createWebPageSchema(url, name, description, custom = {}) {
    const pageUrl = url.startsWith("http") ? url : `${BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`;
    const pageId = `${pageUrl}${pageUrl.endsWith("/") ? "" : "/"}#webpage`;

    return {
      "@type": "WebPage",
      "@id": pageId,
      url: pageUrl,
      name: name,
      description: description,
      isPartOf: { "@id": CANONICAL_IDS.website },
      publisher: { "@id": CANONICAL_IDS.organization },
      inLanguage: "en-US",
      ...custom,
    };
  }

  /**
   * Generates BreadcrumbList Schema Object
   */
  function createBreadcrumbSchema(items = []) {
    return {
      "@type": "BreadcrumbList",
      itemListElement: items.map((item, idx) => ({
        "@type": "ListItem",
        position: idx + 1,
        name: item.name,
        item: item.url.startsWith("http") ? item.url : `${BASE_URL}${item.url.startsWith("/") ? "" : "/"}${item.url}`,
      })),
    };
  }

  /**
   * Generates Service Schema Object
   */
  function createServiceSchema(id, name, serviceType, description, url) {
    return {
      "@type": "Service",
      "@id": `${BASE_URL}/#${id}`,
      name: name,
      serviceType: serviceType,
      description: description,
      provider: { "@id": CANONICAL_IDS.organization },
      url: url.startsWith("http") ? url : `${BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`,
    };
  }

  /**
   * Generates FAQPage Schema Object
   */
  function createFAQPageSchema(qaList = [], pageId = `${BASE_URL}/#webpage`) {
    return {
      "@type": "FAQPage",
      "@id": `${BASE_URL}/#faq`,
      isPartOf: { "@id": pageId },
      mainEntity: qaList.map((qa) => ({
        "@type": "Question",
        name: qa.question,
        acceptedAnswer: {
          "@type": "Answer",
          text: qa.answer,
        },
      })),
    };
  }

  /**
   * Generates Article Schema Object
   */
  function createArticleSchema(slug, headline, description, datePublished, dateModified, authorName = "Plexudo Editorial Team") {
    const articleUrl = `${BASE_URL}/blog/${slug}`;
    return {
      "@type": "Article",
      "@id": `${articleUrl}#article`,
      headline: headline,
      description: description,
      url: articleUrl,
      mainEntityOfPage: { "@id": `${articleUrl}#webpage` },
      isPartOf: { "@id": CANONICAL_IDS.website },
      publisher: { "@id": CANONICAL_IDS.organization },
      author: {
        "@type": "Person",
        name: authorName,
      },
      datePublished: datePublished,
      dateModified: dateModified || datePublished,
      inLanguage: "en-US",
    };
  }

  /**
   * Builds Unified Graph for Whole Page
   */
  function buildEntityGraph(nodes = []) {
    return {
      "@context": "https://schema.org",
      "@graph": nodes,
    };
  }

  // Export module
  const PlexudoSchema = {
    BASE_URL,
    CANONICAL_IDS,
    createOrganizationSchema,
    createWebSiteSchema,
    createSoftwareApplicationSchema,
    createWebPageSchema,
    createBreadcrumbSchema,
    createServiceSchema,
    createFAQPageSchema,
    createArticleSchema,
    buildEntityGraph,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = PlexudoSchema;
  } else {
    global.PlexudoSchema = PlexudoSchema;
  }
})(typeof window !== "undefined" ? window : globalThis);
