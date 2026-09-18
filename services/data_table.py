"""
Vision AI — DataTable helpers (Ustadam Data Science + Web skills applied)

Pure functions for filter / sort / search / paginate.
Use these from any service or route that returns tabular data.
No side effects. Easy to unit test.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Union


def _get_field(row: Any, key: str) -> Any:
    """Support dict rows and simple objects."""
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def search_rows(
    rows: Sequence[Any],
    query: str,
    fields: Sequence[str],
) -> List[Any]:
    """
    Case-insensitive search across the given fields.
    Returns a new list (original is not mutated).
    """
    q = (query or "").strip().lower()
    if not q:
        return list(rows)

    result = []
    for row in rows:
        for field in fields:
            val = _get_field(row, field)
            if val is not None and q in str(val).lower():
                result.append(row)
                break
    return result


def filter_rows(
    rows: Sequence[Any],
    filters: Dict[str, Any],
) -> List[Any]:
    """
    Exact or callable filters.
    filters = {"status": "active"} or {"status": lambda v: v in ("active", "pending")}
    """
    if not filters:
        return list(rows)

    result = []
    for row in rows:
        ok = True
        for key, expected in filters.items():
            actual = _get_field(row, key)
            if callable(expected):
                if not expected(actual):
                    ok = False
                    break
            else:
                if actual != expected:
                    ok = False
                    break
        if ok:
            result.append(row)
    return result


def sort_rows(
    rows: Sequence[Any],
    sort_by: Optional[str] = None,
    descending: bool = False,
) -> List[Any]:
    """Stable sort by a single field. None values go last."""
    if not sort_by:
        return list(rows)

    def key_fn(row: Any):
        val = _get_field(row, sort_by)
        # Push None to the end regardless of direction
        if val is None:
            return (1, "")
        return (0, val)

    return sorted(rows, key=key_fn, reverse=descending)


def paginate(
    rows: Sequence[Any],
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """
    Return a standard page payload.
    page is 1-based.
    """
    page = max(1, int(page or 1))
    page_size = max(1, min(200, int(page_size or 25)))
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    items = list(rows[start:end])

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "has_next": end < total,
        "has_prev": page > 1,
    }


def prepare_table(
    rows: Sequence[Any],
    *,
    query: str = "",
    search_fields: Sequence[str] = (),
    filters: Optional[Dict[str, Any]] = None,
    sort_by: Optional[str] = None,
    descending: bool = False,
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    """
    One-shot helper: search → filter → sort → paginate.
    Returns a clean payload ready for the frontend DataTable component.
    """
    working = list(rows)
    if query and search_fields:
        working = search_rows(working, query, search_fields)
    if filters:
        working = filter_rows(working, filters)
    working = sort_rows(working, sort_by=sort_by, descending=descending)
    return paginate(working, page=page, page_size=page_size)
