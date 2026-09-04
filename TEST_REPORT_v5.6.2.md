# Test Report — v5.6.2

## Executed in build environment
| Test | Result |
|------|--------|
| `node --check frontend/static/js/settings.js` | Pass |
| Preference validate_patch unit logic | Covered in `tests/test_settings_api.py` |
| DB init + prefs row | `tests/test_db_models.py` |

## Run locally
```bash
pip install -r requirements.txt
pytest tests/test_settings_api.py tests/test_db_models.py -q
pytest tests/ -q   # full suite
```

## Known limitations
- Full HTTP integration tests need running server + auth token
- Playwright UI tests not added in this pass
- Login still dual-mode (JSON + DB lazy user)
