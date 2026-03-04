# -*- coding: utf-8 -*-
"""
api/routes_export.py — GET /api/export/excel
"""

import json
import pandas as pd
from io import BytesIO
from urllib.parse import quote
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime

from state.session import get_session
from utils.filters import apply_hierarchy_filters, apply_extra_filters
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2, is_empty_eo_mask
from utils.export import create_excel_download
from config.constants import METHODS_RISK

router = APIRouter()
DEFAULT_THRESHOLDS = {m: info['threshold_default'] for m, info in METHODS_RISK.items()}


@router.get("/api/export/excel")
async def export_excel(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}")
):
    """Скачать Excel."""
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

    # Быстрые фильтры (из вкладки Заказы)
    quick = f.get('quick_filters', {})
    if quick:
        for qk, qcol in [('author', 'USER'), ('tm', 'ТМ'), ('method', None),
                          ('ceh', 'ЦЕХ'), ('zavod', 'ЗАВОД'), ('rm', 'РМ'),
                          ('eo', 'ЕО')]:
            vals = quick.get(qk, [])
            if vals and qcol and qcol in df_f.columns:
                df_f = df_f[df_f[qcol].isin(vals)]
        # Фильтр по методам
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
        # Поиск по номерам заказов
        order_ids = quick.get('order_ids', [])
        if order_ids and 'ID' in df_f.columns:
            df_f = df_f[df_f['ID'].astype(str).isin([str(x).strip() for x in order_ids])]

    # C2-M2: исключаем заказы с пустым ЕО где сработал C2-M2
    c2m2_flag = 'S_C2-M2: Проблемное оборудование'
    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df_f.columns else 'ЕО'
    if c2m2_flag in df_f.columns and eo_col in df_f.columns:
        empty_eo = is_empty_eo_mask(df_f[eo_col])
        df_f = df_f[~(df_f[c2m2_flag] & empty_eo)]

    output = create_excel_download(df_f, "titan_export")
    filename = f"titan_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# Маппинг group_by → колонка DataFrame
_GROUP_COL = {
    'ceh': 'ЦЕХ',
    'tm': 'ТМ',
    'ingrp': 'INGRP',
    'user': 'USER',
    'rm': 'РМ',
}

_GROUP_LABEL = {
    'ceh': 'Цех',
    'tm': 'Техническое место',
    'ingrp': 'Группа плановиков',
    'user': 'Автор',
    'rm': 'Рабочее место',
}


def _sf(v):
    return 0.0 if pd.isna(v) else float(v)


def _fmt_date(val):
    """Форматировать дату для Excel."""
    if pd.isna(val):
        return ''
    return val.strftime('%d.%m.%Y') if hasattr(val, 'strftime') else str(val)[:10]


def _s(row, col):
    """Безопасно достать строковое значение."""
    v = row.get(col)
    return str(v) if pd.notna(v) else ''


def _build_orders_df(df_subset, group_label, group_value):
    """Построить DataFrame заказов для экспорта — все поля."""
    # Сработавшие методы
    methods_acc = pd.Series('', index=df_subset.index)
    for mn in METHODS_RISK.keys():
        flag = f"S_{mn}"
        short = mn.split(':')[0]
        if flag in df_subset.columns:
            add = df_subset[flag].map({True: short, False: ''}).fillna('')
            methods_acc = methods_acc.where(
                (methods_acc == '') | (add == ''),
                methods_acc + ', '
            ) + add

    rows = []
    for idx, row in df_subset.iterrows():
        rows.append({
            group_label: group_value,
            'Номер заказа': _s(row, 'ID'),
            'Текст работ': _s(row, 'Текст'),
            'Код ЕО': _s(row, 'EQUNR_Код') if 'EQUNR_Код' in df_subset.columns else '',
            'Наименование ЕО': _s(row, 'ЕО'),
            'ABC': _s(row, 'ABC'),
            'Вид работ': _s(row, 'Вид'),
            'Статус': _s(row, 'STAT'),
            'РМ': _s(row, 'РМ'),
            'ТМ': _s(row, 'ТМ'),
            'INGRP': _s(row, 'INGRP'),
            'Автор': _s(row, 'USER'),
            'Дата начала': _fmt_date(row.get('Дата_Начало')),
            'Дата окончания': _fmt_date(row.get('Дата_Конец')),
            'Источник дат': _s(row, 'Источник_Дат'),
            'План ₽': _sf(row.get('Plan_N', 0)),
            'Факт ₽': _sf(row.get('Fact_N', 0)),
            'Отклонение ₽': round(_sf(row.get('Fact_N', 0)) - _sf(row.get('Plan_N', 0)), 2),
            'Risk Score': _sf(row.get('Risk_Sum', 0)),
            'Методы': methods_acc.get(idx, ''),
        })
    return pd.DataFrame(rows)


@router.get("/api/export/orders_excel")
async def export_orders_excel(
    session_id: str = Query(...),
    filters: str = Query("{}"),
    thresholds: str = Query("{}"),
    group_by: str = Query(...),
    group_value: str = Query(...),
):
    """Экспорт заказов по группе (цех/ТМ/INGRP/USER/РМ) в Excel."""
    if group_by not in _GROUP_COL:
        return JSONResponse(status_code=400, content={"error": f"Неизвестный group_by: {group_by}"})

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

    col = _GROUP_COL[group_by]
    if col not in df_f.columns:
        return JSONResponse(status_code=400, content={"error": f"Колонка {col} не найдена"})

    df_group = df_f[df_f[col].astype(str) == str(group_value)]
    label = _GROUP_LABEL[group_by]
    df_out = _build_orders_df(df_group, label, group_value)

    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_out.to_excel(writer, index=False, sheet_name='Заказы')
    except ModuleNotFoundError:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_out.to_excel(writer, index=False, sheet_name='Заказы')
    output.seek(0)

    filename = f"Заказы_{group_value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    encoded = quote(filename)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}; filename=\"orders.xlsx\""}
    )
