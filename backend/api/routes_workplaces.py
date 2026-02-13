# -*- coding: utf-8 -*-
"""
api/routes_workplaces.py — GET /api/tab/workplaces
"""

import json
import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2
from config.constants import METHODS_RISK

router = APIRouter()
DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}

def _sf(v):
    return 0.0 if pd.isna(v) else float(v)


@router.get("/api/tab/workplaces")
async def get_workplaces(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Данные для вкладки Рабочие места."""
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

    if 'РМ' not in df_f.columns:
        return {"rm_data": [], "kpi": {}}

    rm_stats = df_f.groupby('РМ').agg(
        count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
    ).reset_index()
    rm_stats['dev'] = rm_stats['fact'] - rm_stats['plan']
    rm_stats = rm_stats[rm_stats['РМ'] != 'Н/Д']
    rm_stats = rm_stats.sort_values('dev', ascending=False)

    rm_data = []
    for _, r in rm_stats.iterrows():
        rm_data.append({
            "name": str(r['РМ']),
            "count": int(r['count']),
            "fact": _sf(r['fact']),
            "plan": _sf(r['plan']),
            "dev": _sf(r['dev'])
        })

    overrun_rm = int(len(rm_stats[rm_stats['dev'] > 0]))

    return {
        "rm_data": rm_data,
        "kpi": {
            "rm_count": len(rm_stats),
            "total_orders": int(rm_stats['count'].sum()),
            "total_fact": _sf(rm_stats['fact'].sum()),
            "overrun_count": overrun_rm,
        }
    }
