# v4.5.0

## Implemented (remaining from audit)
- POST /api/workers/jobs/claim — worker pulls queued jobs by capability
- POST /api/workers/jobs/complete — worker reports result + artifact
- Colab worker heartbeat cycle can claim & run image_generate jobs
- ImageIn + generate_image propagate: model_id, lora_path, weight, seed, guidance, negative
- services/artifacts.py — disk PNG from base64
- Studio UI: workers tab, seed/steps/guidance/lora weight, I2V defaults
- SVD-XT remains I2V-only

## Still limited (honest)
- Full LoRA training GPU loop (Kohya/diffusers train) not bundled in worker — job queues only
- Video execution on worker not fully implemented (queue + capability checks only)
- Registry still JSON (not Postgres)
- Free GPU quotas are provider limits — not unlimited
