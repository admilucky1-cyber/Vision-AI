# Champion patterns (world top sellers) → Vision AI v8.5.0

## Frontend (Linear / Stripe / Notion-style)
| Pattern | Implementation |
|---------|----------------|
| Design tokens | spacing, radius, motion, focus ring |
| Focus-visible a11y | keyboard users see clear focus |
| Empty / loading / error states | `.ch-empty`, `.ch-skeleton`, `.ch-error` |
| Non-blocking ops chrome | live status pill (`/health/ready`) |
| Single state | `VAStore` (React-style) |

## Backend (Google/Netflix ops style)
| Pattern | Implementation |
|---------|----------------|
| Liveness | `GET /health` |
| Readiness | `GET /health/ready` (DB) |
| Version surface | `GET /api/version` |
| Graceful deps | soft imports (rate limit, mongo) |
| Correlation IDs | existing middleware |

## Operations
- Poll readiness every 30s in UI
- Deploy one zip; verify `/api/version` + `/health/ready`
- Set `APP_BASE_URL` for SEO

Full React/Next rewrite is optional later; patterns above match top products without a multi-month migration.
