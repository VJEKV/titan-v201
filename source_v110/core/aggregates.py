# -*- coding: utf-8 -*-
"""
core/aggregates.py — Расчёт агрегатов

ИЗМЕНЕНИЯ v111:
- count_by_eo: фильтрация пустых значений ужесточена
- count_by_tm остаётся для других целей (не для C2-M2)
"""

import pandas as pd


# Общий список пустых значений для ЕО
EMPTY_EO_VALUES = {
    'Н/Д', 'н/д', 'Не присвоено', 'не присвоено', 'Не присв',
    'nan', 'NaN', 'None', 'none', '', ' ', '0', 'Пусто', 'пусто'
}


def compute_aggregates(df):
    """
    Расчёт агрегатов для методов риск-скоринга.
    """
    agg = {}
    
    # Средний факт по видам заказов
    if 'Вид' in df.columns and 'Fact_N' in df.columns:
        agg['mean_by_vid'] = df.groupby('Вид')['Fact_N'].mean().to_dict()
    else:
        agg['mean_by_vid'] = {}
    
    # Средний план
    if 'Plan_N' in df.columns:
        agg['mean_plan'] = float(df['Plan_N'].mean())
    else:
        agg['mean_plan'] = 0.0
    
    # Медиана факта по ТМ (для C1-M6)
    if 'ТМ' in df.columns and 'Fact_N' in df.columns:
        agg['median_by_tm'] = df.groupby('ТМ')['Fact_N'].median().to_dict()
    else:
        agg['median_by_tm'] = {}
    
    # Количество заказов по ТМ (для общей аналитики)
    if 'ТМ' in df.columns and 'ID' in df.columns:
        agg['count_by_tm'] = df.groupby('ТМ')['ID'].count().to_dict()
    else:
        agg['count_by_tm'] = {}
    
    # ========================================
    # Количество заказов по ЕО (для C2-M2)
    # ТОЛЬКО валидные коды ЕО!
    # ========================================
    if 'EQUNR_Код' in df.columns and 'ID' in df.columns:
        df_valid_eo = df[~df['EQUNR_Код'].astype(str).str.strip().isin(EMPTY_EO_VALUES)]
        agg['count_by_eo'] = df_valid_eo.groupby('EQUNR_Код')['ID'].count().to_dict()
    elif 'ЕО' in df.columns and 'ID' in df.columns:
        df_valid_eo = df[~df['ЕО'].astype(str).str.strip().isin(EMPTY_EO_VALUES)]
        agg['count_by_eo'] = df_valid_eo.groupby('ЕО')['ID'].count().to_dict()
    else:
        agg['count_by_eo'] = {}
    
    # Агрегаты по плановикам
    if 'INGRP' in df.columns and 'ID' in df.columns:
        agg['count_by_ingrp'] = df.groupby('INGRP')['ID'].count().to_dict()
    else:
        agg['count_by_ingrp'] = {}
    
    # Агрегаты по авторам
    if 'USER' in df.columns and 'ID' in df.columns:
        agg['count_by_user'] = df.groupby('USER')['ID'].count().to_dict()
    else:
        agg['count_by_user'] = {}
    
    # Агрегаты по рабочим местам
    if 'РМ' in df.columns and 'ID' in df.columns:
        agg['count_by_rm'] = df.groupby('РМ')['ID'].count().to_dict()
    else:
        agg['count_by_rm'] = {}
    
    return agg
