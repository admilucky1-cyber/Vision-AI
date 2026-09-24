"""Public SEO endpoints and ads config (no auth)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from services.seo_ads import ads_config, public_base_url, schema_graph, seo_meta, sitemap_urls

router = APIRouter(tags=["SEO"])


@router.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    base = public_base_url()
    body = f"""User-agent: *
Allow: /
Allow: /frontend/
Disallow: /api/
Disallow: /chat/
Disallow: /auth/
Disallow: /admin/
Sitemap: {base}/sitemap.xml
"""
    return PlainTextResponse(body, media_type="text/plain; charset=utf-8")


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    urls = sitemap_urls()
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        parts.append(
            f"<url><loc>{u['loc']}</loc>"
            f"<changefreq>{u['changefreq']}</changefreq>"
            f"<priority>{u['priority']}</priority></url>"
        )
    parts.append("</urlset>")
    return Response("\n".join(parts), media_type="application/xml")


@router.get("/api/seo")
async def api_seo():
    return seo_meta()


@router.get("/api/ads/config")
async def api_ads_config():
    """Public ad config — never exposes private keys."""
    cfg = ads_config()
    # Do not leak sponsor raw HTML to crawlers if disabled
    if not cfg.get("enabled"):
        cfg = {**cfg, "sponsor_html": ""}
    return JSONResponse(cfg, headers={"Cache-Control": "public, max-age=300"})


@router.get("/api/schema")
async def api_schema():
    """Full Schema.org JSON-LD graph (for debugging / external tools)."""
    return JSONResponse(schema_graph(), headers={"Cache-Control": "public, max-age=600"})
