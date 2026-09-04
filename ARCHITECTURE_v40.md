# Architecture v4.0

## Chat (preserved)
LLM cascade on Railway — no GPU required.

## Studio
API `/api/studio` → registry + job state machine → Colab/Kaggle workers for heavy work.

## Models
Capability map per model. SVD-XT = I2V only.

## Storage
Drive A images · B video · C datasets. Compute downloads to local SSD.

## Jobs
queued → claimed → … → completed/failed with events. Resumable flag on train jobs.

## Workers
register (secret+URL) → heartbeat (existing only) → dispatch by capability (scheduler next).
