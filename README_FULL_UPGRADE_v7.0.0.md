# Vision AI v7.0.0 — Full Upgrade

## Included (cumulative)

| Area | Capability |
|------|------------|
| Chat + LLM | Multi-provider cascade, `/api/llm`, UTF-8 middleware |
| Data Lab | Multi-file CSV/Excel, clean, train (any length adaptive), forecast |
| Smart Video | ffmpeg slideshow + audio (low CPU) |
| Studio | Image/video queue hooks (GPU workers optional) |
| Canvas | VisionCanvas HiDPI + Android/Desktop resize |
| UI | Device-fit, theme controls, scroll fixes, touch gestures |
| Safety | Rust PII redactor bridge (when binary present) |
| Railway | Dockerfile, health `/health`, CPU torch path, syntax-safe main |
| Tooling | `scripts/project_check.py` |

## Run local (Windows / Linux)
```bash
python -m pip install -r requirements.txt
copy .env.example .env   # set keys
python run.py
```
Open http://127.0.0.1:8080

## Railway
- Builder: Dockerfile
- Start: `python run.py`
- Health: `/health`
- Env: SECRET_KEY, ALLOWED_HOSTS, APP_BASE_URL, GOOGLE/GROQ/OPENROUTER keys

## Honest limits
Not unlimited tokens, not unlimited RAM training, not SOTA video on free Railway CPU.
