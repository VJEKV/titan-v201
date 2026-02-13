# -*- coding: utf-8 -*-
"""
api/routes_work_types.py — GET /api/tab/work-types
"""

import json
import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2
from config.constants import METHODS_RISK, ВНЕПЛАНОВЫЕ_ВИДЫ

router = APIRouter()
DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}
MONTH_SHORT = {1:'Янв',2:'Фев',3:'Мар',4:'Апр',5:'Май',6:'Июн',7:'Июл',8:'Авг',9:'Сен',10:'Окт',11:'Ноя',12:'Дек'}

def _sf(v):
    return 0.0 if pd.isna(v) else float(v)


@router.get("/api/tab/work-types")
async def get_work_types(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Данные для вкладки Виды работ."""
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

    # Статистика по видам
    vid_stats = df_f.groupby('Вид').agg(
        count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
    ).reset_index()
    vid_stats['dev'] = vid_stats['fact'] - vid_stats['plan']

    if 'Вид_Код' in df_f.columns:
        vid_codes = df_f.groupby('Вид')['Вид_Код'].first().to_dict()
        vid_stats['is_unplanned'] = vid_stats['Вид'].map(vid_codes).isin(ВНЕПЛАНОВЫЕ_ВИДЫ)
    else:
        vid_stats['is_unplanned'] = False

    types_data = []
    for _, r in vid_stats.sort_values('dev', ascending=False).iterrows():
        types_data.append({
            "name": str(r['Вид']),
            "count": int(r['count']),
            "fact": _sf(r['fact']),
            "plan": _sf(r['plan']),
            "dev": _sf(r['dev']),
            "is_unplanned": bool(r['is_unplanned'])
        })

    # По месяцам
    monthly = []
    date_col = None
    for col in ['Начало', 'Конец', 'Факт_Начало']:
        if col in df_f.columns and df_f[col].notna().any():
            date_col = col
            break

    if date_col:
        df_m = df_f.copy()
        df_m['_month'] = df_m[date_col].dt.month
        df_m['_year'] = df_m[date_col].dt.year
        df_valid = df_m[df_m['_month'].notna()]

        top_vids = df_valid['Вид'].value_counts().head(8).index.tolist()

        for vid in top_vids:
            df_vid = df_valid[df_valid['Вид'] == vid]
            grp = df_vid.groupby(['_year', '_month']).size().reset_index(name='cnt')
            grp = grp.sort_values(['_year', '_month'])
            items = []
            for _, r in grp.iterrows():
                items.append({
                    "label": f"{MONTH_SHORT.get(int(r['_month']), '?')} {int(r['_year'])}",
                    "count": int(r['cnt'])
                })
            monthly.append({"name": vid[:45], "data": items})

    # KPI
    total_orders = int(vid_stats['count'].sum())
    unplanned_count = int(vid_stats[vid_stats['is_unplanned']]['count'].sum())
    unpl_pct = unplanned_count / max(total_orders, 1) * 100

    return {
        "types_data": types_data,
        "monthly": monthly,
        "kpi": {
            "types_count": len(vid_stats),
            "total_orders": total_orders,
            "unplanned_count": unplanned_count,
            "unplanned_pct": round(unpl_pct, 1),
            "total_dev": _sf(vid_stats['dev'].sum()),
        }
    }
