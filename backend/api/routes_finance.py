# -*- coding: utf-8 -*-
"""
api/routes_finance.py — GET /api/tab/finance
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

MONTH_SHORT = {
    1: 'Янв', 2: 'Фев', 3: 'Мар', 4: 'Апр',
    5: 'Май', 6: 'Июн', 7: 'Июл', 8: 'Авг',
    9: 'Сен', 10: 'Окт', 11: 'Ноя', 12: 'Дек'
}

DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}


def _sf(val):
    """Safe float."""
    if pd.isna(val):
        return 0.0
    return float(val)


def _get_df(session_id, filters_str, thresholds_str):
    """Общая логика получения отфильтрованного DataFrame."""
    session = get_session(session_id)
    if not session:
        return None, None

    df = session['df']

    try:
        f = json.loads(filters_str)
    except Exception:
        f = {}

    try:
        thresh = json.loads(thresholds_str)
        merged = {**DEFAULT_THRESHOLDS, **thresh}
    except Exception:
        merged = DEFAULT_THRESHOLDS

    hierarchy = f.get('hierarchy', {})
    extra = {k: v for k, v in f.items() if k != 'hierarchy'}

    df_filtered = apply_hierarchy_filters(df, hierarchy)
    df_filtered = apply_extra_filters(df_filtered, extra)

    agg = compute_aggregates(df_filtered)
    df_scored, _ = apply_risk_scoring_v2(df_filtered, agg, merged)

    return df_scored, agg


@router.get("/api/tab/finance")
async def get_finance(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Данные для вкладки Финансы."""
    df_f, agg = _get_df(session_id, filters, thresholds)
    if df_f is None:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    result = {}

    # 1. Помесячные данные
    date_col = None
    for col in ['Начало', 'Конец', 'Факт_Начало']:
        if col in df_f.columns and df_f[col].notna().any():
            date_col = col
            break

    monthly = []
    if date_col and 'Fact_N' in df_f.columns:
        df_m = df_f[df_f['Fact_N'] > 0].copy()
        df_m['_month'] = df_m[date_col].dt.month
        df_m['_year'] = df_m[date_col].dt.year
        df_valid = df_m[df_m['_month'].notna()]

        if len(df_valid) > 0:
            grp = df_valid.groupby(['_year', '_month']).agg(
                fact=('Fact_N', 'sum'),
                plan=('Plan_N', 'sum'),
                count=('ID', 'count')
            ).reset_index()
            grp = grp.sort_values(['_year', '_month'])

            for _, r in grp.iterrows():
                monthly.append({
                    "label": f"{MONTH_SHORT.get(int(r['_month']), '?')} {int(r['_year'])}",
                    "fact": _sf(r['fact']),
                    "plan": _sf(r['plan']),
                    "count": int(r['count'])
                })
    result['monthly'] = monthly

    # 2. Цеха
    ceh_data = []
    if 'ЦЕХ' in df_f.columns:
        ceh_stats = df_f.groupby('ЦЕХ').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        ceh_stats['dev'] = ceh_stats['fact'] - ceh_stats['plan']
        ceh_stats = ceh_stats[ceh_stats['ЦЕХ'] != 'Н/Д']
        ceh_stats = ceh_stats.sort_values('dev', ascending=False)

        for _, r in ceh_stats.iterrows():
            ceh_data.append({
                "name": str(r['ЦЕХ']),
                "plan": _sf(r['plan']),
                "fact": _sf(r['fact']),
                "dev": _sf(r['dev']),
                "count": int(r['count'])
            })
    result['ceh_data'] = ceh_data

    # 3. ТМ
    tm_data = []
    if 'ТМ_Код' in df_f.columns:
        df_tm = df_f[df_f['ТМ_Код'].astype(str).str.len() >= 12]
    else:
        df_tm = df_f[df_f['ТМ'].astype(str).str.match(r'^ST\d{2}\.\d{4}\.\w+', na=False)]

    if len(df_tm) > 0:
        tm_stats = df_tm.groupby('ТМ').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        tm_stats['dev'] = tm_stats['fact'] - tm_stats['plan']

        tm_over = tm_stats[tm_stats['dev'] > 0].sort_values('dev', ascending=False).head(15)
        tm_save = tm_stats[tm_stats['dev'] < 0].sort_values('dev').head(15)
        tm_combined = pd.concat([tm_over, tm_save]).sort_values('dev', ascending=False)

        for _, r in tm_combined.iterrows():
            tm_data.append({
                "name": str(r['ТМ']),
                "plan": _sf(r['plan']),
                "fact": _sf(r['fact']),
                "dev": _sf(r['dev']),
                "count": int(r['count'])
            })
    result['tm_data'] = tm_data

    # 4. ABC
    abc_data = []
    abc_stats = df_f.groupby('ABC').agg(
        count=('ID', 'count'), sum=('Fact_N', 'sum')
    ).reset_index()
    total_abc = abc_stats['sum'].sum()

    for _, r in abc_stats.sort_values('sum', ascending=False).iterrows():
        pct = r['sum'] / max(total_abc, 1) * 100
        abc_data.append({
            "abc": str(r['ABC']),
            "count": int(r['count']),
            "sum": _sf(r['sum']),
            "pct": round(pct, 1)
        })
    result['abc_data'] = abc_data

    # 5. Парето 80/20
    pareto = []
    pareto_orders = []
    if 'Fact_N' in df_f.columns:
        pareto_cols = ['ID', 'Текст', 'Fact_N', 'Plan_N', 'Вид', 'ТМ']
        if 'EQUNR_Код' in df_f.columns:
            pareto_cols.append('EQUNR_Код')
        if 'ЕО' in df_f.columns:
            pareto_cols.append('ЕО')
        df_p = df_f[df_f['Fact_N'] > 0][[c for c in pareto_cols if c in df_f.columns]].copy()
        df_p = df_p.sort_values('Fact_N', ascending=False).reset_index(drop=True)
        if len(df_p) > 0:
            total = df_p['Fact_N'].sum()
            cumsum = 0
            threshold_idx = len(df_p)  # индекс 80% порога
            for i, (_, r) in enumerate(df_p.iterrows()):
                cumsum += r['Fact_N']
                cum_pct = cumsum / total * 100
                order_pct = (i + 1) / len(df_p) * 100
                if i % max(1, len(df_p) // 100) == 0 or i == len(df_p) - 1:
                    pareto.append({
                        "order_pct": round(order_pct, 1),
                        "cum_pct": round(cum_pct, 1)
                    })
                if cum_pct <= 80 or threshold_idx == len(df_p):
                    eo_code = str(r.get('EQUNR_Код', '')) if 'EQUNR_Код' in r.index else ''
                    if eo_code in ('Н/Д', 'nan', 'None', '', ' ', '0'):
                        eo_code = ''
                    eo_name = str(r.get('ЕО', '')) if 'ЕО' in r.index else ''
                    if eo_name in ('Н/Д', 'nan', 'None', '', ' ', '0'):
                        eo_name = ''
                    pareto_orders.append({
                        "id": str(r['ID']),
                        "text": str(r.get('Текст', ''))[:60],
                        "fact": _sf(r['Fact_N']),
                        "plan": _sf(r.get('Plan_N', 0)),
                        "vid": str(r.get('Вид', '')),
                        "tm": str(r.get('ТМ', '')),
                        "equipment_code": eo_code,
                        "equipment_name": eo_name,
                        "cum_pct": round(cum_pct, 1),
                    })
                    if cum_pct >= 80 and threshold_idx == len(df_p):
                        threshold_idx = i + 1
            # Статистика 80/20
            result['pareto_stats'] = {
                "orders_80pct": threshold_idx,
                "total_orders": len(df_p),
                "orders_pct": round(threshold_idx / len(df_p) * 100, 1),
            }
    result['pareto'] = pareto
    result['pareto_orders'] = pareto_orders[:100]  # Ограничиваем 100 заказами

    # KPI
    plan_total = _sf(df_f['Plan_N'].sum())
    fact_total = _sf(df_f['Fact_N'].sum())
    result['kpi'] = {
        "plan": plan_total,
        "fact": fact_total,
        "dev": fact_total - plan_total,
        "dev_pct": round((fact_total - plan_total) / max(plan_total, 1) * 100, 1),
        "overrun_count": int(len(df_f[df_f['Fact_N'] > df_f['Plan_N']])) if 'Plan_N' in df_f.columns else 0,
    }

    return result
