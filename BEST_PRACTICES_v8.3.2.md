# Vision AI v8.3.2 — validated preferred stack

## Critical fix
- **X-Robots-Tag** was `noindex` on ALL responses (blocked SEO). Now:
  - Public pages: `index, follow`
  - `/api` `/chat` `/auth` `/admin`: `noindex`

## Preferred features kept
- Schema.org @graph + `/api/schema` + live `schema-refresh.js`
- robots.txt + sitemap.xml
- Optional ads / plans monetization
- Browser-safe layout, column forms
- Railway health hosts, RLock, upload fix, short LLM answers
- Optional Mongo, Rust PII
- Security headers, HSTS, correlation IDs
- Static asset long-cache; HTML no-cache

## Deploy
Use this zip only. Set APP_BASE_URL. Submit sitemap in Search Console.
