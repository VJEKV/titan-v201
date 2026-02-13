# -*- coding: utf-8 -*-
"""
api/routes_planners.py — GET /api/tab/planners
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


@router.get("/api/tab/planners")
async def get_planners(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Данные для вкладки Плановики."""
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

    # Группы плановиков
    ingrp_data = []
    if 'INGRP' in df_f.columns:
        stats = df_f.groupby('INGRP').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        stats['dev'] = stats['fact'] - stats['plan']
        stats = stats.sort_values('dev', ascending=False)

        for _, r in stats.iterrows():
            ingrp_data.append({
                "name": str(r['INGRP']),
                "count": int(r['count']),
                "fact": _sf(r['fact']),
                "plan": _sf(r['plan']),
                "dev": _sf(r['dev'])
            })

    # Авторы
    users_data = []
    if 'USER' in df_f.columns:
        u_stats = df_f.groupby('USER').agg(
            count=('ID', 'count'), fact=('Fact_N', 'sum'), plan=('Plan_N', 'sum')
        ).reset_index()
        u_stats['dev'] = u_stats['fact'] - u_stats['plan']
        u_stats = u_stats.sort_values('dev', ascending=False).head(20)

        for _, r in u_stats.iterrows():
            users_data.append({
                "name": str(r['USER']),
                "count": int(r['count']),
                "fact": _sf(r['fact']),
                "plan": _sf(r['plan']),
                "dev": _sf(r['dev'])
            })

    # Скоринг пользователей: незаполненные поля
    user_scoring = []
    check_fields = {
        'Plan_N': 'План. стоимость',
        'Начало': 'Дата начала',
        'Конец': 'Дата окончания',
        'ТМ': 'Техническое место',
        'ЕО': 'Оборудование',
        'ABC': 'Код ABC',
        'Вид': 'Вид заказа',
        'ДОГОВОР': 'Номер договора',
    }
    if 'USER' in df_f.columns:
        # Группируем по пользователю
        users_list = df_f['USER'].unique()
        for user in users_list[:30]:  # TOP-30
            user_df = df_f[df_f['USER'] == user]
            total_user = len(user_df)
            if total_user == 0:
                continue
            empty_fields = {}
            for field_code, field_name in check_fields.items():
                if field_code in user_df.columns:
                    empty_count = 0
                    if field_code in ('Plan_N',):
                        empty_count = int((user_df[field_code].fillna(0) == 0).sum())
                    elif field_code in ('Начало', 'Конец'):
                        empty_count = int(user_df[field_code].isna().sum())
                    else:
                        empty_count = int(
                            user_df[field_code].astype(str).str.strip().isin(
                                {'Н/Д', 'н/д', 'Не присвоено', 'nan', 'NaN', 'None', 'none', '', ' ', '0', 'Пусто'}
                            ).sum()
                        )
                    if empty_count > 0:
                        empty_fields[field_name] = {
                            "count": empty_count,
                            "pct": round(empty_count / total_user * 100, 1)
                        }

            if empty_fields:
                total_empty = sum(f['count'] for f in empty_fields.values())
                user_scoring.append({
                    "user": str(user),
                    "total_orders": total_user,
                    "empty_fields": empty_fields,
                    "total_empty_entries": total_empty,
                    "score": round(total_empty / (total_user * len(check_fields)) * 100, 1),
                })

        user_scoring.sort(key=lambda x: x['score'], reverse=True)

    # Heatmap плановик × метод
    heatmap = []
    if 'INGRP' in df_f.columns:
        for method_name in METHODS_RISK.keys():
            flag = f"S_{method_name}"
            if flag in df_f.columns:
                method_by_ingrp = df_f.groupby('INGRP')[flag].sum().to_dict()
                for ingrp_name, count in method_by_ingrp.items():
                    if count > 0:
                        heatmap.append({
                            "ingrp": str(ingrp_name),
                            "method": method_name.split(':')[0],
                            "count": int(count)
                        })

    # KPI
    n_ingrp = df_f['INGRP'].nunique() if 'INGRP' in df_f.columns else 0
    n_users = df_f['USER'].nunique() if 'USER' in df_f.columns else 0
    overrun = int(len(df_f[df_f['Fact_N'] > df_f['Plan_N']])) if 'Plan_N' in df_f.columns else 0

    return {
        "ingrp_data": ingrp_data,
        "users_data": users_data,
        "user_scoring": user_scoring,
        "heatmap": heatmap,
        "kpi": {
            "n_ingrp": n_ingrp,
            "n_users": n_users,
            "total_fact": _sf(df_f['Fact_N'].sum()),
            "overrun_count": overrun,
        }
    }
