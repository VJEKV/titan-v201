# -*- coding: utf-8 -*-
"""
api/routes_upload.py — POST /api/upload
"""

import time
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

from core.data_loader import load_file
from core.data_processor import process_data
from core.aggregates import compute_aggregates
from state.session import create_session

router = APIRouter()


@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Загрузка файла SAP (.xlsx, .csv)."""
    start = time.time()

    try:
        contents = await file.read()
        df_raw = load_file(contents, file.filename)
        df = process_data(df_raw)

        # Оптимизация памяти: object → category
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() / len(df) < 0.5:
                df[col] = df[col].astype('category')

        agg = compute_aggregates(df)
        session_id = create_session(df, agg)

        elapsed = round(time.time() - start, 2)

        return {
            "session_id": session_id,
            "rows": len(df),
            "columns": len(df.columns),
            "processing_time": elapsed,
            "format": df.attrs.get('export_format', 'UNKNOWN')
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
