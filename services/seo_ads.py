"""SEO helpers, Schema.org JSON-LD, and ad monetization for Vision AI."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

PRODUCT = "Vision AI"
DEFAULT_DESC = (
    "Vision AI — multimodal assistant for chat, coding, data lab, image and video. "
    "Fast free cascade, Pro plans, and tools for students and teams."
)


def public_base_url() -> str:
    return (
        os.getenv("APP_BASE_URL")
        or os.getenv("PUBLIC_BASE_URL")
        or "https://vision-ai.up.railway.app"
    ).rstrip("/")


def seo_meta() -> Dict[str, str]:
    base = public_base_url()
    return {
        "title": os.getenv("SEO_TITLE") or f"{PRODUCT} — AI Chat, Code, Data & Studio",
        "description": os.getenv("SEO_DESCRIPTION") or DEFAULT_DESC,
        "keywords": os.getenv("SEO_KEYWORDS")
        or "Vision AI, AI chat, multimodal AI, coding assistant, data lab, image generation",
        "author": os.getenv("SEO_AUTHOR") or PRODUCT,
        "og_image": os.getenv("SEO_OG_IMAGE") or f"{base}/frontend/static/icons/icon-512.png",
        "twitter_site": os.getenv("SEO_TWITTER") or "",
        "canonical": base + "/",
    }


def sitemap_urls() -> List[Dict[str, str]]:
    base = public_base_url()
    paths = [
        ("/", "1.0", "daily"),
        ("/frontend/login.html", "0.8", "weekly"),
        ("/frontend/plans.html", "0.9", "weekly"),
        ("/frontend/settings.html", "0.5", "monthly"),
        ("/frontend/studio.html", "0.7", "weekly"),
        ("/frontend/data-lab.html", "0.7", "weekly"),
        ("/frontend/skills.html", "0.6", "weekly"),
    ]
    return [
        {"loc": base + p, "priority": pri, "changefreq": cf}
        for p, pri, cf in paths
    ]


def schema_graph() -> Dict[str, Any]:
    """Full Schema.org @graph for rich results."""
    base = public_base_url()
    meta = seo_meta()
    org_id = f"{base}/#organization"
    website_id = f"{base}/#website"
    app_id = f"{base}/#app"

    organization = {
        "@type": "Organization",
        "@id": org_id,
        "name": PRODUCT,
        "url": base + "/",
        "logo": {
            "@type": "ImageObject",
            "url": f"{base}/frontend/static/icons/icon-512.png",
        },
        "sameAs": [
            s.strip()
            for s in (os.getenv("SEO_SAME_AS") or "").split(",")
            if s.strip()
        ],
    }
    if not organization["sameAs"]:
        del organization["sameAs"]

    website = {
        "@type": "WebSite",
        "@id": website_id,
        "url": base + "/",
        "name": PRODUCT,
        "description": meta["description"],
        "publisher": {"@id": org_id},
        "inLanguage": ["en", "ur"],
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": base + "/?q={search_term_string}",
            },
            "query-input": "required name=search_term_string",
        },
    }

    software = {
        "@type": ["SoftwareApplication", "WebApplication"],
        "@id": app_id,
        "name": PRODUCT,
        "url": base + "/",
        "applicationCategory": "MultimediaApplication",
        "operatingSystem": "Web, Windows, Android, iOS",
        "browserRequirements": "Requires JavaScript",
        "description": meta["description"],
        "image": meta["og_image"],
        "author": {"@id": org_id},
        "publisher": {"@id": org_id},
        "offers": [
            {
                "@type": "Offer",
                "name": "Free",
                "price": "0",
                "priceCurrency": "PKR",
                "url": base + "/frontend/plans.html",
            },
            {
                "@type": "Offer",
                "name": "Student",
                "price": os.getenv("STUDENT_PRICE_PKR") or "1499",
                "priceCurrency": "PKR",
                "url": base + "/frontend/plans.html",
            },
            {
                "@type": "Offer",
                "name": "Pro",
                "price": os.getenv("PRO_PRICE_PKR") or "2799",
                "priceCurrency": "PKR",
                "url": base + "/frontend/plans.html",
            },
        ],
        "featureList": [
            "AI chat with multi-provider cascade",
            "Image generation",
            "Video generation tools",
            "Data lab and model training",
            "Code assistance",
            "Studio workspace",
        ],
    }

    breadcrumb = {
        "@type": "BreadcrumbList",
        "@id": f"{base}/#breadcrumb",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": base + "/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Plans",
                "item": base + "/frontend/plans.html",
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": "Studio",
                "item": base + "/frontend/studio.html",
            },
        ],
    }

    faq = {
        "@type": "FAQPage",
        "@id": f"{base}/#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "What is Vision AI?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Vision AI is a multimodal web assistant for chat, coding, data analysis, image and video tools.",
                },
            },
            {
                "@type": "Question",
                "name": "Is Vision AI free?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Yes. A free tier is available. Student, Pro, Team and Enterprise plans unlock higher limits.",
                },
            },
            {
                "@type": "Question",
                "name": "How do I upgrade?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Open Plans in the app, choose a plan, and pay via the listed methods (e.g. Easypaisa, bank, or Stripe when configured).",
                },
            },
        ],
    }

    return {
        "@context": "https://schema.org",
        "@graph": [organization, website, software, breadcrumb, faq],
    }


def schema_json(indent: int | None = None) -> str:
    return json.dumps(schema_graph(), ensure_ascii=False, indent=indent)


def ads_config() -> Dict[str, Any]:
    client = (os.getenv("ADSENSE_CLIENT_ID") or os.getenv("ADS_CLIENT_ID") or "").strip()
    enabled = (os.getenv("ADS_ENABLED") or "0").strip() in ("1", "true", "True", "yes")
    if client:
        enabled = True
    return {
        "enabled": enabled and bool(client),
        "client_id": client if enabled else "",
        "slots": {
            "sidebar": (os.getenv("ADSENSE_SLOT_SIDEBAR") or "").strip(),
            "footer": (os.getenv("ADSENSE_SLOT_FOOTER") or "").strip(),
            "in_feed": (os.getenv("ADSENSE_SLOT_INFEED") or "").strip(),
        },
        "show_for_free_only": (os.getenv("ADS_FREE_ONLY") or "1").strip() in ("1", "true", "True"),
        "affiliate_link": (os.getenv("AFFILIATE_LINK") or "").strip(),
        "sponsor_html": (os.getenv("SPONSOR_BANNER_HTML") or "").strip()[:2000],
        "plans_url": "/frontend/plans.html",
        "upgrade_cta": os.getenv("UPGRADE_CTA") or "Go Pro — remove ads & unlock limits",
    }
