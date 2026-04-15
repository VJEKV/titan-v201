# -*- coding: utf-8 -*-
"""
state/session.py — Хранение DataFrame в памяти
"""

import time
import uuid
from typing import Optional
import pandas as pd

# Хранилище сессий
_sessions: dict = {}

# Автоочистка — удалять сессии старше 1 часа
SESSION_TTL = 3600


def create_session(df: pd.DataFrame, agg: dict) -> str:
    """Создать новую сессию."""
    cleanup_old_sessions()
    session_id = str(uuid.uuid4())[:8]
    _sessions[session_id] = {
        'df': df,
        'agg': agg,
        'bdrv_df': None,          # ТИТАН-5: BDRV parsed DataFrame (опционально)
        'bdrv_parquet_path': None,  # ТИТАН-5: путь к кэшу BDRV
        'bdrv_summary': None,       # {eo_count, tag_count, rows, date_min, date_max}
        'timestamp': time.time(),
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """Получить данные сессии."""
    session = _sessions.get(session_id)
    if session and (time.time() - session['timestamp']) < SESSION_TTL:
        session['timestamp'] = time.time()
        return session
    if session:
        del _sessions[session_id]
    return None


def set_bdrv(session_id: str, df: pd.DataFrame, parquet_path: str, summary: dict) -> bool:
    """Прикрепить BDRV DataFrame к сессии."""
    session = _sessions.get(session_id)
    if not session:
        return False
    session['bdrv_df'] = df
    session['bdrv_parquet_path'] = parquet_path
    session['bdrv_summary'] = summary
    session['timestamp'] = time.time()
    return True


def cleanup_old_sessions():
    """Удалить устаревшие сессии."""
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s['timestamp'] > SESSION_TTL]
    for sid in expired:
        # Закрываем DuckDB-connection и удаляем parquet-кэш этой сессии, если есть
        try:
            from core import duck
            duck.close_session(sid)
        except Exception:
            pass
        del _sessions[sid]
