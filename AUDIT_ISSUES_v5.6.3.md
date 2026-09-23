# Audit — remaining / fixed issues (v5.6.3)

## Fixed in this pass
1. Orphan unique-banner close button + extra `</div>` in index.html (broke main tag balance)
2. Asset cache drift: JS still `?v=562` while layout CSS was `?v=563` → unified to **563**
3. upgrade.html possible unclosed div

## Still present (non-blocking)
| Issue | Severity | Notes |
|-------|----------|--------|
| Default SECRET_KEY | Ops | Set strong SECRET_KEY on Railway |
| Admin pages load legacy CSS stack | Low | Still functional; Nova layered on top |
| Dual user store (JSON + SQLAlchemy) | Medium | By design during migration |
| Settings API needs SQLAlchemy | Medium | Mount fails soft if missing; pip install covers it |
| Offline badge false positives | Low | Network probe UX |
| Full refresh-token rotation | Deferred | Table exists, login path still JWT JSON |

## Verified OK
- All `.py` files parse (AST)
- main.py login/settings try-except structure
- settings.js / index.js node --check
- railway.toml startCommand = python run.py
- Critical modules present
