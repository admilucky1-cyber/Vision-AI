# Vision AI Data Lab v6.1.0

**Product:** Vision AI  
**Module:** Data Lab — master workspace for modern data work

## Capabilities

| Capability | Support |
|------------|---------|
| Multi-file upload | CSV, TSV, Excel (all sheets), PDF text, JSON |
| Data cleaning | Dedupe, NA handling, strip, rename, type inference, column keep/drop |
| Data management | Dataset registry, preview, merge |
| Data science profile | Nulls, uniques, min/max/mean/std, top values, memory |
| Retrieve specific data | Column select, filters (==, !=, >, <, contains, in, null), search, sort, pagination |
| Forecasting | Linear trend baseline + confidence band (fast Kaggle-style baseline) |
| Dashboard | KPIs, histograms, categorical bars, correlation matrix payload |

## API

- `POST /api/data-lab/upload` — multipart multiple files
- `GET  /api/data-lab/datasets`
- `GET  /api/data-lab/datasets/{id}/preview`
- `GET  /api/data-lab/datasets/{id}/profile`
- `GET  /api/data-lab/datasets/{id}/dashboard`
- `POST /api/data-lab/clean`
- `POST /api/data-lab/query`
- `POST /api/data-lab/forecast`
- `POST /api/data-lab/merge`

## UI

Open **`/data-lab.html`**

## Design intent

Built to handle real multi-file workflows (not single-file toys): Excel workbooks with many sheets, batch CSVs, PDF extracts, then clean → query → forecast → dashboard in one product surface under **Vision AI**.
