# Vision AI — Any-Length Dataset Training v6.3.0

## Goal
Model training accepts **any dataset length** from 3 rows to multi-million rows.

## How it works
| Size | Behavior |
|------|----------|
| 3 – 100k rows | Train on **all** rows (default) |
| > 100k rows | Adaptive **sample** up to `max_train_rows` (default 100,000) |
| Absolute safety cap | 2,000,000 rows in one train call (host RAM protection) |

Override with API: `"max_train_rows": 500000`

## Large file load
`ingest_csv_path(path, chunksize=100000)` loads big CSVs in chunks without one-shot memory spikes.

## No false claims
- Handles **any length of tabular problem/dataset** within RAM-safe caps
- Not unlimited GPU deep learning on infinite data
- Metrics always returned; `sampled_for_train` and `n_full_dataset` are explicit

## API
```json
POST /api/data-lab/train
{
  "dataset_id": "...",
  "target": "label",
  "task": "auto",
  "max_train_rows": 200000
}
```
