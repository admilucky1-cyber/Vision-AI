# How Google Drive mount works (Colab)

## What happens
1. You open a Colab notebook under **one Google account**.
2. Code runs `drive.mount("/content/drive")`.
3. Google shows a **permission popup** for that account (once per session/runtime).
4. Your Drive appears at `/content/drive/MyDrive/...`.
5. Vision AI stores models under:
   `MyDrive/vision_ai_models/`
   (e.g. sdxl-turbo weights).

## Important
- The Gmail is **whichever account is logged into Colab**, not a separate question from Vision AI.
- Free Drive ≈ 15 GB shared with Gmail/Photos — large models need space.
- After Runtime disconnect, mount again (or re-run Boost).
- Copy models from Drive → `/content/...` before loading (faster than reading Drive during inference).

## First time vs next time
| Time | What you wait for |
|------|-------------------|
| First | Download model into Drive (minutes) |
| Later | Copy from Drive to `/content` (faster) + load GPU |

## If mount fails
- Allow popups for colab.research.google.com
- Use the same account that has Drive space
- Runtime → Restart → run mount/Boost again
