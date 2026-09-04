# VISION-AI Master Audit Report (code-truth)

**Baseline:** v3.9.0-STUDIO source  
**Result version:** v4.0.0-HARDENED

## Executive summary
Code inspection (not docs) found production-blocking issues: worker heartbeat could auto-create workers, Studio accepted model/LoRA ids without capability checks, SVD-XT was exposed as T2V, Drive paths lacked traversal protection, Studio status endpoints were public, and JSON registry lacked job state events. Chat cascade and auth cores were preserved.

## Inventory (high level)
- Backend: FastAPI `main.py`, routes: chat, login, studio, workers, upload, upgrade, skills, agent
- Services: llm, image_gen, flux_image, colab_worker, model_registry, studio_engine, quota, security, youtube, …
- Frontend: index, login, studio, settings, boost, upgrade, admin pages
- Deploy: Dockerfile, run.py, railway.toml, Procfile

## P0 fixes applied
1. Heartbeat no longer registers unknown workers  
2. Worker register requires configured secret  
3. Drive path sanitization (no `..`, no absolute paths)  
4. SVD-XT marked I2V-only; API rejects T2V for it  
5. Studio endpoints require auth  
6. Job ownership checks on job detail  
7. Model/LoRA capability validation before generate/train/video  

## Remaining limitations (honest)
- Full LoRA training/resume still requires Colab worker implementation claiming jobs  
- Video generation is queue-only until worker executes  
- JSON registry is not Postgres (abstraction ready, backend still file)  
- Image providers may still ignore exotic samplers not supported by free fallbacks  
- No unlimited free GPU — Colab/Kaggle quotas apply  
