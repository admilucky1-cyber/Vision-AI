# Sample ZIP review (v2.9.2)

| Package | Verdict | Action in Vision AI |
|---------|---------|---------------------|
| **yt-dlp-master.zip** | Official yt-dlp source tree | **Not vendored.** App already uses PyPI `yt-dlp>=2024` in requirements. No third-party trackers added by us. |
| **AI-Youtube-Shorts-Generator** | Separate AI shorts pipeline | **Not merged** (different stack/deps). YouTube summary/quiz/download already in Vision AI. |
| **free-short-video-studio** | Next.js + Cloudflare studio UI | **Not merged** (would require Node/Next rewrite of the whole frontend). |
| **Open-Generative-AI** | Large multi-app monorepo | **Not merged** (incompatible architecture). Ideas only. |

## Why not full merge?
Dropping entire foreign apps into FastAPI+static frontend would break Railway deploy, double dependency graphs, and introduce untested trackers/UI frameworks.

## What we applied instead
- Theme-aware **sidebar + topbar** for every preset
- Clearer **3D logo** rendering
- Keep production **yt-dlp via pip** (no zip embed, no extra trackers)
