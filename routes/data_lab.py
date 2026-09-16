"""Vision AI Data Lab API — multi-file data science workspace."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from services.data_lab import get_engine

logger = logging.getLogger("vision-ai.data-lab-api")
router = APIRouter(prefix="/api/data-lab", tags=["Data Lab"])


class CleanRequest(BaseModel):
    dataset_id: str
    drop_duplicates: bool = False
    drop_na_rows: bool = False
    drop_na_cols: bool = False
    fill_na: Optional[str] = None
    strip_strings: bool = True
    standardize_colnames: bool = True
    drop_columns: Optional[List[str]] = None
    keep_columns: Optional[List[str]] = None
    rename_columns: Optional[Dict[str, str]] = None
    infer_types: bool = True


class QueryRequest(BaseModel):
    dataset_id: str
    columns: Optional[List[str]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    search: Optional[str] = None
    sort_by: Optional[str] = None
    ascending: bool = True
    limit: int = Field(100, ge=1, le=5000)
    offset: int = Field(0, ge=0)


class ForecastRequest(BaseModel):
    dataset_id: str
    column: str
    periods: int = Field(12, ge=1, le=365)
    date_column: Optional[str] = None


class MergeRequest(BaseModel):
    left_id: str
    right_id: str
    on: Optional[List[str]] = None
    how: str = "inner"


@router.get("/health")
def data_lab_health():
    return {"status": "ok", "module": "data-lab", "product": "Vision AI"}


@router.get("/datasets")
def list_datasets():
    return {"datasets": get_engine().list_datasets()}


@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "No files provided")
    batch = []
    for f in files:
        content = await f.read()
        batch.append((f.filename or "upload.bin", content))
    try:
        result = get_engine().ingest_multiple(batch)
        return result
    except Exception as e:
        logger.exception("upload failed")
        raise HTTPException(400, str(e)) from e


@router.get("/datasets/{ds_id}/preview")
def preview(ds_id: str, n: int = 50):
    try:
        return get_engine().preview(ds_id, n=n)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.get("/datasets/{ds_id}/profile")
def profile(ds_id: str):
    try:
        return get_engine().profile(ds_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/clean")
def clean(body: CleanRequest):
    try:
        return get_engine().clean(
            body.dataset_id,
            drop_duplicates=body.drop_duplicates,
            drop_na_rows=body.drop_na_rows,
            drop_na_cols=body.drop_na_cols,
            fill_na=body.fill_na,
            strip_strings=body.strip_strings,
            standardize_colnames=body.standardize_colnames,
            drop_columns=body.drop_columns,
            keep_columns=body.keep_columns,
            rename_columns=body.rename_columns,
            infer_types=body.infer_types,
        )
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/query")
def query(body: QueryRequest):
    try:
        return get_engine().query(
            body.dataset_id,
            columns=body.columns,
            filters=body.filters,
            search=body.search,
            sort_by=body.sort_by,
            ascending=body.ascending,
            limit=body.limit,
            offset=body.offset,
        )
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/forecast")
def forecast(body: ForecastRequest):
    try:
        return get_engine().forecast(
            body.dataset_id,
            body.column,
            periods=body.periods,
            date_column=body.date_column,
        )
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.get("/datasets/{ds_id}/dashboard")
def dashboard(ds_id: str):
    try:
        return get_engine().dashboard(ds_id)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/merge")
def merge(body: MergeRequest):
    try:
        return get_engine().merge(body.left_id, body.right_id, on=body.on, how=body.how)
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except Exception as e:
        raise HTTPException(400, str(e)) from e


class TrainRequest(BaseModel):
    dataset_id: str
    target: str
    features: Optional[List[str]] = None
    task: str = "auto"
    test_size: float = Field(0.2, ge=0.05, le=0.5)
    random_seed: int = 42
    min_rows: int = Field(3, ge=3, le=1000)
    max_train_rows: Optional[int] = Field(None, ge=100, le=2_000_000)


class PredictRequest(BaseModel):
    model_id: str
    rows: List[Dict[str, Any]]


@router.post("/train")
def train_model(body: TrainRequest):
    try:
        return get_engine().train(
            body.dataset_id,
            body.target,
            features=body.features,
            task=body.task,
            test_size=body.test_size,
            random_seed=body.random_seed,
            min_rows=body.min_rows,
            max_train_rows=body.max_train_rows,
        )
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@router.post("/predict")
def predict_model(body: PredictRequest):
    try:
        return get_engine().predict(body.model_id, body.rows)
    except KeyError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, str(e)) from e
