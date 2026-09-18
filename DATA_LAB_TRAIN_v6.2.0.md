# Vision AI Data Lab — Small-Data Model Training v6.2.0

**Product:** Vision AI  
**Goal:** Train useful models on small datasets at minimal cost (best revenue).

## Why this design
- No GPU required
- Seconds to train on typical business/Kaggle-small tables
- Strong baselines: Ridge regression + Logistic (binary / one-vs-rest)
- Automatic feature prep: numeric + frequency encoding for categoricals
- Holdout metrics reported (RMSE/MAE/R² or accuracy)

## API
- `POST /api/data-lab/train` `{ dataset_id, target, features?, task: auto|regression|classification }`
- `POST /api/data-lab/predict` `{ model_id, rows: [{...}] }`

## UI
`/data-lab.html` → set target column → Train model

## When to use
- Tables from tens to ~50k rows
- Fast revenue features: churn, price, lead score, demand baseline
- Not a replacement for large-scale deep learning (use Model Studio / Colab workers for that)
