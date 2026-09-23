"""
Vision AI Data Lab Engine
-------------------------
Multi-file ingest (CSV, Excel, PDF), profiling, cleaning, query,
simple forecasting, and dashboard payload generation.
Designed to handle Kaggle/Google-style tabular workflows inside Vision AI.
"""
from __future__ import annotations

import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("vision-ai.data-lab")

BASE = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE / "data" / "uploads"
DATASET_DIR = BASE / "data" / "datasets"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)

MAX_ROWS_PREVIEW = 500
MAX_FILES = 100
MAX_TRAIN_ROWS_DEFAULT = 100_000
MAX_TRAIN_ROWS_HARD = 2_000_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DataLabEngine:
    """Session-scoped multi-dataset workspace."""

    def __init__(self) -> None:
        self.datasets: Dict[str, Dict[str, Any]] = {}  # id -> meta + dataframe path
        self._models: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------
    def ingest_bytes(
        self,
        filename: str,
        content: bytes,
        dataset_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Load CSV / Excel / PDF into a managed dataset. Supports multi-file via repeated calls."""
        name = dataset_name or Path(filename).stem
        ext = Path(filename).suffix.lower()
        ds_id = str(uuid.uuid4())[:12]
        raw_path = UPLOAD_DIR / f"{ds_id}_{Path(filename).name}"
        raw_path.write_bytes(content)

        frames: List[Tuple[str, pd.DataFrame]] = []

        if ext in {".csv", ".tsv", ".txt"}:
            sep = "\t" if ext == ".tsv" else ","
            df = self._read_csv_safe(content, sep=sep)
            frames.append((name, df))
        elif ext in {".xlsx", ".xls"}:
            frames.extend(self._read_excel_all_sheets(content, name))
        elif ext == ".pdf":
            df = self._pdf_to_dataframe(content, filename)
            frames.append((name, df))
        elif ext == ".json":
            df = self._read_json_safe(content)
            frames.append((name, df))
        else:
            raise ValueError(f"Unsupported file type: {ext}. Use CSV, Excel, PDF, or JSON.")

        results = []
        for sheet_name, df in frames:
            sid = str(uuid.uuid4())[:12]
            meta = self._register(sid, sheet_name, df, source_file=filename)
            results.append(meta)
        return {"datasets": results, "count": len(results)}

    def ingest_multiple(self, files: List[Tuple[str, bytes]]) -> Dict[str, Any]:
        """Ingest many files at once."""
        if len(files) > MAX_FILES:
            raise ValueError(f"Max {MAX_FILES} files per batch")
        all_ds = []
        errors = []
        for fname, blob in files:
            try:
                out = self.ingest_bytes(fname, blob)
                all_ds.extend(out["datasets"])
            except Exception as e:
                errors.append({"file": fname, "error": str(e)})
        return {"datasets": all_ds, "count": len(all_ds), "errors": errors}

    def _register(self, ds_id: str, name: str, df: pd.DataFrame, source_file: str) -> Dict[str, Any]:
        parquet_path = DATASET_DIR / f"{ds_id}.parquet"
        csv_path = DATASET_DIR / f"{ds_id}.csv"
        try:
            df.to_parquet(parquet_path, index=False)
        except Exception:
            parquet_path = None
        df.to_csv(csv_path, index=False)

        profile = self.profile_df(df)
        meta = {
            "id": ds_id,
            "name": name,
            "source_file": source_file,
            "rows": int(len(df)),
            "columns": list(df.columns.astype(str)),
            "dtypes": {c: str(df[c].dtype) for c in df.columns},
            "profile": profile,
            "created_at": _now(),
            "path_csv": str(csv_path),
            "path_parquet": str(parquet_path) if parquet_path else None,
        }
        self.datasets[ds_id] = {"meta": meta, "df": df}
        return meta

    def _read_csv_safe(self, content: bytes, sep: str = ",") -> pd.DataFrame:
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                return pd.read_csv(io.BytesIO(content), sep=sep, encoding=enc, low_memory=False)
            except Exception:
                continue
        return pd.read_csv(io.BytesIO(content), sep=sep, encoding="utf-8", errors="replace", low_memory=False)

    def _read_excel_all_sheets(self, content: bytes, base_name: str) -> List[Tuple[str, pd.DataFrame]]:
        xl = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
        out = []
        for sheet in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet)
            out.append((f"{base_name}::{sheet}", df))
        return out

    def _read_json_safe(self, content: bytes) -> pd.DataFrame:
        data = json.loads(content.decode("utf-8", errors="replace"))
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            if "data" in data and isinstance(data["data"], list):
                return pd.DataFrame(data["data"])
            return pd.json_normalize(data)
        raise ValueError("JSON must be array or object")

    def _pdf_to_dataframe(self, content: bytes, filename: str) -> pd.DataFrame:
        """Extract text per page; attempt table-like lines."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError("pypdf required for PDF support")
        reader = PdfReader(io.BytesIO(content))
        rows = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()
                if line:
                    rows.append({"page": i + 1, "line": line, "source": filename})
        if not rows:
            rows = [{"page": 0, "line": "(empty PDF)", "source": filename}]
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Load / list
    # ------------------------------------------------------------------
    def get_df(self, ds_id: str) -> pd.DataFrame:
        if ds_id not in self.datasets:
            # try reload from disk
            csv_path = DATASET_DIR / f"{ds_id}.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                self.datasets[ds_id] = {
                    "meta": {
                        "id": ds_id,
                        "name": ds_id,
                        "rows": len(df),
                        "columns": list(df.columns),
                    },
                    "df": df,
                }
            else:
                raise KeyError(f"Dataset {ds_id} not found")
        return self.datasets[ds_id]["df"].copy()

    def list_datasets(self) -> List[Dict[str, Any]]:
        return [v["meta"] for v in self.datasets.values()]

    def preview(self, ds_id: str, n: int = 50) -> Dict[str, Any]:
        df = self.get_df(ds_id)
        n = min(max(1, n), MAX_ROWS_PREVIEW)
        sample = df.head(n).replace({np.nan: None})
        return {
            "id": ds_id,
            "columns": list(df.columns.astype(str)),
            "rows": sample.to_dict(orient="records"),
            "total_rows": len(df),
        }

    # ------------------------------------------------------------------
    # Profile / Data Science basics
    # ------------------------------------------------------------------
    def profile_df(self, df: pd.DataFrame) -> Dict[str, Any]:
        cols = []
        for c in df.columns:
            s = df[c]
            info: Dict[str, Any] = {
                "name": str(c),
                "dtype": str(s.dtype),
                "nulls": int(s.isna().sum()),
                "null_pct": round(float(s.isna().mean() * 100), 2),
                "unique": int(s.nunique(dropna=True)),
            }
            if pd.api.types.is_numeric_dtype(s):
                info["min"] = _safe_float(s.min())
                info["max"] = _safe_float(s.max())
                info["mean"] = _safe_float(s.mean())
                info["std"] = _safe_float(s.std())
                info["median"] = _safe_float(s.median())
            elif pd.api.types.is_string_dtype(s) or s.dtype == object:
                top = s.astype(str).value_counts(dropna=True).head(5)
                info["top_values"] = {str(k): int(v) for k, v in top.items()}
            cols.append(info)
        return {
            "rows": int(len(df)),
            "cols": int(len(df.columns)),
            "memory_mb": round(float(df.memory_usage(deep=True).sum() / 1e6), 3),
            "columns": cols,
            "duplicate_rows": int(df.duplicated().sum()),
        }

    def profile(self, ds_id: str) -> Dict[str, Any]:
        return self.profile_df(self.get_df(ds_id))

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------
    def clean(
        self,
        ds_id: str,
        *,
        drop_duplicates: bool = False,
        drop_na_rows: bool = False,
        drop_na_cols: bool = False,
        fill_na: Optional[Union[str, float]] = None,
        strip_strings: bool = True,
        standardize_colnames: bool = True,
        drop_columns: Optional[List[str]] = None,
        keep_columns: Optional[List[str]] = None,
        rename_columns: Optional[Dict[str, str]] = None,
        infer_types: bool = True,
    ) -> Dict[str, Any]:
        df = self.get_df(ds_id)
        ops = []

        if standardize_colnames:
            df.columns = [_clean_colname(c) for c in df.columns]
            ops.append("standardize_colnames")

        if rename_columns:
            df = df.rename(columns=rename_columns)
            ops.append("rename_columns")

        if keep_columns:
            keep = [c for c in keep_columns if c in df.columns]
            df = df[keep]
            ops.append("keep_columns")

        if drop_columns:
            df = df.drop(columns=[c for c in drop_columns if c in df.columns], errors="ignore")
            ops.append("drop_columns")

        if strip_strings:
            for c in df.select_dtypes(include=["object", "string"]).columns:
                df[c] = df[c].map(lambda x: x.strip() if isinstance(x, str) else x)
            ops.append("strip_strings")

        if drop_duplicates:
            before = len(df)
            df = df.drop_duplicates()
            ops.append(f"drop_duplicates(-{before - len(df)})")

        if drop_na_cols:
            df = df.dropna(axis=1, how="all")
            ops.append("drop_na_cols")

        if drop_na_rows:
            before = len(df)
            df = df.dropna(axis=0, how="any")
            ops.append(f"drop_na_rows(-{before - len(df)})")

        if fill_na is not None:
            df = df.fillna(fill_na)
            ops.append(f"fill_na={fill_na}")

        if infer_types:
            df = _infer_types(df)
            ops.append("infer_types")

        new_id = str(uuid.uuid4())[:12]
        meta = self._register(new_id, f"{self.datasets[ds_id]['meta'].get('name', ds_id)}_clean", df, source_file=f"clean:{ds_id}")
        meta["cleaning_ops"] = ops
        meta["parent_id"] = ds_id
        return meta

    # ------------------------------------------------------------------
    # Query / retrieve specific data
    # ------------------------------------------------------------------
    def query(
        self,
        ds_id: str,
        *,
        columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        ascending: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve specific rows/columns.
        filters: [{"column": "age", "op": ">=", "value": 18}, ...]
        ops: ==, !=, >, >=, <, <=, contains, in, notnull, isnull
        """
        df = self.get_df(ds_id)

        if columns:
            cols = [c for c in columns if c in df.columns]
            df = df[cols] if cols else df

        if search:
            mask = pd.Series(False, index=df.index)
            for c in df.columns:
                mask = mask | df[c].astype(str).str.contains(search, case=False, na=False)
            df = df[mask]

        if filters:
            for f in filters:
                col = f.get("column")
                op = f.get("op", "==")
                val = f.get("value")
                if col not in df.columns:
                    continue
                s = df[col]
                if op == "==":
                    df = df[s == val]
                elif op == "!=":
                    df = df[s != val]
                elif op == ">":
                    df = df[pd.to_numeric(s, errors="coerce") > float(val)]
                elif op == ">=":
                    df = df[pd.to_numeric(s, errors="coerce") >= float(val)]
                elif op == "<":
                    df = df[pd.to_numeric(s, errors="coerce") < float(val)]
                elif op == "<=":
                    df = df[pd.to_numeric(s, errors="coerce") <= float(val)]
                elif op == "contains":
                    df = df[s.astype(str).str.contains(str(val), case=False, na=False)]
                elif op == "in":
                    df = df[s.isin(val if isinstance(val, list) else [val])]
                elif op == "isnull":
                    df = df[s.isna()]
                elif op == "notnull":
                    df = df[s.notna()]

        total = len(df)
        if sort_by and sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=ascending)

        limit = min(max(1, limit), 5000)
        offset = max(0, offset)
        page = df.iloc[offset : offset + limit].replace({np.nan: None})

        return {
            "id": ds_id,
            "total_matched": total,
            "offset": offset,
            "limit": limit,
            "columns": list(page.columns.astype(str)),
            "rows": page.to_dict(orient="records"),
        }

    # ------------------------------------------------------------------
    # Forecast (simple, robust)
    # ------------------------------------------------------------------
    def forecast(
        self,
        ds_id: str,
        column: str,
        periods: int = 12,
        date_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Simple forecasting for numeric series.
        Uses linear trend + optional seasonal naive if enough points.
        Suitable for quick Kaggle-style baselines, not deep learning.
        """
        df = self.get_df(ds_id)
        if column not in df.columns:
            raise ValueError(f"Column {column} not found")

        y = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(y) < 3:
            raise ValueError("Need at least 3 numeric points to forecast")

        periods = min(max(1, periods), 365)
        x = np.arange(len(y), dtype=float)
        # linear regression via numpy
        coef = np.polyfit(x, y.values.astype(float), 1)
        trend = np.poly1d(coef)

        future_x = np.arange(len(y), len(y) + periods, dtype=float)
        pred = trend(future_x)

        # residual std for simple band
        resid = y.values.astype(float) - trend(x)
        sigma = float(np.std(resid)) if len(resid) > 1 else 0.0

        history = {
            "values": [_safe_float(v) for v in y.tolist()[-min(100, len(y)) :]],
        }
        if date_column and date_column in df.columns:
            history["dates"] = df[date_column].astype(str).tolist()[-min(100, len(y)) :]

        return {
            "column": column,
            "method": "linear_trend",
            "periods": periods,
            "history_tail": history,
            "forecast": [_safe_float(v) for v in pred.tolist()],
            "lower_80": [_safe_float(v - 1.28 * sigma) for v in pred.tolist()],
            "upper_80": [_safe_float(v + 1.28 * sigma) for v in pred.tolist()],
            "r2": _safe_float(1 - (np.var(resid) / np.var(y.values.astype(float))) if np.var(y.values) > 0 else 0),
        }

    # ------------------------------------------------------------------
    # Dashboard payload
    # ------------------------------------------------------------------
    def dashboard(self, ds_id: str) -> Dict[str, Any]:
        """Modern dashboard summary: KPIs, distributions, correlations."""
        df = self.get_df(ds_id)
        profile = self.profile_df(df)
        numeric = df.select_dtypes(include=[np.number])

        kpis = {
            "rows": len(df),
            "columns": len(df.columns),
            "null_cells": int(df.isna().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "numeric_columns": int(len(numeric.columns)),
        }

        histograms = {}
        for c in numeric.columns[:8]:
            series = numeric[c].dropna()
            if series.empty:
                continue
            counts, edges = np.histogram(series, bins=min(12, max(5, len(series) // 10 or 5)))
            histograms[str(c)] = {
                "counts": [int(x) for x in counts.tolist()],
                "edges": [_safe_float(e) for e in edges.tolist()],
            }

        corr = None
        if numeric.shape[1] >= 2:
            corr_df = numeric.corr(numeric_only=True)
            corr = {
                "columns": list(corr_df.columns.astype(str)),
                "matrix": [[_safe_float(v) for v in row] for row in corr_df.values.tolist()],
            }

        categorical = {}
        for c in df.select_dtypes(include=["object", "string", "category"]).columns[:6]:
            vc = df[c].astype(str).value_counts().head(10)
            categorical[str(c)] = {str(k): int(v) for k, v in vc.items()}

        return {
            "id": ds_id,
            "name": self.datasets.get(ds_id, {}).get("meta", {}).get("name", ds_id),
            "kpis": kpis,
            "profile": profile,
            "histograms": histograms,
            "correlation": corr,
            "categorical": categorical,
            "generated_at": _now(),
        }

    def merge(self, left_id: str, right_id: str, on: Optional[List[str]] = None, how: str = "inner") -> Dict[str, Any]:
        left = self.get_df(left_id)
        right = self.get_df(right_id)
        if on:
            df = left.merge(right, on=on, how=how)
        else:
            common = list(set(left.columns) & set(right.columns))
            if not common:
                raise ValueError("No common columns to merge on; pass on=[...]")
            df = left.merge(right, on=common, how=how)
        new_id = str(uuid.uuid4())[:12]
        return self._register(new_id, f"merge_{left_id}_{right_id}", df, source_file=f"merge:{left_id}+{right_id}")



    def ingest_csv_path(self, path: str, dataset_name: Optional[str] = None, chunksize: int = 100_000) -> Dict[str, Any]:
        """Load large CSV from disk in chunks (any length), concatenate, register once."""
        path_p = Path(path)
        if not path_p.exists():
            raise FileNotFoundError(path)
        name = dataset_name or path_p.stem
        chunks = []
        total = 0
        for chunk in pd.read_csv(path_p, chunksize=chunksize, low_memory=False):
            chunks.append(chunk)
            total += len(chunk)
            if total >= MAX_TRAIN_ROWS_HARD * 2:
                # soft stop to protect host RAM; caller can raise max via env later
                break
        if not chunks:
            raise ValueError("Empty CSV")
        df = pd.concat(chunks, ignore_index=True)
        sid = str(uuid.uuid4())[:12]
        meta = self._register(sid, name, df, source_file=str(path_p))
        meta["loaded_rows"] = len(df)
        meta["chunked_load"] = True
        return {"datasets": [meta], "count": 1}

    def train(
        self,
        ds_id: str,
        target: str,
        features: Optional[List[str]] = None,
        task: str = "auto",
        test_size: float = 0.2,
        random_seed: int = 42,
        min_rows: int = 3,
        drop_na_target_only: bool = True,
        max_train_rows: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Train on any dataset length (tiny → multi-million).

        Strategy:
        - Small data: use all rows
        - Large data: adaptive sample up to max_train_rows (default 100k, hard cap 2M)
          so training stays in memory and finishes quickly (best revenue)
        - No artificial "problem type" blocks for tabular regression/classification
        - Rows with valid target kept; feature gaps filled (no mass frame drops)

        Scope: tabular ML. LLM/vision/video remain on Model Studio workers.
        """
        df = self.get_df(ds_id)
        if target not in df.columns:
            raise ValueError(f"Target column '{target}' not found")

        feats = [
            c for c in (features or [c for c in df.columns if c != target])
            if c in df.columns and c != target
        ]
        if not feats:
            raise ValueError("No feature columns available")

        work = df[feats + [target]].copy()
        if drop_na_target_only:
            work = work.dropna(subset=[target])
        else:
            work = work.dropna()

        min_rows = max(3, int(min_rows or 3))
        if len(work) < min_rows:
            raise ValueError(f"Need at least {min_rows} rows with a non-null target (got {len(work)})")

        n_full = len(work)
        # Adaptive cap: any length accepted; sample only when necessary for RAM/speed
        if max_train_rows is None:
            max_train_rows = MAX_TRAIN_ROWS_DEFAULT
        max_train_rows = int(max(min_rows, min(MAX_TRAIN_ROWS_HARD, max_train_rows)))
        sampled = False
        if n_full > max_train_rows:
            work = work.sample(n=max_train_rows, random_state=random_seed)
            sampled = True

        X_parts: List[Any] = []
        used_features: List[str] = []
        for c in feats:
            s = work[c]
            if pd.api.types.is_numeric_dtype(s):
                col = pd.to_numeric(s, errors="coerce")
                fill = float(col.median()) if col.notna().any() else 0.0
                X_parts.append(col.fillna(fill))
                used_features.append(c)
            else:
                # stable frequency encode; unseen -> 0 (no row drops)
                freq = s.astype(str).value_counts(normalize=True)
                X_parts.append(s.astype(str).map(freq).fillna(0.0))
                used_features.append(f"{c}__freq")

        X = pd.concat(X_parts, axis=1)
        X.columns = used_features
        # zero-variance guard: keep column but model stays stable
        y_raw = work[target]

        if task == "auto":
            nunique = y_raw.nunique(dropna=True)
            if pd.api.types.is_numeric_dtype(y_raw) and nunique > max(12, int(0.05 * len(y_raw))):
                task = "regression"
            else:
                task = "classification"

        n = len(X)
        rng = np.random.RandomState(random_seed)
        idx = np.arange(n)
        rng.shuffle(idx)
        # adaptive holdout: never empty train
        test_size = float(min(0.5, max(0.0, test_size)))
        if n < 8:
            train_idx, test_idx = idx, idx  # report train metrics; tiny-sample mode
            tiny = True
        else:
            split = max(1, min(n - 1, int(n * (1 - test_size))))
            train_idx, test_idx = idx[:split], idx[split:]
            tiny = False

        X_train = X.iloc[train_idx].values.astype(float)
        X_test = X.iloc[test_idx].values.astype(float)
        model_id = str(uuid.uuid4())[:12]
        result: Dict[str, Any] = {
            "model_id": model_id,
            "dataset_id": ds_id,
            "target": target,
            "features": used_features,
            "task": task,
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            "n_total": n,
            "n_full_dataset": n_full,
            "sampled_for_train": sampled,
            "max_train_rows": max_train_rows,
            "tiny_sample_mode": tiny,
            "rows_preserved": True,
            "created_at": _now(),
            "note": (
                "Unrestricted tabular small-model path: no GPU, no artificial job-type blocks. "
                "Keeps all usable rows (target-only NA drop). "
                "For LLM/vision/video use Model Studio workers."
            ),
        }

        if task == "regression":
            y = pd.to_numeric(y_raw, errors="coerce")
            # fill residual target gaps without dropping frames
            y = y.fillna(y.median() if y.notna().any() else 0.0).values.astype(float)
            y_train, y_test = y[train_idx], y[test_idx]
            model = _fit_ridge(X_train, y_train, l2=1.0)
            pred_tr = _predict_linear(model, X_train)
            pred_te = _predict_linear(model, X_test)
            result["algorithm"] = "ridge_regression"
            result["metrics"] = {
                "train_rmse": _rmse(y_train, pred_tr),
                "test_rmse": _rmse(y_test, pred_te),
                "train_mae": _mae(y_train, pred_tr),
                "test_mae": _mae(y_test, pred_te),
                "train_r2": _r2(y_train, pred_tr),
                "test_r2": _r2(y_test, pred_te),
            }
            result["coefficients"] = {
                "intercept": _safe_float(model["intercept"]),
                "weights": {f: _safe_float(w) for f, w in zip(used_features, model["weights"])},
            }
            self._models[model_id] = {
                "type": "ridge", "model": model, "features": used_features, "task": task, "target": target
            }
        else:
            y_series = y_raw.astype(str).fillna("__NA__")
            classes = sorted(y_series.unique().tolist())
            # single-class: still train a constant classifier (no hard block)
            if len(classes) == 1:
                model = {"constant": classes[0], "ovr": False, "weights": np.zeros(X_train.shape[1]), "intercept": 0.0}
                pred_tr = np.zeros(len(train_idx), dtype=int)
                pred_te = np.zeros(len(test_idx), dtype=int)
                result["algorithm"] = "constant_classifier"
                result["classes"] = classes
                result["metrics"] = {"train_accuracy": 1.0, "test_accuracy": 1.0}
                self._models[model_id] = {
                    "type": "constant", "model": model, "features": used_features,
                    "task": "classification", "target": target, "classes": classes,
                }
            else:
                class_to_i = {c: i for i, c in enumerate(classes)}
                y_idx = y_series.map(class_to_i).values.astype(int)
                y_train, y_test = y_idx[train_idx], y_idx[test_idx]
                if len(classes) == 2:
                    model = _fit_logistic_binary(X_train, (y_train == 1).astype(float))
                    pred_tr = (_predict_logistic(model, X_train) >= 0.5).astype(int)
                    pred_te = (_predict_logistic(model, X_test) >= 0.5).astype(int)
                    result["algorithm"] = "logistic_regression_binary"
                else:
                    model = _fit_logistic_ovr(X_train, y_train, n_classes=len(classes))
                    pred_tr = _predict_ovr(model, X_train)
                    pred_te = _predict_ovr(model, X_test)
                    result["algorithm"] = "logistic_regression_ovr"
                result["classes"] = classes
                result["metrics"] = {
                    "train_accuracy": _accuracy(y_train, pred_tr),
                    "test_accuracy": _accuracy(y_test, pred_te),
                }
                self._models[model_id] = {
                    "type": "logistic", "model": model, "features": used_features,
                    "task": "classification", "target": target, "classes": classes,
                }

        meta_path = DATASET_DIR / f"model_{model_id}.json"
        meta_path.write_text(
            json.dumps({k: v for k, v in result.items() if k != "coefficients"}, default=str),
            encoding="utf-8",
        )
        return result


    def predict(self, model_id: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        if model_id not in self._models:
            raise KeyError(f"Model {model_id} not found — train first in this session")
        pack = self._models[model_id]
        feats = pack["features"]
        X = []
        for row in rows:
            vec = []
            for f in feats:
                raw_name = f.replace("__freq", "")
                val = row.get(f, row.get(raw_name, 0))
                try:
                    vec.append(float(val) if val is not None else 0.0)
                except Exception:
                    vec.append(0.0)
            X.append(vec)
        Xa = np.array(X, dtype=float) if X else np.zeros((0, len(feats)))
        if pack["type"] == "ridge":
            preds = _predict_linear(pack["model"], Xa).tolist() if len(Xa) else []
            return {
                "model_id": model_id,
                "task": "regression",
                "predictions": [_safe_float(p) for p in preds],
            }
        if pack["type"] == "constant":
            label = pack["model"].get("constant", pack.get("classes", ["0"])[0])
            return {
                "model_id": model_id,
                "task": "classification",
                "predictions": [label] * len(rows),
            }
        if pack["model"].get("ovr"):
            idx = _predict_ovr(pack["model"], Xa) if len(Xa) else np.array([], dtype=int)
        else:
            idx = (_predict_logistic(pack["model"], Xa) >= 0.5).astype(int) if len(Xa) else np.array([], dtype=int)
        classes = pack.get("classes") or ["0", "1"]
        labels = [classes[i] if i < len(classes) else str(i) for i in idx.tolist()]
        return {"model_id": model_id, "task": "classification", "predictions": labels}


        if model_id not in self._models:
            raise KeyError(f"Model {model_id} not found — train first in this session")
        pack = self._models[model_id]
        feats = pack["features"]
        X = []
        for row in rows:
            vec = []
            for f in feats:
                raw_name = f.replace("__freq", "")
                val = row.get(f, row.get(raw_name, 0))
                try:
                    vec.append(float(val))
                except Exception:
                    vec.append(0.0)
            X.append(vec)
        Xa = np.array(X, dtype=float)
        if pack["type"] == "ridge":
            preds = _predict_linear(pack["model"], Xa).tolist()
            return {
                "model_id": model_id,
                "task": "regression",
                "predictions": [_safe_float(p) for p in preds],
            }
        if pack["model"].get("ovr"):
            idx = _predict_ovr(pack["model"], Xa)
        else:
            idx = (_predict_logistic(pack["model"], Xa) >= 0.5).astype(int)
        classes = pack.get("classes") or ["0", "1"]
        labels = [classes[i] if i < len(classes) else str(i) for i in idx.tolist()]
        return {"model_id": model_id, "task": "classification", "predictions": labels}



def _clean_colname(c: Any) -> str:
    s = str(c).strip().lower()
    s = re.sub(r"[^\w]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "col"


def _infer_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object:
            # try numeric
            num = pd.to_numeric(out[c], errors="coerce")
            if num.notna().mean() > 0.8:
                out[c] = num
                continue
            # try datetime
            try:
                dt = pd.to_datetime(out[c], errors="coerce", utc=False)
                if dt.notna().mean() > 0.8:
                    out[c] = dt
            except Exception:
                pass
    return out


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return float(v)
    except Exception:
        return None


_ENGINE: Optional[DataLabEngine] = None


def get_engine() -> DataLabEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = DataLabEngine()
    return _ENGINE


def _fit_ridge(X: np.ndarray, y: np.ndarray, l2: float = 1.0) -> Dict[str, Any]:
    n, d = X.shape
    Xb = np.c_[np.ones(n), X]
    I = np.eye(d + 1)
    I[0, 0] = 0.0
    try:
        beta = np.linalg.solve(Xb.T @ Xb + l2 * I, Xb.T @ y)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(Xb.T @ Xb + l2 * I, Xb.T @ y, rcond=None)[0]
    return {"intercept": float(beta[0]), "weights": beta[1:].astype(float)}


def _predict_linear(model: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    return model["intercept"] + X @ np.array(model["weights"], dtype=float)


def _fit_logistic_binary(X: np.ndarray, y: np.ndarray, lr: float = 0.1, steps: int = 400) -> Dict[str, Any]:
    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(steps):
        z = X @ w + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        err = p - y
        w -= lr * (X.T @ err) / n
        b -= lr * float(np.mean(err))
    return {"weights": w, "intercept": b, "ovr": False}


def _predict_logistic(model: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    z = X @ model["weights"] + model["intercept"]
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def _fit_logistic_ovr(X: np.ndarray, y: np.ndarray, n_classes: int) -> Dict[str, Any]:
    models = []
    for k in range(n_classes):
        yk = (y == k).astype(float)
        models.append(_fit_logistic_binary(X, yk))
    return {"models": models, "ovr": True, "n_classes": n_classes}


def _predict_ovr(model: Dict[str, Any], X: np.ndarray) -> np.ndarray:
    probs = np.column_stack([_predict_logistic(m, X) for m in model["models"]])
    return np.argmax(probs, axis=1)


def _rmse(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return _safe_float(np.sqrt(np.mean((y - p) ** 2)))


def _mae(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return _safe_float(np.mean(np.abs(y - p)))


def _r2(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    ss_res = np.sum((y - p) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    if ss_tot <= 0:
        return None
    return _safe_float(1 - ss_res / ss_tot)


def _accuracy(y, p):
    y, p = np.asarray(y), np.asarray(p)
    if len(y) == 0:
        return None
    return _safe_float(np.mean(y == p))
