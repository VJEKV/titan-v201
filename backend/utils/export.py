# -*- coding: utf-8 -*-
"""
utils/export.py — Экспорт данных в Excel
"""

import pandas as pd
from io import BytesIO


def create_excel_download(df, filename_prefix="export"):
    """Создать Excel-файл (.xlsx) для скачивания."""
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Данные')
    except ModuleNotFoundError:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Данные')
    output.seek(0)
    return output
