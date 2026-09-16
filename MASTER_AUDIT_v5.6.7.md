# Vision AI v5.6.7 — Master Audit

## Level assessment

| Layer | Level | Notes |
|-------|-------|-------|
| Core chat + streaming | Advanced | Dual mount /chat + /api/chat |
| Auth (login/logout/guest/google) | Advanced | JWT + VisionAuth frontend |
| Settings + preferences DB | Advanced | SQLAlchemy SQLite/Postgres |
| UI system (Nova + Humanly) | Advanced | Tokens, polish, cross-platform |
| Layout / responsive | Advanced | dvh, safe-area, breakpoints |
| RAG / studio / agents | Medium–Advanced | Present; env/GPU dependent |
| Admin | Medium | Functional, mixed legacy CSS |
| Tests / CI | Medium | tests/ present; run in CI optional |

## Verified
- All critical modules present
- main.py AST clean; login/settings/db try blocks valid
- Core JS syntax OK
- 9 app HTML pages + 2 admin; Nova + cross-platform on app pages
- Asset cache unified ?v=567
- VERSION file 5.6.7

## Production ops
- SECRET_KEY (32+)
- ALLOWED_HOSTS=*
- Start: python run.py
- Health: /health

## Not claiming
- Pixel-perfect on every device without live QA
- Unlimited free GPU / paid APIs without keys
