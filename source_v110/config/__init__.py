# -*- coding: utf-8 -*-
"""
config/ — Конфигурация ТИТАН Аудит ТОРО

Стили, константы, настройки по умолчанию.
"""

from .styles import STYLES
from .constants import (
    METHODS_RISK, 
    HIERARCHY_LEVELS, 
    ВНЕПЛАНОВЫЕ_ВИДЫ,
    ВИДЫ_ЗАКАЗОВ
)
from .settings import init_session_state, DEFAULT_THRESHOLDS

__all__ = [
    'STYLES',
    'METHODS_RISK', 'HIERARCHY_LEVELS', 'ВНЕПЛАНОВЫЕ_ВИДЫ', 'ВИДЫ_ЗАКАЗОВ',
    'init_session_state', 'DEFAULT_THRESHOLDS'
]
