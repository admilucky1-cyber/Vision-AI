# Vision AI Smart Video v6.4.0

## Honest capability map

| Goal | How Vision AI does it | Hardware |
|------|----------------------|----------|
| Images → polished video + soundtrack + effects | **ffmpeg smart compose** (`/api/smart-video/*`) | CPU / small GPU host (G4-class OK) |
| Image-to-video generative | Queue to **Model Studio / Colab worker** when online | Needs GPU worker |
| Tabular model training any length | Data Lab v6.3+ adaptive train | CPU |

There is **no** truthful system that produces “best video of all input types” at SOTA quality on a single small G4 with near-zero load. This release optimizes the **smart, low-load path** that actually runs firmly on modest hardware, and keeps generative video on workers.

## API
- `GET  /api/smart-video/status`
- `POST /api/smart-video/slideshow` — paths JSON
- `POST /api/smart-video/slideshow-upload` — multipart images + optional audio
- `POST /api/smart-video/mux-audio`
- `POST /api/smart-video/generate-queue` — GPU worker if available
- `GET  /api/smart-video/download/{name}`

## Effects
`none` | `sharpen` | `vignette` | `eq` (+ background audio volume/fade)
