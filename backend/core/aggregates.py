# -*- coding: utf-8 -*-
"""
core/aggregates.py — Расчёт агрегатов
"""

import pandas as pd

from core.risk_scoring_v2 import is_empty_eo_mask


def compute_aggregates(df):
    """Расчёт агрегатов для методов риск-скоринга."""
    agg = {}

    if 'Вид' in df.columns and 'Fact_N' in df.columns:
        agg['mean_by_vid'] = df.groupby('Вид')['Fact_N'].mean().to_dict()
    else:
        agg['mean_by_vid'] = {}

    if 'Plan_N' in df.columns:
        agg['mean_plan'] = float(df['Plan_N'].mean())
    else:
        agg['mean_plan'] = 0.0

    if 'ТМ' in df.columns and 'Fact_N' in df.columns:
        agg['median_by_tm'] = df.groupby('ТМ')['Fact_N'].median().to_dict()
    else:
        agg['median_by_tm'] = {}

    if 'ТМ' in df.columns and 'ID' in df.columns:
        agg['count_by_tm'] = df.groupby('ТМ')['ID'].count().to_dict()
    else:
        agg['count_by_tm'] = {}

    # Подсчёт заказов по ЕО — векторизованная фильтрация (без .apply)
    if 'EQUNR_Код' in df.columns and 'ID' in df.columns:
        df_valid_eo = df[~is_empty_eo_mask(df['EQUNR_Код'])]
        agg['count_by_eo'] = df_valid_eo.groupby('EQUNR_Код')['ID'].count().to_dict()
    elif 'ЕО' in df.columns and 'ID' in df.columns:
        df_valid_eo = df[~is_empty_eo_mask(df['ЕО'])]
        agg['count_by_eo'] = df_valid_eo.groupby('ЕО')['ID'].count().to_dict()
    else:
        agg['count_by_eo'] = {}

    if 'INGRP' in df.columns and 'ID' in df.columns:
        agg['count_by_ingrp'] = df.groupby('INGRP')['ID'].count().to_dict()
    else:
        agg['count_by_ingrp'] = {}

    if 'USER' in df.columns and 'ID' in df.columns:
        agg['count_by_user'] = df.groupby('USER')['ID'].count().to_dict()
    else:
        agg['count_by_user'] = {}

    if 'РМ' in df.columns and 'ID' in df.columns:
        agg['count_by_rm'] = df.groupby('РМ')['ID'].count().to_dict()
    else:
        agg['count_by_rm'] = {}

    return agg
