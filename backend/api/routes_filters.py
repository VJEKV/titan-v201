# -*- coding: utf-8 -*-
"""
api/routes_filters.py — GET /api/filters/options
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from state.session import get_session
from utils.filters import get_hierarchy_options
from config.constants import HIERARCHY_LEVELS

router = APIRouter()


@router.get("/api/filters/options")
async def get_filter_options(session_id: str = Query(...)):
    """Доступные значения фильтров."""
    session = get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})

    df = session['df']

    # Иерархия
    hierarchy = {}
    for level in HIERARCHY_LEVELS:
        key = level['key']
        if key in df.columns:
            vals = df[key].dropna().unique()
            vals = [str(v) for v in vals if str(v) not in ['Н/Д', 'nan', 'None', '', 'Не присвоено']]
            hierarchy[key] = sorted(vals)
        else:
            hierarchy[key] = []

    # Прочие фильтры
    def _unique(col):
        if col in df.columns:
            vals = df[col].dropna().unique()
            return sorted([str(v) for v in vals if str(v) not in ['Н/Д', 'nan', 'None', '']])
        return []

    return {
        "hierarchy": hierarchy,
        "vid": _unique('Вид'),
        "abc": _unique('ABC'),
        "stat": _unique('STAT'),
        "rm": _unique('РМ'),
        "ingrp": _unique('INGRP'),
    }
