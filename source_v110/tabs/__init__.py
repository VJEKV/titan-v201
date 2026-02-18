# -*- coding: utf-8 -*-
"""
tabs/ — Вкладки дашборда ТИТАН Аудит ТОРО

7 вкладок аналитики.
"""

from .tab_finance import render_tab_finance
from .tab_timeline import render_tab_timeline
from .tab_work_types import render_tab_work_types
from .tab_planners import render_tab_planners
from .tab_workplaces import render_tab_workplaces
from .tab_risks import render_tab_risks
from .tab_quality import render_tab_quality

__all__ = [
    'render_tab_finance',
    'render_tab_timeline',
    'render_tab_work_types',
    'render_tab_planners',
    'render_tab_workplaces',
    'render_tab_risks',
    'render_tab_quality'
]
