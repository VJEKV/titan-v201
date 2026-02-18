# -*- coding: utf-8 -*-
"""
core/risk_scoring.py — Логика методов риск-скоринга

6 методов: C1-M1, C1-M6, C1-M9, C2-M2, NEW-9, NEW-10

ИЗМЕНЕНИЯ v111:
- C2-M2: УБРАН fallback по ТМ (давал ложные срабатывания на 90%+ заказов)
- C2-M2: работает ТОЛЬКО по коду ЕО (EQUNR_Код)
- C2-M2: заказы без ЕО — НЕ помечаются (нет оборудования — нет анализа)
"""

import pandas as pd
from config.constants import METHODS_RISK


def check_method_has_data(df, method_name):
    """Проверка наличия данных для метода."""
    method = METHODS_RISK.get(method_name, {})
    required = method.get('requires_fields', [])
    
    for field in required:
        if field not in df.columns:
            return False, f"Нет поля: {field}"
        if field in ['N_STATUS_RETURNS', 'N_STATUS_CHANGES']:
            if field not in df.columns:
                return False, "Нужен новый формат выгрузки"
    
    return True, "OK"


# Общий список пустых значений для ЕО
EMPTY_EO_VALUES = {
    'Н/Д', 'н/д', 'Не присвоено', 'не присвоено', 'Не присв',
    'nan', 'NaN', 'None', 'none', '', ' ', '0', 'Пусто', 'пусто'
}


def _check_problem_equipment(df, threshold, agg):
    """
    C2-M2: Проблемное оборудование.
    
    Логика v111:
    - Работает ТОЛЬКО по коду ЕО (EQUNR_Код или ЕО)
    - Заказы без ЕО НЕ помечаются (fallback по ТМ УБРАН)
    - Срабатывает если количество заказов на ЕО > порог
    
    Причина убирания fallback по ТМ:
    У большинства ТМ количество заказов >> порога (5),
    что приводило к ложному срабатыванию на 90%+ заказов без ЕО.
    """
    result = pd.Series(False, index=df.index)
    
    if not agg:
        return result
    
    count_by_eo = agg.get('count_by_eo', {})
    if not count_by_eo:
        return result
    
    # Работаем ТОЛЬКО по ЕО
    if 'EQUNR_Код' in df.columns:
        eo_str = df['EQUNR_Код'].astype(str).str.strip()
        has_eo = ~eo_str.isin(EMPTY_EO_VALUES)
        eo_count = df['EQUNR_Код'].map(count_by_eo).fillna(0)
        result = has_eo & (eo_count > threshold)
    elif 'ЕО' in df.columns:
        eo_str = df['ЕО'].astype(str).str.strip()
        has_eo = ~eo_str.isin(EMPTY_EO_VALUES)
        eo_count = df['ЕО'].map(count_by_eo).fillna(0)
        result = has_eo & (eo_count > threshold)
    
    return result


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


def _check_december_formal(df, threshold):
    """Проверка формального закрытия в декабре."""
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
