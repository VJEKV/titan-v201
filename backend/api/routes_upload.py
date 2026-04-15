# -*- coding: utf-8 -*-
"""
api/routes_upload.py — POST /api/upload

ТИТАН-5: Parquet-кэш. Если SHA-256 файла совпадает с сохранённым в кэше —
пропускаем process_data и compute_aggregates (4-5 мин → 2-3 сек).
"""

import time
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

from core.data_loader import load_file
from core.data_processor import process_data
from core.aggregates import compute_aggregates
from core import cache
from core import response_cache
from state.session import create_session

router = APIRouter()


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Загрузка файла SAP (.xlsx, .csv)."""
    start = time.time()

    try:
        contents = await file.read()
        file_hash = cache.compute_file_hash(contents)

        cache_hit = cache.has_cache(file_hash)
        if cache_hit:
            # Быстрый путь: читаем готовый DataFrame из Parquet
            df, agg, meta = cache.load_cache(file_hash)
            export_format = df.attrs.get('export_format', 'UNKNOWN')
        else:
            # Полный путь: парсинг + обработка
            df_raw = load_file(contents, file.filename)
            df = process_data(df_raw)
            agg = compute_aggregates(df)
            export_format = df.attrs.get('export_format', 'UNKNOWN')
            # Сохраняем в кэш для следующих загрузок
            cache.save_cache(file_hash, df, agg, meta={
                'filename': file.filename,
                'rows': len(df),
                'columns': len(df.columns),
            })

        session_id = create_session(df, agg)

        # ТИТАН-5: очищаем LRU-кэш ответов (данные могли измениться)
        response_cache.invalidate_session(session_id)

        elapsed = round(time.time() - start, 2)

        return {
            "session_id": session_id,
            "rows": len(df),
            "columns": len(df.columns),
            "processing_time": elapsed,
            "format": export_format,
            "cache_hit": cache_hit,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.get("/api/cache/stats")
async def get_cache_stats():
    """Статистика Parquet-кэша."""
    return cache.cache_stats()


@router.post("/api/cache/clear")
async def clear_cache():
    """Очистка всего Parquet-кэша."""
    removed = cache.invalidate_cache()
    return {"removed_files": removed}
