# -*- coding: utf-8 -*-
"""
api/routes_risks.py — GET /api/tab/risks
"""

import json
import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2, _is_empty_eo, is_empty_eo_mask
from config.constants import METHODS_RISK

router = APIRouter()
DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}

def _sf(v):
    return 0.0 if pd.isna(v) else float(v)


@router.get("/api/tab/risks")
async def get_risks(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
):
    """Данные для вкладки Приоритеты аудита."""
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
    df_f, scoring_info = apply_risk_scoring_v2(df_f, agg, thresh)
    orders_without_eo = scoring_info.get('orders_without_eo', 0)

    total = len(df_f)
    risk_orders = df_f[df_f['Priority_Score'] > 0]

    # Методы
    methods = []
    for method_name, method_info in METHODS_RISK.items():
        flag = f"S_{method_name}"
        score_col = f"Score_{method_name}"
        # Для C2-M2 исключаем заказы без ЕО
        if 'C2-M2' in method_name and flag in df_f.columns:
            eo_c = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
            if eo_c in df_f.columns:
                valid = ~is_empty_eo_mask(df_f[eo_c])
                triggered_count = int((df_f[flag] & valid).sum())
                triggered_sum = _sf(df_f[(df_f[flag] == True) & valid]['Fact_N'].sum())
            else:
                triggered_count = int(df_f[flag].sum())
                triggered_sum = _sf(df_f[df_f[flag] == True]['Fact_N'].sum())
        else:
            triggered_count = int(df_f[flag].sum()) if flag in df_f.columns else 0
            triggered_sum = _sf(df_f[df_f[flag] == True]['Fact_N'].sum()) if flag in df_f.columns else 0
        avg_score = _sf(df_f[score_col].mean()) if score_col in df_f.columns else 0

        method_data = {
            "name": method_name,
            "desc": method_info['desc'],
            "icon": method_info['icon'],
            "color": method_info.get('color', '#f43f5e'),
            "weight": method_info.get('weight', 1),
            "count": triggered_count,
            "total": total,
            "sum": triggered_sum,
            "avg_score": round(avg_score, 2),
            "threshold": thresh.get(method_name, method_info['threshold_default']),
            "has_threshold": method_info.get('has_threshold', False),
            "threshold_range": method_info.get('threshold_range', [0, 100]),
            "threshold_label": method_info.get('threshold_label', ''),
        }
        # Добавляем orders_without_eo для C2-M2
        if 'C2-M2' in method_name:
            method_data['orders_without_eo'] = orders_without_eo
        methods.append(method_data)

    # Radar данные
    radar = []
    for m in methods:
        pct = m['count'] / max(total, 1) * 100
        radar.append({
            "method": m['name'].split(':')[0],
            "value": round(pct, 1),
            "count": m['count']
        })

    # Фильтрация C2-M2: исключаем заказы с пустым ЕО где сработал C2-M2
    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
    c2m2_flag = 'S_C2-M2: Проблемное оборудование'
    if c2m2_flag in df_f.columns and eo_col in df_f.columns:
        empty_eo = is_empty_eo_mask(df_f[eo_col])
        df_f = df_f[~(df_f[c2m2_flag] & empty_eo)]

    top_priority = []
    total_risk_orders = len(df_f)
    total_pages = max(1, (total_risk_orders + page_size - 1) // page_size)

    if total_risk_orders > 0:
        top_df = df_f.sort_values('Priority_Score', ascending=False)
        start = (page - 1) * page_size
        end = start + page_size
        page_df = top_df.iloc[start:end]

        for idx, (_, r) in enumerate(page_df.iterrows()):
            triggered = []
            for mn in METHODS_RISK.keys():
                flag = f"S_{mn}"
                if flag in r and r[flag]:
                    triggered.append(mn.split(':')[0])

            # Код и наименование оборудования — полная проверка через _is_empty_eo
            eo_code = str(r.get('EQUNR_Код', '')) if 'EQUNR_Код' in r.index else ''
            if _is_empty_eo(eo_code):
                eo_code = ''
            eo_name = str(r.get('ЕО', '')) if 'ЕО' in r.index else ''
            if _is_empty_eo(eo_name):
                eo_name = ''

            top_priority.append({
                "id": str(r.get('ID', '')),
                "text": str(r.get('Текст', ''))[:60],
                "tm": str(r.get('ТМ', '')),
                "eo": eo_code or eo_name,
                "eo_name": eo_name if eo_code else '',
                "vid": str(r.get('Вид', '')),
                "plan": _sf(r.get('Plan_N', 0)),
                "fact": _sf(r.get('Fact_N', 0)),
                "risk_sum": round(_sf(r.get('Risk_Sum', 0)), 1),
                "priority_score": round(_sf(r.get('Priority_Score', 0)), 1),
                "dq_risk": round(_sf(r.get('DQ_Risk', 0)), 1),
                "methods_count": int(r.get('Methods_Count', 0)),
                "category": str(r.get('Risk_Category', 'Зелёный')),
                "methods": triggered,
                "completeness": round(_sf(r.get('Data_Completeness', 0)), 0),
            })

    # Подсчёт категорий
    cat_counts = {}
    if 'Risk_Category' in df_f.columns:
        cat_counts = df_f['Risk_Category'].value_counts().to_dict()

    return {
        "methods": methods,
        "radar": radar,
        "top_priority": top_priority,
        "total_orders": total_risk_orders,
        "page": page,
        "pages": total_pages,
        "page_size": page_size,
        "categories": {
            "red": int(cat_counts.get('Красный', 0)),
            "yellow": int(cat_counts.get('Жёлтый', 0)),
            "grey": int(cat_counts.get('Серый', 0)),
            "green": int(cat_counts.get('Зелёный', 0)),
        },
        "kpi": {
            "total": total,
            "risk_count": len(risk_orders),
            "risk_pct": round(len(risk_orders) / max(total, 1) * 100, 1),
            "risk_sum_total": round(float(df_f['Priority_Score'].sum()), 1),
            "avg_score": round(float(df_f['Priority_Score'].mean()), 2) if total > 0 else 0,
        }
    }
