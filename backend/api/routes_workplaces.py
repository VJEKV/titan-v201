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


def _get_df(session_id, filters_str, thresholds_str):
    """Получить отфильтрованный DataFrame."""
    session = get_session(session_id)
    if not session:
        return None
    df = session['df']
    try:
        f = json.loads(filters_str)
    except Exception:
        f = {}
    try:
        thresh = {**DEFAULT_THRESHOLDS, **json.loads(thresholds_str)}
    except Exception:
        thresh = DEFAULT_THRESHOLDS
    hierarchy = f.get('hierarchy', {})
    extra = {k: v for k, v in f.items() if k != 'hierarchy'}
    df_f = apply_hierarchy_filters(df, hierarchy)
    df_f = apply_extra_filters(df_f, extra)
    agg = compute_aggregates(df_f)
    df_f, _ = apply_risk_scoring_v2(df_f, agg, thresh)
    return df_f


def _fmt_cascade_date(val):
    if pd.notna(val):
        return val.strftime('%d.%m.%Y') if hasattr(val, 'strftime') else str(val)[:10]
    return ''


def _build_orders_list(df_subset):
    """Стандартный список заказов из подмножества DataFrame."""
    orders = []
    for _, row in df_subset.iterrows():
        order_id = str(row.get('ID', '')) if pd.notna(row.get('ID')) else ''
        text = str(row.get('Текст', '')) if pd.notna(row.get('Текст')) else ''
        vid = str(row.get('Вид', '')) if pd.notna(row.get('Вид')) else ''
        date_val = None
        for dc in ['Факт_Начало', 'Факт_Конец', 'Начало', 'Конец']:
            v = row.get(dc, None)
            if pd.notna(v):
                date_val = v
                break
        date_str = ''
        if date_val is not None and pd.notna(date_val):
            date_str = date_val.isoformat()[:10] if hasattr(date_val, 'isoformat') else str(date_val)[:10]
        fact = _sf(row.get('Fact_N', 0))
        plan = _sf(row.get('Plan_N', 0))
        stat = str(row.get('STAT', '')) if pd.notna(row.get('STAT')) else ''
        abc = str(row.get('ABC', '')) if pd.notna(row.get('ABC')) else ''
        eo_name = str(row.get('ЕО', '')) if pd.notna(row.get('ЕО')) else ''
        eo_code = str(row.get('EQUNR_Код', '')) if 'EQUNR_Код' in df_subset.columns and pd.notna(row.get('EQUNR_Код')) else ''
        # Каскадные даты
        date_source = str(row.get('Источник_Дат', 'NONE')) if pd.notna(row.get('Источник_Дат')) else 'NONE'
        orders.append({
            "id": order_id, "text": text, "vid": vid,
            "date": date_str, "fact": fact, "plan": plan, "stat": stat,
            "dev": round(fact - plan, 2),
            "abc": abc, "equipment_name": eo_name, "equipment_code": eo_code,
            "date_start": _fmt_cascade_date(row.get('Дата_Начало')),
            "date_end": _fmt_cascade_date(row.get('Дата_Конец')),
            "date_source": date_source,
        })
    return orders


@router.get("/api/tab/workplaces")
async def get_workplaces(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Данные для вкладки Рабочие места."""
    df_f = _get_df(session_id, filters, thresholds)
    if df_f is None:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

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


@router.get("/api/workplaces/orders")
async def get_workplaces_orders(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}"),
    rm: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Заказы по конкретному РМ для аккордеона, с пагинацией."""
    df_f = _get_df(session_id, filters, thresholds)
    if df_f is None:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})
    if 'РМ' not in df_f.columns:
        return {"orders": [], "total": 0}
    df_group = df_f[df_f['РМ'].astype(str) == str(rm)]
    orders = _build_orders_list(df_group)
    orders.sort(key=lambda x: x['date'], reverse=True)
    total = len(orders)
    start = (page - 1) * page_size
    return {"orders": orders[start:start + page_size], "total": total}
