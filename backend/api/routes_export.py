# -*- coding: utf-8 -*-
"""
api/routes_export.py — GET /api/export/excel
"""

import json
import pandas as pd
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
