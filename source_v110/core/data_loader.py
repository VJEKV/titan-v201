# -*- coding: utf-8 -*-
"""
core/data_loader.py — Загрузка данных

Загрузка Excel/CSV файлов, определение формата выгрузки.
"""

import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def load_file(file_obj, file_name):
    if file_name.endswith('.csv'):
        try:
            return pd.read_csv(file_obj, encoding='utf-8', sep=';', on_bad_lines='skip')
        except:
            file_obj.seek(0)
            try:
                return pd.read_csv(file_obj, encoding='cp1251', sep=';', on_bad_lines='skip')
            except:
                file_obj.seek(0)
                return pd.read_csv(file_obj, encoding='cp1251', sep=',', on_bad_lines='skip')
    else:
        return pd.read_excel(file_obj, engine='calamine')


def detect_export_format(df):
    """
    Определение формата выгрузки SAP.
    
    Форматы:
    - NEW_STATUS_HISTORY: новый формат с историей статусов (ISTAT, ISTAT_TXT)
    - LEGACY: старый формат (один заказ = одна строка)
    
    Args:
        df: DataFrame с сырыми данными
        
    Returns:
        str: 'NEW_STATUS_HISTORY' или 'LEGACY'
    """
    # Признаки нового формата
    new_format_cols = ['ISTAT', 'ISTAT_TXT', 'PMCOALLP', 'PMCOALLF', 'AUFNR']
    has_new_cols = all(col in df.columns for col in new_format_cols)
    
    if has_new_cols:
        # Проверяем есть ли дубликаты AUFNR (признак истории статусов)
        if df['AUFNR'].nunique() < len(df):
            return 'NEW_STATUS_HISTORY'
    
    return 'LEGACY'
