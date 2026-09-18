# Vision AI v7.3.0 — Best applied path

## Decision
- **Keep** FastAPI + HTML/JS (no full React rewrite yet)
- **Do not** add full Bootstrap/React bundles (heavy, rewrite cost)
- **Do** ship a single design system + Bootstrap-like utilities

## Applied
| Piece | Status |
|-------|--------|
| vision-system.css/js | Single entry on all pages |
| Layout (AppBar, pad, spacer, container) | Included |
| Theme-aware controls | Included |
| Utility kit (.va-row, .va-col, .va-btn, .va-card) | **New** |
| Device fit + safe-area | Included |
| Encoding sanitize (server/client) | From 7.0.1+ |
| Canvas HiDPI | From 6.9+ |

## Not applied (by design)
- Full React SPA
- Full Bootstrap CSS/JS
- Next.js

When the chat UI becomes unmaintainable, plan a **React chat shell only** on the same FastAPI APIs.
