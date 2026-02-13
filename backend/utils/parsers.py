# -*- coding: utf-8 -*-
"""
utils/parsers.py — Парсинг данных

Функции для преобразования данных из выгрузки SAP.
"""

import pandas as pd


def fast_parse_series(series):
    """
    Быстрый парсинг числовой серии.

    Обрабатывает пробелы (разделители разрядов), запятые (десятичные).
    '1 234,56' → 1234.56
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

    Обрабатывает ISO формат с timezone (Z, +00:00), различные форматы дат.
    """
    try:
        parsed = pd.to_datetime(series, errors='coerce', utc=True)
        if parsed.dt.tz is not None:
            parsed = parsed.dt.tz_convert(None)
        return parsed
    except Exception:
        try:
            cleaned = series.astype(str).str.replace('Z', '').str.replace('T', ' ')
            return pd.to_datetime(cleaned, errors='coerce')
        except Exception:
            return pd.NaT
