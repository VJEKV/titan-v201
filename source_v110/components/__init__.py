# -*- coding: utf-8 -*-
"""
components/ — UI компоненты ТИТАН Аудит ТОРО

Переиспользуемые компоненты интерфейса.
"""

from .sidebar import render_sidebar
from .kpi_block import render_kpi, calculate_level_kpi
from .charts import create_method_donut, CHART_FONT

__all__ = [
    'render_sidebar',
    'render_kpi', 'calculate_level_kpi',
    'create_method_donut', 'CHART_FONT'
]
