# -*- coding: utf-8 -*-
"""
utils/filters.py — Работа с фильтрами

Функции для иерархической фильтрации и построения навигации.
"""

import pandas as pd


# Импортируем HIERARCHY_LEVELS из config (будет доступен после создания)
# from config.constants import HIERARCHY_LEVELS

# Временно определяем здесь для автономности модуля
# БЕ → ЗАВОД → ПРОИЗВОДСТВО → ЦЕХ → УСТАНОВКА → ЕО
HIERARCHY_LEVELS = [
    {'key': 'БЕ', 'name': 'Балансовая единица', 'icon': '🏢'},
    {'key': 'ЗАВОД', 'name': 'Завод', 'icon': '🏭'},
    {'key': 'ПРОИЗВОДСТВО', 'name': 'Производство', 'icon': '🏗️'},
    {'key': 'ЦЕХ', 'name': 'Цех', 'icon': '⚙️'},
    {'key': 'УСТАНОВКА', 'name': 'Установка', 'icon': '📍'},
    {'key': 'ЕО', 'name': 'Ед. оборудования', 'icon': '🔧'}
]


def get_hierarchy_options(df, level_key, parent_filters):
    """
    Получить доступные опции для уровня иерархии с учётом родительских фильтров.
    
    Args:
        df: DataFrame с данными
        level_key: ключ уровня (например, 'ТМ')
        parent_filters: dict с фильтрами родительских уровней
        
    Returns:
        list: отсортированный список уникальных значений
        
    Пример:
        get_hierarchy_options(df, 'ТМ', {'БЕ': ['1000'], 'ЗАВОД': ['Завод1']})
    """
    df_filtered = df
    
    # Применяем фильтры родительских уровней
    for parent_key, parent_values in parent_filters.items():
        if parent_values and parent_key in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[parent_key].isin(parent_values)]
    
    # Проверяем наличие колонки
    if level_key not in df_filtered.columns:
        return []
    
    # Получаем уникальные значения, исключая пустые
    options = df_filtered[level_key].dropna().unique()
    options = [x for x in options if str(x) not in ['Н/Д', 'nan', 'None', '', 'Не присвоено']]
    
    return sorted(options)


def apply_hierarchy_filters(df, hierarchy_filters):
    """
    Применить иерархические фильтры к DataFrame.
    
    Args:
        df: DataFrame с данными
        hierarchy_filters: dict вида {'БЕ': [...], 'ЗАВОД': [...], ...}
        
    Returns:
        DataFrame: отфильтрованные данные
    """
    df_filtered = df
    
    for level in HIERARCHY_LEVELS:
        key = level['key']
        if key in hierarchy_filters and hierarchy_filters[key]:
            if key in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[key].isin(hierarchy_filters[key])]
    
    return df_filtered


def build_breadcrumb(hierarchy_filters):
    """
    Построить строку навигации (хлебные крошки).
    
    Args:
        hierarchy_filters: dict с активными фильтрами
        
    Returns:
        str: строка вида "🏢 БЕ: 1000 → 🏭 Завод: Завод1 → ..."
    """
    parts = []
    
    for level in HIERARCHY_LEVELS:
        key = level['key']
        if key in hierarchy_filters and hierarchy_filters[key]:
            values = hierarchy_filters[key]
            if len(values) == 1:
                parts.append(f"{level['icon']} {level['name']}: {values[0]}")
            else:
                parts.append(f"{level['icon']} {level['name']}: ({len(values)} шт)")
    
    if not parts:
        return "📊 Все данные (без фильтров)"
    
    return " → ".join(parts)
