# -*- coding: utf-8 -*-
"""
api/routes_orders.py — GET /api/tab/orders
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


@router.get("/api/tab/orders")
async def get_orders(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    sort: str = Query("Risk_Sum"),
    order: str = Query("desc")
):
    """Реестр заказов с пагинацией."""
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

    # Быстрые фильтры вкладки Заказы
    quick = f.get('quick_filters', {})
    if quick:
        for qk, qcol in [('author', 'USER'), ('tm', 'ТМ'), ('method', None),
                          ('ceh', 'ЦЕХ'), ('zavod', 'ЗАВОД'), ('rm', 'РМ'),
                          ('eo', 'ЕО')]:
            vals = quick.get(qk, [])
            if vals and qcol and qcol in df_f.columns:
                df_f = df_f[df_f[qcol].isin(vals)]
        # Фильтр по методам — проверяем флаги S_<method>
        method_vals = quick.get('method', [])
        if method_vals:
            mask = pd.Series(False, index=df_f.index)
            for mn in METHODS_RISK.keys():
                short = mn.split(':')[0]
                if short in method_vals:
                    flag = f"S_{mn}"
                    if flag in df_f.columns:
                        mask |= df_f[flag]
            df_f = df_f[mask]
            # C2-M2: исключаем заказы с пустым ЕО — векторизованная фильтрация
            if any('C2-M2' in v for v in method_vals):
                eo_col_filt = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
                if eo_col_filt in df_f.columns:
                    df_f = df_f[~is_empty_eo_mask(df_f[eo_col_filt])]
        # Поиск по нескольким номерам заказов
        order_ids = quick.get('order_ids', [])
        if order_ids and 'ID' in df_f.columns:
            df_f = df_f[df_f['ID'].astype(str).isin([str(x).strip() for x in order_ids])]

    # Вычисляемые поля
    df_f = df_f.copy()
    df_f['Δ_Сумма'] = df_f['Fact_N'] - df_f['Plan_N']

    if 'План_Длит' in df_f.columns and 'Факт_Длит' in df_f.columns:
        df_f['Δ_Дней'] = pd.to_numeric(df_f['Факт_Длит'], errors='coerce') - \
                         pd.to_numeric(df_f['План_Длит'], errors='coerce')
    else:
        df_f['Δ_Дней'] = 0

    # Сработавшие методы — векторизованная конкатенация (без .apply(axis=1))
    methods_acc = pd.Series('', index=df_f.index)
    for mn in METHODS_RISK.keys():
        flag = f"S_{mn}"
        short = mn.split(':')[0]
        if flag in df_f.columns:
            add = df_f[flag].map({True: short, False: ''}).fillna('')
            # Добавляем разделитель только если обе части непустые
            methods_acc = methods_acc.where(
                (methods_acc == '') | (add == ''),
                methods_acc + ', '
            ) + add
    df_f['methods'] = methods_acc

    # Сортировка
    sort_col = sort if sort in df_f.columns else 'Risk_Sum'
    ascending = order == 'asc'
    df_f = df_f.sort_values(sort_col, ascending=ascending, na_position='last')

    total = len(df_f)
    pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    df_page = df_f.iloc[start:end]

    # Определяем колонки оборудования
    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else None
    eo_name_col = 'ЕО' if 'ЕО' in df_f.columns else None

    # Формируем данные
    columns_order = [
        'ID', 'Текст', 'ТМ', 'Вид', 'STAT', 'ABC',
        'Plan_N', 'Fact_N', 'Δ_Сумма',
        'Начало', 'Конец', 'Факт_Начало', 'Факт_Конец',
        'План_Длит', 'Факт_Длит', 'Δ_Дней',
        'Risk_Sum', 'methods',
        'INGRP', 'USER', 'РМ', 'ЗАВОД', 'УСТАНОВКА', 'БЕ'
    ]

    data = []
    for _, row in df_page.iterrows():
        item = {}
        for col in columns_order:
            if col in row.index:
                val = row[col]
                if pd.isna(val):
                    item[col] = None
                elif hasattr(val, 'isoformat'):
                    item[col] = val.isoformat()[:10]
                else:
                    item[col] = val if not isinstance(val, (float,)) else round(val, 2)
            else:
                item[col] = None
        # Код ЕО и Наименование ЕО — отдельными полями
        eo_code_val = str(row.get(eo_col, '')) if eo_col and eo_col in row.index else ''
        if _is_empty_eo(eo_code_val):
            eo_code_val = ''
        item['equipment_code'] = eo_code_val
        eo_name_val = str(row.get(eo_name_col, '')) if eo_name_col and eo_name_col in row.index else ''
        if _is_empty_eo(eo_name_val):
            eo_name_val = ''
        item['equipment_name'] = eo_name_val
        data.append(item)

    # Опции для быстрых фильтров (уникальные значения в текущей выборке до quick_filters)
    def _opts(col, limit=50):
        if col in session['df'].columns:
            vals = session['df'][col].dropna().astype(str)
            vals = vals[~vals.isin(['Н/Д', 'nan', 'None', '', 'Не присвоено'])]
            return sorted(vals.unique().tolist())[:limit]
        return []

    quick_options = {
        "author": _opts('USER'),
        "tm": _opts('ТМ', 100),
        "method": [mn.split(':')[0] for mn in METHODS_RISK.keys()],
        "ceh": _opts('ЦЕХ'),
        "zavod": _opts('ЗАВОД'),
        "rm": _opts('РМ', 100),
        "eo": _opts('ЕО', 200),
    }

    return {
        "data": data,
        "total": total,
        "page": page,
        "pages": pages,
        "page_size": page_size,
        "quick_options": quick_options,
    }
