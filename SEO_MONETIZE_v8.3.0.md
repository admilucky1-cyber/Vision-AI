# Vision AI v8.3.0 — SEO + Monetization

## SEO
- Meta description, keywords, robots, canonical
- Open Graph + Twitter cards
- JSON-LD WebApplication schema
- `/robots.txt` and `/sitemap.xml`
- `GET /api/seo`

## Monetization (earn)
Already: **Plans** (Student/Pro/Team/Enterprise) + Easypaisa/bank/Stripe hooks in `routes/upgrade.py`

New ads layer (optional):
```
ADS_ENABLED=1
ADSENSE_CLIENT_ID=ca-pub-xxxxxxxx
ADSENSE_SLOT_SIDEBAR=1234567890
ADSENSE_SLOT_FOOTER=1234567890
ADS_FREE_ONLY=1
AFFILIATE_LINK=https://...
SPONSOR_BANNER_HTML=<optional html>
APP_BASE_URL=https://your-domain.up.railway.app
SEO_TITLE=...
SEO_DESCRIPTION=...
```

- Free users can see ads; paid plans skip ads when `ADS_FREE_ONLY=1`
- Upgrade CTA in sidebar → plans page
- `GET /api/ads/config` for frontend

## Google
1. Search Console → property = APP_BASE_URL
2. Submit sitemap: `https://YOUR_DOMAIN/sitemap.xml`
3. AdSense approval → paste client + slots in Railway env
