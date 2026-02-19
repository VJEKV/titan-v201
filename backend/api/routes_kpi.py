# -*- coding: utf-8 -*-
"""
api/routes_kpi.py — GET /api/kpi
"""

import json
import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2
from utils.formatters import fmt_short, fmt
from config.constants import METHODS_RISK, FIELD_MAPPING, RENAMED_TO_ORIGINAL, EMPTY_VALUES

router = APIRouter()

DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}


def _safe_float(val):
    """Безопасное преобразование в float для JSON."""
    if pd.isna(val) or val is None:
        return 0.0
    return float(val)


def _is_empty(val) -> bool:
    """Проверка: является ли значение пустым (аналог из routes_quality)."""
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


def _calc_fill_rate(df):
    """Расчёт fill_rate — та же формула что и в routes_quality."""
    columns_map = {}
    for col in df.columns:
        if col in FIELD_MAPPING:
            columns_map[col] = FIELD_MAPPING[col]
        elif col in RENAMED_TO_ORIGINAL:
            original = RENAMED_TO_ORIGINAL[col]
            if original in FIELD_MAPPING:
                columns_map[col] = FIELD_MAPPING[original]
    if not columns_map:
        return 0.0
    total_rows = len(df)
    total_empty = 0
    for col in columns_map:
        total_empty += sum(1 for val in df[col] if _is_empty(val))
    total_cells = total_rows * len(columns_map)
    if total_cells == 0:
        return 0.0
    return round(((total_cells - total_empty) / total_cells * 100), 1)


@router.get("/api/kpi")
async def get_kpi(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """KPI-блок (6 карточек + 3 макс-карточки + статистика по выгрузке)."""
    session = get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    df = session['df']

    try:
        f = json.loads(filters)
    except Exception:
        f = {}

    try:
        thresh = json.loads(thresholds)
        merged_thresholds = {**DEFAULT_THRESHOLDS, **thresh}
    except Exception:
        merged_thresholds = DEFAULT_THRESHOLDS

    # Применяем фильтры
    hierarchy = f.get('hierarchy', {})
    extra = {k: v for k, v in f.items() if k != 'hierarchy'}

    df_filtered = apply_hierarchy_filters(df, hierarchy)
    df_filtered = apply_extra_filters(df_filtered, extra)

    # Агрегаты и скоринг v2
    agg = compute_aggregates(df_filtered)
    df_scored, _ = apply_risk_scoring_v2(df_filtered, agg, merged_thresholds)

    total = len(df_scored)
    plan = _safe_float(df_scored['Plan_N'].sum())
    fact = _safe_float(df_scored['Fact_N'].sum())
    dev = fact - plan
    dev_pct = (dev / plan * 100) if plan != 0 else 0

    risk_orders = df_scored[df_scored['Risk_Sum'] > 0]
    risk_count = len(risk_orders)
    risk_pct = risk_count / max(total, 1) * 100

    # fill_rate — та же формула что на вкладке «Качество данных»
    completeness = _calc_fill_rate(df_scored)

    # Максимальные карточки
    max_fact_row = df_scored.loc[df_scored['Fact_N'].idxmax()] if total > 0 else None
    max_dev_idx = (df_scored['Fact_N'] - df_scored['Plan_N']).idxmax() if total > 0 else None
    max_dev_row = df_scored.loc[max_dev_idx] if max_dev_idx is not None else None
    max_risk_row = df_scored.loc[df_scored['Risk_Sum'].idxmax()] if total > 0 else None

    def _card(row, val_col):
        if row is None:
            return None
        return {
            "id": str(row.get('ID', '')),
            "text": str(row.get('Текст', ''))[:80],
            "value": _safe_float(row.get(val_col, 0))
        }

    # Статистика по выгрузке — уникальные значения
    def _nunique(col):
        if col in df_scored.columns:
            vals = df_scored[col].dropna().astype(str)
            vals = vals[~vals.isin(['Н/Д', 'nan', 'None', '', 'Не присвоено', '0'])]
            return int(vals.nunique())
        return 0

    stats = {
        "n_zavod": _nunique('ЗАВОД'),
        "n_eo": _nunique('EQUNR_Код') if 'EQUNR_Код' in df_scored.columns else _nunique('ЕО'),
        "n_ceh": _nunique('ЦЕХ'),
        "n_tm": _nunique('ТМ'),
        "n_users": _nunique('USER'),
    }

    return {
        "total": total,
        "plan": plan,
        "fact": fact,
        "dev": dev,
        "dev_pct": round(dev_pct, 1),
        "risk_count": risk_count,
        "risk_pct": round(risk_pct, 1),
        "completeness": round(completeness, 1),
        "max_fact": _card(max_fact_row, 'Fact_N'),
        "max_dev": _card(max_dev_row, 'Fact_N'),
        "max_risk": _card(max_risk_row, 'Risk_Sum'),
        "stats": stats,
        # Форматированные значения
        "plan_fmt": fmt_short(plan),
        "fact_fmt": fmt_short(fact),
        "dev_fmt": fmt_short(abs(dev)),
    }
