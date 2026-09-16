# Forever-free stack (no paid API required)

Honest truth: **no** provider is unlimited forever. Free tiers have **rate limits**.  
This app is tuned to use **only free keys** and to **failover** when one hits a limit.

## Keys to set on Railway (all free, no card for basic use)

| Key | Get it | Role |
|-----|--------|------|
| `GROQ_API_KEY` | https://console.groq.com | Fast chat (Llama 3.3 70B) |
| `GOOGLE_API_KEY` | https://aistudio.google.com/apikey | Gemini Flash free tier |
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys | Many `:free` models (rate-limited) |
| `HF_TOKEN` | https://huggingface.co/settings/tokens | Free images (Inference API) |
| `TAVILY_API_KEY` | optional free tier | Search (or use DuckDuckGo built-in) |

Optional: `DEEPSEEK_API_KEY` if you have free credits.

## Auto routing (v2.4.6+)

1. **Groq** free  
2. **Gemini 2.5/2.0 Flash** free  
3. **OpenRouter** `openrouter/free` + other `:free` models  
4. DeepSeek only if key present  

Images: **Colab Boost** (free GPU) → **HF** free API → Gemini image if available.

## Rate limits (expect these)

- Groq / Gemini: daily or RPM caps on free tier  
- OpenRouter `:free`: often ~20 RPM and a daily request cap (varies; sometimes higher after a small one-time credit)  
- When one fails, the next provider is tried automatically  

## Users don’t buy keys

Your **owner** keys on the server power all free users (within plan limits).  
Users pay you (Easypaisa/bank) for Pro; you keep using free upstream APIs.

## Stay “best effort free”

1. Put **all three** of Groq + Gemini + OpenRouter keys so failover works.  
2. Keep **Colab Boost** for heavy images.  
3. Prefer short prompts when near rate limits.  
4. Monitor OpenRouter free model list — IDs change over time.

There is no legal way to get **unlimited** GPT-5/Claude-class quality at $0 forever.  
This stack maximizes **quality per free key** with automatic fallbacks.
