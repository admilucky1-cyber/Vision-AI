# Security baseline (v2.8.1)

## In place
- Worker secret header for Colab endpoints
- Guest mode optional via ALLOW_GUEST
- No secrets committed (.env, cookies.txt gitignored)
- Rate limit env vars (RATE_LIMIT_*)

## CI
- `bandit` on routes/services (informational in CI)

## Do not
- Commit `.env`, API keys, cookies.txt
- Disable HTTPS in production
- Expose WORKER_SECRET publicly

## Recommended
- Rotate SECRET_KEY periodically
- Keep ALLOWED_HOSTS / CORS_ORIGINS tight in production
