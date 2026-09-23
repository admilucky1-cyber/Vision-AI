# Vision AI v6.2.1 — Readiness Check

**Product:** Vision AI  
**Version:** 6.2.1  
**Status:** READY for Data Lab + small-data training

## Backend
| Item | Status |
|------|--------|
| VERSION file | 6.2.1 |
| main.py identity | Vision AI v6.2.1 |
| Data Lab router mounted | `/api/data-lab` |
| Explicit page route | `/data-lab` + `/data-lab.html` |
| Catch-all HTML serve | yes |

## API endpoints
- GET  /api/data-lab/health
- GET  /api/data-lab/datasets
- POST /api/data-lab/upload (multi-file)
- GET  /api/data-lab/datasets/{id}/preview|profile|dashboard
- POST /api/data-lab/clean|query|forecast|merge|train|predict

## Engine (verified E2E)
ingest, multi-ingest, clean, query, forecast, dashboard, merge, train, predict — PASS

## Frontend
| Item | Status |
|------|--------|
| data-lab.html | present |
| Upload multi-file | yes |
| Clean / Query / Forecast / Dashboard | yes |
| Train + Predict | yes |
| Version meta | 6.2.1 |

## Dependencies (requirements.txt)
pandas, numpy, openpyxl, PyPDF2 listed

## Not in this scope
- Full sklearn/AutoML suite (by design: lightweight small-data models)
- Persistent model store across process restarts (session models)
- FastAPI not installed in check environment (runtime deploy must have it)

## Run
```bash
pip install -r requirements.txt
python run.py   # or uvicorn main:app
# open http://localhost:PORT/data-lab.html
```
