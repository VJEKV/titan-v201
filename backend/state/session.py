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


def cleanup_old_sessions():
    """Удалить устаревшие сессии."""
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if now - s['timestamp'] > SESSION_TTL]
    for sid in expired:
        del _sessions[sid]
