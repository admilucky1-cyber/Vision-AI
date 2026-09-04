# Changelog — v5.6.2

### Added
- SQLAlchemy models: User, UserPreferences, RefreshToken, UsageEvent
- SQLite default DB; PostgreSQL via DATABASE_URL
- Settings API: GET/PATCH /api/settings, POST reset, GET schema
- Preference validation allowlist
- LLM policy helper for response_style / reasoning_level
- JSON → DB migration script
- Frontend server sync + legacy key migration

### Changed
- Version identity → 5.6.2
- Settings changes PATCH backend when authenticated

### Not claimed complete
- Full refresh-token rotation in login flow
- Redis-backed rate limit cluster mode
- Forced server-side chat history
