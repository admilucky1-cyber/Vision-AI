# Free AI sources for Vision AI (2026)

**Nothing is truly unlimited** at high quality. Use rate-limited free tiers + failover.

## Best free chat (recommended order)

| Provider | Free reality | Env key |
|----------|--------------|---------|
| **Groq** | Strong daily free RPM (e.g. Llama 8B/70B) | `GROQ_API_KEY` |
| **Google Gemini** | Free AI Studio quota (RPM/RPD) | `GOOGLE_API_KEY` |
| **OpenRouter `:free`** | ~20 RPM, ~50 req/day (or 1000/day after $10 one-time) | `OPENROUTER_API_KEY` |
| **DeepSeek** | Own free/cheap tier | `DEEPSEEK_API_KEY` |
| **Hugging Face** | **Not unlimited** — ~$0.10/mo credits or rate-limited serverless | `HF_TOKEN` |

### OpenRouter free model IDs (examples — list changes)
- `openrouter/free` (auto free router)
- `meta-llama/llama-3.3-70b-instruct:free`
- `nvidia/nemotron-3-super-120b-a12b:free`
- Live list: https://openrouter.ai/models?q=free

### Hugging Face
- Good for **image caption / small models**, not primary chat at volume
- Inference Providers free credits are tiny for production chat
- Prefer Groq + Gemini + OpenRouter free for Vision AI chat

## yt-dlp cookies (Netscape format)

File must start with:
```
# Netscape HTTP Cookie File
```
or
```
# HTTP Cookie File
```

Columns (tab-separated):
```
domain  flag  path  secure  expiration  name  value
```

Example:
```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	1800000000	VISITOR_INFO1_LIVE	xxxx
.youtube.com	TRUE	/	TRUE	1800000000	SID	xxxx
```

**How to export**
1. Chrome extension: **Get cookies.txt LOCALLY** (open-source) while on youtube.com
2. Or: `yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com"`
3. Set `YTDLP_COOKIES=/app/cookies.txt` (Railway) or project path locally

**Do not** use old “Get cookies.txt” (non-LOCALLY) — reported malware.

## Microphone permission denied

Browsers only allow mic on **secure contexts**:
- `https://your-domain`
- `http://localhost` / `http://127.0.0.1`

Blocked on `http://192.168.x.x` or plain public HTTP.

Fix: deploy with HTTPS (Railway default, Cloudflare Tunnel) or use localhost.
