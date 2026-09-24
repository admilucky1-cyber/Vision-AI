# Vision AI v8.4.1 — Frontend / Backend / Testing audit

## Frontend
| Check | Result |
|-------|--------|
| JS files syntax (`node --check`) | 30/30 OK |
| Critical scripts present | va-store, click-fix, index, auth, vision-system |
| Script order | store → index → click-fix (correct) |
| Layout CSS | browser-safe-layout + click-fix present |
| SEO / schema scripts | present |

## Backend
| Check | Result |
|-------|--------|
| Python files | 92 |
| Syntax errors | 0 |
| `/api/version`, health, Railway hosts | present |
| Optimizer RLock | present |
| SEO router | present |
| Optional Mongo | present |
| Rate limit | slowapi soft-import (works if missing in minimal test env) |

## Testing
| Suite | Result (audit machine) |
|-------|-------------------------|
| smoke + version + schemas | PASS |
| Full unit tests without full deps | 42 passed |
| Railway regression (needs full `pip install -r requirements.txt`) | needs jose/bcrypt/slowapi/itsdangerous — **included in requirements.txt for Docker/Railway** |

### How to run tests properly
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
pytest tests/ -q
```

Production Railway image installs full requirements — local missing packages are not a production defect.
