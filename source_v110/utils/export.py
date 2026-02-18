# -*- coding: utf-8 -*-
"""
utils/export.py — Экспорт данных в Excel

ВАЖНО: Требует openpyxl (pip install openpyxl)
"""

import pandas as pd
from io import BytesIO


def create_excel_download(df, filename_prefix="export"):
    """
    Создать Excel-файл (.xlsx) для скачивания.
    
    Args:
        df: DataFrame для экспорта
        filename_prefix: префикс имени файла (без расширения)
        
    Returns:
        BytesIO: буфер с Excel-файлом для st.download_button
    """
    output = BytesIO()
    
    # Явно указываем engine='openpyxl' для .xlsx
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Данные')
    except ModuleNotFoundError:
        # Если openpyxl не установлен - пробуем xlsxwriter
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Данные')
    
    output.seek(0)
    return output


def create_multi_sheet_excel(sheets_dict):
    """
    Создать Excel-файл с несколькими листами.
    
    Args:
        sheets_dict: словарь {'Имя листа': DataFrame, ...}
        
    Returns:
        BytesIO: буфер с Excel-файлом
    """
    output = BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in sheets_dict.items():
                safe_name = sheet_name[:31]
                df.to_excel(writer, index=False, sheet_name=safe_name)
    except ModuleNotFoundError:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet_name, df in sheets_dict.items():
                safe_name = sheet_name[:31]
                df.to_excel(writer, index=False, sheet_name=safe_name)
    
    output.seek(0)
    return output
