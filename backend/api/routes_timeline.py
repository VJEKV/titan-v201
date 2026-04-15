# -*- coding: utf-8 -*-
"""
api/routes_timeline.py — GET /api/tab/timeline
"""

import json
import pandas as pd
import numpy as np
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2
from utils.formatters import fmt_downtime
from config.constants import METHODS_RISK
from core.response_cache import cached_endpoint

router = APIRouter()

MONTH_SHORT = {1:'Янв',2:'Фев',3:'Мар',4:'Апр',5:'Май',6:'Июн',7:'Июл',8:'Авг',9:'Сен',10:'Окт',11:'Ноя',12:'Дек'}
MONTH_NAMES = {1:'Январь',2:'Февраль',3:'Март',4:'Апрель',5:'Май',6:'Июнь',7:'Июль',8:'Август',9:'Сентябрь',10:'Октябрь',11:'Ноябрь',12:'Декабрь'}
DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}

def _sf(v):
    return 0.0 if pd.isna(v) else float(v)


@router.get("/api/tab/timeline")
@cached_endpoint(ttl=300)
async def get_timeline(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Данные для вкладки Сроки."""
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
    agg = compute_aggregates(df_f)
    df_f, _ = apply_risk_scoring_v2(df_f, agg, thresh)

    # Определяем колонку с датой (каскадная дата)
    date_col = None
    for col in ['Дата_Месяц', 'Начало', 'Конец', 'Факт_Начало']:
        if col in df_f.columns and df_f[col].notna().any():
            date_col = col
            break

    if not date_col:
        return {"monthly_count": [], "duration": [], "cost": [], "downtime": [], "kpi": {}}

    df_m = df_f.copy()
    df_m['_month'] = df_m[date_col].dt.month
    df_m['_year'] = df_m[date_col].dt.year
    df_valid = df_m[df_m['_month'].notna()]

    # 1. Количество по месяцам
    monthly_count = []
    grp = df_valid.groupby(['_year', '_month']).size().reset_index(name='cnt')
    grp = grp.sort_values(['_year', '_month'])
    for _, r in grp.iterrows():
        monthly_count.append({
            "label": f"{MONTH_SHORT.get(int(r['_month']), '?')} {int(r['_year'])}",
            "count": int(r['cnt'])
        })

    # 2. Длительность по месяцам
    duration = []
    for dur_col, label in [('План_Длит', 'plan'), ('Факт_Длит', 'fact')]:
        if dur_col in df_valid.columns:
            d_grp = df_valid.groupby(['_year', '_month'])[dur_col].mean().reset_index()
            d_grp = d_grp.sort_values(['_year', '_month'])
            items = []
            for _, r in d_grp.iterrows():
                items.append({
                    "label": f"{MONTH_SHORT.get(int(r['_month']), '?')} {int(r['_year'])}",
                    "value": round(_sf(r[dur_col]), 1)
                })
            duration.append({"name": label, "data": items})

    # 3. Стоимость по месяцам
    cost = []
    for cost_col, label in [('Plan_N', 'plan'), ('Fact_N', 'fact')]:
        if cost_col in df_valid.columns:
            c_grp = df_valid.groupby(['_year', '_month'])[cost_col].mean().reset_index()
            c_grp = c_grp.sort_values(['_year', '_month'])
            items = []
            for _, r in c_grp.iterrows():
                items.append({
                    "label": f"{MONTH_SHORT.get(int(r['_month']), '?')} {int(r['_year'])}",
                    "value": round(_sf(r[cost_col]), 0)
                })
            cost.append({"name": label, "data": items})

    # 4. Простой по месяцам
    downtime = []
    if 'Простой_Сек' in df_valid.columns:
        dt_col = pd.to_numeric(df_valid['Простой_Сек'], errors='coerce').fillna(0)
        df_dt = df_valid.copy()
        df_dt['_dt'] = dt_col
        dt_grp = df_dt.groupby(['_year', '_month'])['_dt'].agg(['sum', 'mean']).reset_index()
        dt_grp = dt_grp.sort_values(['_year', '_month'])
        for _, r in dt_grp.iterrows():
            label = f"{MONTH_SHORT.get(int(r['_month']), '?')} {int(r['_year'])}"
            downtime.append({
                "label": label,
                "total_sec": _sf(r['sum']),
                "total_fmt": fmt_downtime(r['sum']),
                "avg_sec": _sf(r['mean']),
                "avg_fmt": fmt_downtime(r['mean']),
                "total_hours": round(_sf(r['sum']) / 3600, 1),
            })

    # KPI
    avg_dur = _sf(df_valid['Факт_Длит'].mean()) if 'Факт_Длит' in df_valid.columns else 0
    avg_cost = _sf(df_valid['Fact_N'].mean()) if 'Fact_N' in df_valid.columns else 0
    # KPI простоя
    total_downtime_sec = 0
    avg_downtime_sec = 0
    if 'Простой_Сек' in df_valid.columns:
        dt_all = pd.to_numeric(df_valid['Простой_Сек'], errors='coerce').fillna(0)
        total_downtime_sec = _sf(dt_all.sum())
        dt_pos = dt_all[dt_all > 0]
        avg_downtime_sec = _sf(dt_pos.mean()) if len(dt_pos) > 0 else 0

    return {
        "monthly_count": monthly_count,
        "duration": duration,
        "cost": cost,
        "downtime": downtime,
        "kpi": {
            "total_with_dates": len(df_valid),
            "avg_duration": round(avg_dur, 0),
            "avg_cost": round(avg_cost, 0),
            "total_downtime_fmt": fmt_downtime(total_downtime_sec),
            "avg_downtime_fmt": fmt_downtime(avg_downtime_sec),
        }
    }
