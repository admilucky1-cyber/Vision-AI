# Vision AI Small-Model Policy v6.2.1

## What “no restriction” means here
Within **tabular machine learning jobs**, the small-model trainer:
- Does **not** block legitimate regression/classification work
- Does **not** drop feature rows except null targets (configurable)
- Accepts very small samples (from 3 rows)
- Handles single-class data with a constant classifier (no hard fail)
- Runs on CPU only — best cost/revenue for small tables

## What it does **not** claim
It is **not** an unrestricted AGI or a replacement for:
- Large language models
- Video/frame pipelines
- GPU deep learning at Kaggle/Google scale

Those remain on **Model Studio / Colab workers**.

## “No frame drops”
- Training keeps all rows that have a valid target
- Feature NA filled (median / frequency) instead of dropping rows
- Predict accepts partial feature dicts (missing → 0)

## “No allegations”
- No fabricated capability claims beyond tabular baselines
- Metrics always returned so quality is measurable
