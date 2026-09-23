# Vision AI v8.2.2 — Master status (stronger than all prior zips in this repo)

This package is the **single deploy source**. Older zips (v4–v8.2.1) are archives only.

## Included & verified

| Area | Status |
|------|--------|
| Version single source (VERSION + pyproject + UI) | 8.2.2 |
| Railway health hosts | healthcheck.railway.app + *.up.railway.app |
| Chat file upload (sync extractor) | Fixed |
| Short LLM answers ("4", "Yes") | Accepted |
| Optimizer deadlock | RLock |
| /api/version | Yes |
| /api/mongo/status | Optional Mongo |
| Mongo store | Optional (SQL fallback) |
| Rust PII redactor | native/pii_redactor |
| Browser-safe layout (Chrome/Edge/mobile) | Last CSS wins |
| Column structure (forms) | Yes |
| Delete-chat scoping | From v8.1.2 lineage |
| Device-fit + touch gestures | Yes |
| Data lab / train / video lineage | Present in tree |
| Dockerfile CPU torch + pip check | Yes |

## Deploy

1. Use only this zip on Railway
2. Hard refresh clients after deploy
3. Confirm GET /api/version → 8.2.2
4. Optional: MONGODB_URI for Mongo

## Stronger than older packages because

- All Railway regression fixes kept
- Layout no longer loses to older CSS order
- Mongo + Rust + JS status without breaking SQL
- Unified version metadata
