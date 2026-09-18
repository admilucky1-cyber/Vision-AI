# Why models fail + Offline + Plans UI

## All AI models unavailable
| Variable | Problem |
|----------|---------|
| GROQ_API_KEY | Empty |
| OPENROUTER_API_KEY | Empty |
| GOOGLE_API_KEY | Must be full valid key |
| APP_BASE_URL | Broken quote / wrong host (use vision-ai-v6) |
| ALLOWED_HOSTS | Still lists vision-ai-v5 — update to v6 |
| SECRET_KEY | Must be non-empty 32+ chars |

Set on Railway, then redeploy.
