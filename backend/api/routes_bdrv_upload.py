# -*- coding: utf-8 -*-
"""
api/routes_bdrv_upload.py — POST /api/bdrv/upload
GET /api/bdrv/status

Загрузка выгрузки БДРВ (временные ряды режимов оборудования из SCADA-историка).

ТИТАН-5.
"""

import hashlib
import time
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import JSONResponse

from core.bdrv_loader import (
    load_bdrv_csv, load_bdrv_zip,
    save_bdrv_parquet, load_bdrv_parquet,
    bdrv_summary,
)
from core import duck
from state.session import get_session, set_bdrv

router = APIRouter()

BDRV_CACHE_DIR = Path(__file__).parent.parent / 'cache' / 'bdrv'
BDRV_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(file_hash: str) -> Path:
    return BDRV_CACHE_DIR / f'bdrv_{file_hash}.parquet'


@router.post("/api/bdrv/upload")
async def upload_bdrv(session_id: str = Query(...), file: UploadFile = File(...)):
    """Загрузка выгрузки БДРВ: ZIP с несколькими CSV или одиночный CSV.

    Привязывается к сессии session_id (её нужно получить через /api/upload заранее).

    Формат файлов:
        CSV «Панель тренда»: Timestamp;tag1;tag2;...
        Разделитель `;`, десятичный `,`
        Теги SCADA: PLANT.POS.TYPE.VALUE (например ETL1.PDI2045.DACA.PV)
    """
    start = time.time()
    session = get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена. Сначала загрузите файл ТОРО через /api/upload."})

    try:
        contents = await file.read()
        file_hash = hashlib.sha256(contents).hexdigest()[:32]
        cache_path = _cache_path(file_hash)

        if cache_path.exists():
            df = load_bdrv_parquet(cache_path)
            cache_hit = True
        else:
            name = (file.filename or '').lower()
            if name.endswith('.zip'):
                df = load_bdrv_zip(contents)
            else:
                df = load_bdrv_csv(contents, filename=file.filename or '')
            if not df.empty:
                save_bdrv_parquet(df, cache_path)
            cache_hit = False

        summary = bdrv_summary(df)
        set_bdrv(session_id, df, str(cache_path), summary)

        # Регистрируем DataFrame в DuckDB-connection сессии для быстрых SQL-запросов
        try:
            duck.register_bdrv(session_id, df)
        except Exception:
            pass

        elapsed = round(time.time() - start, 2)
        return {
            "session_id": session_id,
            "cache_hit": cache_hit,
            "summary": summary,
            "processing_time": elapsed,
            "filename": file.filename,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.get("/api/bdrv/status")
async def bdrv_status(session_id: str = Query(...)):
    """Проверить, загружена ли БДРВ для сессии."""
    session = get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})
    loaded = session.get('bdrv_df') is not None
    return {
        "session_id": session_id,
        "loaded": loaded,
        "summary": session.get('bdrv_summary'),
    }


@router.get("/api/bdrv/eo-list")
async def bdrv_eo_list(session_id: str = Query(...)):
    """Список ЕО, для которых есть БДРВ-данные (для выпадающего списка в UI)."""
    session = get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Сессия не найдена"})
    bdrv_df = session.get('bdrv_df')
    if bdrv_df is None or bdrv_df.empty:
        return {"eo_list": []}

    # Уникальные equnr с числом точек данных
    counts = bdrv_df.groupby('equnr', observed=True).size().reset_index(name='n_points')
    counts = counts.sort_values('n_points', ascending=False)
    return {
        "eo_list": [
            {"equnr": str(r['equnr']), "n_points": int(r['n_points'])}
            for _, r in counts.iterrows()
        ]
    }
