# Private API configuration

Set real credentials only in Railway: project → production → Vision Ai → Variables.
The repository's `.env.example` contains names and empty placeholders. Never upload
a real `.env`, credential export, database, or cookies file to GitHub or a shared ZIP.
Local `.env` files and runtime data are excluded from Git and the Docker build.

| Feature | Server variables |
| --- | --- |
| AI chat (at least one provider) | `GROQ_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`, or `DEEPSEEK_API_KEY` |
| Gemini model | `GEMINI_MODEL` (defaults to `gemini-3.6-flash`) |
| Tavily search | `TAVILY_API_KEY` |
| Hugging Face images | `HF_TOKEN` |
| YouTube API | `YOUTUBE_API_KEY` |
| Google image search | `GOOGLE_API_KEY` and `GOOGLE_ENGINE_ID` |
| Google sign-in | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |
| Stripe checkout and webhooks | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| Telegram notifications | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| Optional RunPod worker | `RUNPOD_API_KEY` and the worker endpoint settings |
| Application authentication | Independent random `SECRET_KEY` and `SESSION_SECRET` |

Missing optional integrations do not require creating every provider account.
Provider credentials must be issued by the relevant provider; a randomly generated
string is not a working provider key. An expired key needs replacement at its
provider. Insufficient credit must be resolved in the provider account.

## Flutter / FlutLab

The Flutter client needs only the public backend URL:

```sh
flutter run --dart-define=API_URL=https://vision-ai-v6.up.railway.app
```

Do not put provider keys in Dart source, assets, web JavaScript, or `--dart-define`.
Build-time defines are compiled into the app and are not a private secret store.
Authenticated requests go to Railway, which calls providers with server-held keys.
An app login token belongs to the signed-in user; it must never be a shared provider key.

## Verify without revealing values

`/api/llm/health` reports whether the four chat provider keys are configured. It does
not validate credentials, account balance, or model access. `/health/detailed`
also reports presence for Tavily, Hugging Face and Google sign-in.

The existing `/api/llm/test` diagnostic sends a small test generation to each chat
provider and may use provider quota. Connection probes in `services/api_vault.py`
return status codes and fixed error categories, never provider response bodies or
raw connection exceptions. OpenRouter is checked against its authenticated key
endpoint rather than its public model list.
