# -*- coding: utf-8 -*-
"""
core/ — Ядро обработки данных ТИТАН Аудит ТОРО

Загрузка, обработка, агрегация и риск-скоринг.
"""

from .data_loader import load_file, detect_export_format
from .data_processor import process_data, aggregate_status_history
from .aggregates import compute_aggregates
from .risk_scoring import get_logic, check_method_has_data, apply_risk_scoring

__all__ = [
    'load_file', 'detect_export_format',
    'process_data', 'aggregate_status_history',
    'compute_aggregates',
    'get_logic', 'check_method_has_data', 'apply_risk_scoring'
]
