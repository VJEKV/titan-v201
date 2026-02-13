# -*- coding: utf-8 -*-
"""
core/data_loader.py — Загрузка данных
"""

import pandas as pd
from io import BytesIO


def load_file(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    """Загрузка Excel/CSV файла из байтов."""
    buf = BytesIO(file_bytes)
    if file_name.endswith('.csv'):
        try:
            return pd.read_csv(buf, encoding='utf-8', sep=';', on_bad_lines='skip')
        except Exception:
            buf.seek(0)
            try:
                return pd.read_csv(buf, encoding='cp1251', sep=';', on_bad_lines='skip')
            except Exception:
                buf.seek(0)
                return pd.read_csv(buf, encoding='cp1251', sep=',', on_bad_lines='skip')
    else:
        return pd.read_excel(buf, engine='calamine')


def detect_export_format(df):
    """Определение формата выгрузки SAP."""
    new_format_cols = ['ISTAT', 'ISTAT_TXT', 'PMCOALLP', 'PMCOALLF', 'AUFNR']
    has_new_cols = all(col in df.columns for col in new_format_cols)

    if has_new_cols:
        if df['AUFNR'].nunique() < len(df):
            return 'NEW_STATUS_HISTORY'

    return 'LEGACY'
