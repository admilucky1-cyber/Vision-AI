# Security Audit — v5.6.2

## Findings & actions
| Issue | Severity | Action |
|-------|----------|--------|
| Preferences only in localStorage | Medium | Server-side `UserPreferences` + API |
| Mass assignment on settings | Medium | Pydantic + allowlist validation |
| Default SECRET_KEY | High (ops) | Documented; startup should set env |
| JSON user store multi-instance races | Medium | DB path + migration; login still dual-mode |
| API keys in browser | High if present | Not expanded; vault pattern preferred |
| Stack traces | Medium | Existing handlers; settings returns structured 422 |

## Controls
- Settings mutations require Bearer token
- Guest cannot PATCH settings
- Unknown preference fields rejected
- Passwords remain bcrypt via existing login flows
- No secrets logged in new settings code paths
