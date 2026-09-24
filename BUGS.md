| ID | Sev | File | Problem | Fix |
|----|-----|------|---------|-----|
| B01 | P0 | services/colab_worker.py | Heartbeat auto-created workers | Require prior register + secret |
| B02 | P0 | services/colab_worker.py | Register possible with empty secret if env unset | Fail if REGISTER_SECRET empty |
| B03 | P1 | services/studio_engine.py | model_id/lora_id ignored by generators | Capability check + worker_payload |
| B04 | P1 | studio video | svd-xt as T2V | capabilities.i2v only; default I2V |
| B05 | P1 | routes/studio.py | Public models/storage info | Require auth |
| B06 | P1 | model_registry | Drive path traversal | sanitize_drive_path |
| B07 | P1 | jobs | Username-only ownership | owner_id field + checks |
| B08 | P2 | jobs | No state machine | transition_job + events |
| B09 | P2 | studio UI | Fake-feeling params | Negative prompt + capability-driven modes |
| B10 | P3 | docs | Docs oversold features | AUDIT + ARCHITECTURE_v40 |
