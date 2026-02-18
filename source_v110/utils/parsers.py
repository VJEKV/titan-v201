# -*- coding: utf-8 -*-
"""
utils/parsers.py — Парсинг данных

Функции для преобразования данных из выгрузки SAP.
"""

import pandas as pd


def fast_parse_series(series):
    """
    Быстрый парсинг числовой серии.
    
    Обрабатывает:
    - Пробелы и неразрывные пробелы (разделители разрядов)
    - Запятые как десятичные разделители
    - Некорректные значения → 0.0
    
    Пример:
        fast_parse_series(pd.Series(["1 234,56", "abc", None]))
        → pd.Series([1234.56, 0.0, 0.0])
    """
    return pd.to_numeric(
        series.astype(str)
              .str.replace(r'[\s\xa0\u202f\u00A0]+', '', regex=True)
              .str.replace(',', '.'),
        errors='coerce'
    ).fillna(0.0)


def safe_parse_datetime(series):
    """
    Безопасный парсинг datetime с обработкой timezone.
    
    Обрабатывает:
    - ISO формат с timezone (Z, +00:00)
    - Различные форматы дат
    - Некорректные значения → NaT
    
    Пример:
        safe_parse_datetime(pd.Series(["2024-01-15T10:30:00Z", "15.01.2024"]))
    """
    try:
        # Пробуем парсинг с UTC
        parsed = pd.to_datetime(series, errors='coerce', utc=True)
        # Убираем timezone для совместимости
        if parsed.dt.tz is not None:
            parsed = parsed.dt.tz_convert(None)
        return parsed
    except Exception:
        try:
            # Fallback: убираем Z и T вручную
            cleaned = series.astype(str).str.replace('Z', '').str.replace('T', ' ')
            return pd.to_datetime(cleaned, errors='coerce')
        except:
            return pd.NaT
