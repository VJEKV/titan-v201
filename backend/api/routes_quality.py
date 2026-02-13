# -*- coding: utf-8 -*-
"""
api/routes_quality.py — GET /api/tab/quality
"""

import json
import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2
from config.constants import METHODS_RISK, FIELD_MAPPING, RENAMED_TO_ORIGINAL, EMPTY_VALUES

router = APIRouter()
DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}


def _is_empty(val) -> bool:
    """Проверка: является ли значение пустым."""
    if val is None:
        return True
    if pd.isna(val):
        return True
    if hasattr(val, 'year'):
        try:
            return val.year <= 1971
        except Exception:
            return True
    str_val = str(val).strip()
    return str_val in EMPTY_VALUES or len(str_val) == 0


def _find_columns_to_check(df_columns):
    """Найти колонки для проверки."""
    result = {}
    for col in df_columns:
        if col in FIELD_MAPPING:
            result[col] = FIELD_MAPPING[col]
        elif col in RENAMED_TO_ORIGINAL:
            original = RENAMED_TO_ORIGINAL[col]
            if original in FIELD_MAPPING:
                result[col] = FIELD_MAPPING[original]
    return result


@router.get("/api/tab/quality")
async def get_quality(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Данные для вкладки C4 Качество."""
    session = get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    df = session['df']
    try:
        f = json.loads(filters)
    except Exception:
        f = {}
    try:
        thresh = {**DEFAULT_THRESHOLDS, **json.loads(thresholds)}
    except Exception:
        thresh = DEFAULT_THRESHOLDS

    hierarchy = f.get('hierarchy', {})
    extra = {k: v for k, v in f.items() if k != 'hierarchy'}
    df_f = apply_hierarchy_filters(df, hierarchy)
    df_f = apply_extra_filters(df_f, extra)

    columns_map = _find_columns_to_check(df_f.columns.tolist())
    total_rows = len(df_f)

    if not columns_map:
        return {"fields": [], "kpi": {}}

    # Подсчёт пустых
    fields = []
    for col, display_name in columns_map.items():
        series = df_f[col]
        empty_cnt = sum(1 for val in series if _is_empty(val))
        pct = empty_cnt / total_rows * 100 if total_rows > 0 else 0
        fields.append({
            "code": col,
            "name": display_name,
            "empty": empty_cnt,
            "filled": total_rows - empty_cnt,
            "pct": round(pct, 1)
        })

    fields.sort(key=lambda x: x['empty'], reverse=True)

    total_empty = sum(f['empty'] for f in fields)
    total_cells = total_rows * len(columns_map)
    fill_rate = ((total_cells - total_empty) / total_cells * 100) if total_cells > 0 else 0
    problem_cols = len([f for f in fields if f['pct'] > 30])

    return {
        "fields": fields,
        "kpi": {
            "total_rows": total_rows,
            "total_fields": len(columns_map),
            "problem_cols": problem_cols,
            "fill_rate": round(fill_rate, 1),
        }
    }
