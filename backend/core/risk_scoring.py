# -*- coding: utf-8 -*-
"""
core/risk_scoring.py — Логика методов риск-скоринга (6 методов)
"""

import pandas as pd
from config.constants import METHODS_RISK
from core.risk_scoring_v2 import is_empty_eo_mask


def _check_problem_equipment(df, threshold, agg):
    """C2-M2: Проблемное оборудование (только по ЕО).

    Использует единую векторизованную фильтрацию is_empty_eo_mask.
    """
    result = pd.Series(False, index=df.index)
    if not agg:
        return result
    count_by_eo = agg.get('count_by_eo', {})
    if not count_by_eo:
        return result

    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df.columns else 'ЕО'
    if eo_col not in df.columns:
        return result

    has_eo = ~is_empty_eo_mask(df[eo_col])
    eo_count = df[eo_col].map(count_by_eo).fillna(0)
    result = has_eo & (eo_count > threshold)

    return result


def _check_december_formal(df, threshold):
    """NEW-9: Формальное закрытие в декабре."""
    result = pd.Series(False, index=df.index)

    has_fact_end = 'Факт_Конец' in df.columns
    has_plan_end = 'Конец' in df.columns
    has_fact_dur = 'Факт_Длит' in df.columns
    has_plan_dur = 'План_Длит' in df.columns

    if not (has_fact_end and has_plan_end and has_fact_dur and has_plan_dur):
        return result

    try:
        cond1 = df['Факт_Конец'].dt.month == 12
        cond2 = df['Конец'].dt.month != 12
        coeff = threshold / 100
        cond3 = df['Факт_Длит'] < (df['План_Длит'] * coeff)
        cond4 = df['План_Длит'] > 0
        cond5 = df['Факт_Длит'] >= 0
        result = cond1 & cond2 & cond3 & cond4 & cond5
    except Exception:
        pass

    return result.fillna(False)


def get_logic(name, agg=None, thresholds=None):
    """Получить функцию логики для метода."""
    logic = {
        "C1-M1: Перерасход бюджета":
            lambda d, p: (d['Fact_N'] / d['Plan_N'].replace(0, 1) - 1) * 100 > p,
        "C1-M6: Аномалия по истории ТМ":
            lambda d, p: (
                d['Fact_N'] > d['ТМ'].map(agg['median_by_tm']).fillna(0) * (p / 100)
                if agg and 'median_by_tm' in agg
                else pd.Series(False, index=d.index)
            ),
        "C1-M9: Незавершённые работы":
            lambda d, p: d['STAT'].str.contains(
                'ОТКР|Внутреннее планирование|В работе',
                na=False, regex=True
            ),
        "C2-M2: Проблемное оборудование":
            lambda d, p: _check_problem_equipment(d, p, agg),
        "NEW-9: Формальное закрытие в декабре":
            lambda d, p: _check_december_formal(d, p),
        "NEW-10: Возвраты статусов":
            lambda d, p: (
                d['N_STATUS_RETURNS'] > p
                if 'N_STATUS_RETURNS' in d.columns
                else pd.Series(False, index=d.index)
            )
    }
    return logic.get(name, lambda d, p: pd.Series(False, index=d.index))


def apply_risk_scoring(df, agg, thresholds):
    """Применить все методы риск-скоринга к DataFrame."""
    df = df.copy()
    df['Risk_Sum'] = 0

    for method_name, method_info in METHODS_RISK.items():
        flag = f"S_{method_name}"
        threshold = thresholds.get(method_name, method_info.get('threshold_default', 0))
        weight = method_info.get('weight', 1)

        logic_func = get_logic(method_name, agg, thresholds)

        try:
            df[flag] = logic_func(df, threshold).astype(bool)
        except Exception:
            df[flag] = False

        df['Risk_Sum'] += df[flag].astype(int) * weight

    return df
