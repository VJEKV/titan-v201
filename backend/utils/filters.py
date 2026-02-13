# -*- coding: utf-8 -*-
"""
utils/filters.py — Работа с фильтрами
"""

import pandas as pd
from config.constants import HIERARCHY_LEVELS


def get_hierarchy_options(df, level_key, parent_filters):
    """Получить доступные опции для уровня иерархии."""
    df_filtered = df
    for parent_key, parent_values in parent_filters.items():
        if parent_values and parent_key in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[parent_key].isin(parent_values)]
    if level_key not in df_filtered.columns:
        return []
    options = df_filtered[level_key].dropna().unique()
    options = [x for x in options if str(x) not in ['Н/Д', 'nan', 'None', '', 'Не присвоено']]
    return sorted(options)


def apply_hierarchy_filters(df, hierarchy_filters):
    """Применить иерархические фильтры к DataFrame."""
    df_filtered = df
    for level in HIERARCHY_LEVELS:
        key = level['key']
        if key in hierarchy_filters and hierarchy_filters[key]:
            if key in df_filtered.columns:
                df_filtered = df_filtered[df_filtered[key].isin(hierarchy_filters[key])]
    return df_filtered


def apply_extra_filters(df, extra_filters):
    """Применить дополнительные фильтры."""
    mask = pd.Series(True, index=df.index)

    search = extra_filters.get('search', '')
    if search:
        search_mask = pd.Series(False, index=df.index)
        for col in ['ID', 'Текст', 'ТМ', 'ЕО']:
            if col in df.columns:
                search_mask |= df[col].astype(str).str.contains(search, case=False, na=False)
        mask &= search_mask

    for key, col in [('vid', 'Вид'), ('abc', 'ABC'), ('stat', 'STAT'),
                     ('rm', 'РМ'), ('ingrp', 'INGRP')]:
        values = extra_filters.get(key, [])
        if values and col in df.columns:
            mask &= df[col].isin(values)

    # Фильтр по датам (Начало — план. начало заказа)
    date_from = extra_filters.get('date_from', '')
    date_to = extra_filters.get('date_to', '')
    if (date_from or date_to) and 'Начало' in df.columns:
        dates = pd.to_datetime(df['Начало'], errors='coerce')
        if date_from:
            try:
                mask &= dates >= pd.Timestamp(date_from)
            except Exception:
                pass
        if date_to:
            try:
                mask &= dates <= pd.Timestamp(date_to)
            except Exception:
                pass

    return df[mask]


def build_breadcrumb(hierarchy_filters):
    """Построить строку навигации."""
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
        return "Все данные (без фильтров)"
    return " \u2192 ".join(parts)
