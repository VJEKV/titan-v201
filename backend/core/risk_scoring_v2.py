# -*- coding: utf-8 -*-
"""
core/risk_scoring_v2.py — Непрерывный риск-скоринг v2 (шкала 0-10)

Линейная интерполяция: value=порог → 5 баллов, 2×порог → 10 баллов.
Priority_Score = Methods_Total × Multiplier + DQ_Risk × 0.8
Категории: Красный >7, Жёлтый 4-7, Серый 1-4, Зелёный <1
"""

import pandas as pd
import numpy as np
from config.constants import METHODS_RISK

# Множитель по количеству сработавших методов
MULTIPLIERS = {0: 0.0, 1: 1.0, 2: 1.3, 3: 1.7, 4: 2.2, 5: 2.5, 6: 3.0}

EMPTY_EO_VALUES = {
    'Н/Д', 'н/д', 'НД', 'нд',
    'Не присвоено', 'не присвоено', 'Не присв', 'не присв',
    'nan', 'NaN', 'NAN', 'None', 'none', 'NONE', 'null', 'NULL',
    '', ' ', '-', '0.0',
    'Пусто', 'пусто', 'ПУСТО',
}


def is_empty_eo_mask(series):
    """Векторизованная проверка: ЕО пустое/неинформативное.

    Возвращает pd.Series[bool] — True где ЕО пустое.
    Фильтрует: NaN, None, пустые строки, Н/Д, НД, Не присвоено,
    ПУСТО, null, 0, -, строки из одних нулей, длина < 3.
    Без .apply() — полностью векторизовано.
    """
    # NaN/None → пустое
    is_na = series.isna()
    # Приведение к строке + strip
    s = series.astype(str).str.strip()
    # Точное совпадение с известными пустыми значениями
    in_empty_set = s.isin(EMPTY_EO_VALUES)
    # Строка состоит только из нулей (0, 00, 000, ...)
    only_zeros = (s.str.len() > 0) & (s.str.replace('0', '', regex=False) == '')
    # Строки короче 3 символов — не валидный код ЕО
    too_short = s.str.len() < 3
    return is_na | in_empty_set | only_zeros | too_short


def _is_empty_eo(val):
    """Скалярная проверка для единичных значений (для iterrows и подобного).

    Для массовой обработки используй is_empty_eo_mask(series).
    """
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return True
    s = str(val).strip()
    if not s or s in EMPTY_EO_VALUES:
        return True
    if s.replace('0', '') == '':
        return True
    if len(s) < 3:
        return True
    return False


def linear_score(value, threshold):
    """Линейный скоринг: value=threshold → 5, 2×threshold → 10."""
    if threshold <= 0 or pd.isna(value):
        return 0.0
    score = (value / threshold) * 5.0
    return min(max(score, 0.0), 10.0)


def _score_c1m1(df, threshold):
    """C1-M1: Перерасход бюджета — непрерывный балл."""
    plan = df['Plan_N'].replace(0, np.nan)
    pct_overrun = ((df['Fact_N'] / plan) - 1) * 100
    pct_overrun = pct_overrun.clip(lower=0).fillna(0)
    scores = (pct_overrun / threshold) * 5.0
    return scores.clip(0, 10).fillna(0)


def _score_c1m6(df, threshold, agg):
    """C1-M6: Аномалия по истории ТМ — непрерывный балл."""
    scores = pd.Series(0.0, index=df.index)
    if not agg or 'median_by_tm' not in agg:
        return scores
    median_mapped = df['ТМ'].map(agg['median_by_tm']).fillna(0)
    # ratio = Fact_N / (median * threshold/100)
    denom = median_mapped * (threshold / 100)
    denom = denom.replace(0, np.nan)
    ratio = df['Fact_N'] / denom
    # ratio=1 значит на пороге → 5 баллов, ratio=2 → 10 баллов
    scores = (ratio * 5.0).fillna(0).clip(0, 10)
    return scores


def _score_c1m9(df):
    """C1-M9: Незавершённые работы — бинарный (0 или 5)."""
    mask = df['STAT'].str.contains(
        'ОТКР|Внутреннее планирование|В работе',
        na=False, regex=True
    )
    return mask.astype(float) * 5.0


def _score_c2m2(df, threshold, agg):
    """C2-M2: Проблемное оборудование — непрерывный балл. Только заказы с реальным ЕО.

    Жёсткая фильтрация: все строки где ЕО пустое, None, NaN, nan, Н/Д, НД,
    Не присвоено, пусто, null, 0, -, из одних нулей, длина < 3 — ИСКЛЮЧАЮТСЯ.

    Возвращает кортеж (scores, orders_without_eo).
    """
    scores = pd.Series(0.0, index=df.index)
    orders_without_eo = 0

    if not agg:
        return scores, orders_without_eo

    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df.columns else 'ЕО'
    if eo_col not in df.columns:
        return scores, orders_without_eo

    # Жёсткая фильтрация — векторизованная (без .apply)
    has_eo = ~is_empty_eo_mask(df[eo_col])
    orders_without_eo = int((~has_eo).sum())

    # Пересчитываем count_by_eo ТОЛЬКО для строк с реальным ЕО
    df_valid_eo = df[has_eo]
    if len(df_valid_eo) == 0:
        return scores, orders_without_eo
    valid_count_by_eo = df_valid_eo[eo_col].value_counts().to_dict()

    eo_count = df[eo_col].map(valid_count_by_eo).fillna(0)
    raw_scores = (eo_count / threshold) * 5.0
    scores = (raw_scores * has_eo.astype(float)).clip(0, 10).fillna(0)
    return scores, orders_without_eo


def _score_new9(df, threshold):
    """NEW-9: Формальное закрытие в декабре — непрерывный балл."""
    scores = pd.Series(0.0, index=df.index)
    required = ['Факт_Конец', 'Конец', 'Факт_Длит', 'План_Длит']
    if not all(c in df.columns for c in required):
        return scores
    try:
        is_dec = df['Факт_Конец'].dt.month == 12
        not_planned_dec = df['Конец'].dt.month != 12
        plan_dur = pd.to_numeric(df['План_Длит'], errors='coerce').fillna(0)
        fact_dur = pd.to_numeric(df['Факт_Длит'], errors='coerce').fillna(0)
        valid = (plan_dur > 0) & (fact_dur >= 0) & is_dec & not_planned_dec

        # ratio = plan_dur / fact_dur — чем быстрее закрыт, тем выше
        coeff = threshold / 100
        speed_ratio = plan_dur / fact_dur.replace(0, np.nan)
        # Если fact_dur < plan_dur * coeff → подозрительно
        # Скоринг: нормализуем по порогу
        raw = (speed_ratio / (1 / coeff)) * 5.0
        scores = (raw * valid.astype(float)).fillna(0).clip(0, 10)
    except Exception:
        pass
    return scores


def _score_new10(df, threshold):
    """NEW-10: Возвраты статусов — непрерывный балл."""
    if 'N_STATUS_RETURNS' not in df.columns:
        return pd.Series(0.0, index=df.index)
    returns = pd.to_numeric(df['N_STATUS_RETURNS'], errors='coerce').fillna(0)
    scores = (returns / threshold) * 5.0
    return scores.clip(0, 10).fillna(0)


def compute_dq_risk(df):
    """Вычисляет DQ_Risk (0-10) на основе Data_Completeness."""
    if 'Data_Completeness' not in df.columns:
        return pd.Series(0.0, index=df.index)
    completeness = pd.to_numeric(df['Data_Completeness'], errors='coerce').fillna(0)
    # DQ_Risk = 10 * (1 - completeness/100)
    dq = (1 - completeness / 100) * 10
    return dq.clip(0, 10)


def apply_risk_scoring_v2(df, agg, thresholds):
    """Применить непрерывный риск-скоринг v2 к DataFrame.

    Добавляет колонки:
    - Score_<method> — непрерывный балл 0-10 для каждого метода
    - S_<method> — бинарный флаг (балл > 0)
    - Methods_Total — взвешенная сумма баллов
    - Methods_Count — количество сработавших методов
    - DQ_Risk — качество данных (0-10)
    - Priority_Score — итоговый приоритет
    - Risk_Category — категория (Красный/Жёлтый/Серый/Зелёный)
    - Risk_Sum — для обратной совместимости
    """
    df = df.copy()

    method_scores = {}
    extra_info = {}  # Дополнительная информация от методов

    # C2-M2 возвращает кортеж (scores, orders_without_eo)
    c2m2_result = _score_c2m2(df, thresholds.get("C2-M2: Проблемное оборудование", 5), agg)
    extra_info['orders_without_eo'] = c2m2_result[1]

    method_funcs = {
        "C1-M1: Перерасход бюджета": lambda: _score_c1m1(df, thresholds.get("C1-M1: Перерасход бюджета", 20)),
        "C1-M6: Аномалия по истории ТМ": lambda: _score_c1m6(df, thresholds.get("C1-M6: Аномалия по истории ТМ", 140), agg),
        "C1-M9: Незавершённые работы": lambda: _score_c1m9(df),
        "C2-M2: Проблемное оборудование": lambda: c2m2_result[0],
        "NEW-9: Формальное закрытие в декабре": lambda: _score_new9(df, thresholds.get("NEW-9: Формальное закрытие в декабре", 50)),
        "NEW-10: Возвраты статусов": lambda: _score_new10(df, thresholds.get("NEW-10: Возвраты статусов", 3)),
    }

    methods_total = pd.Series(0.0, index=df.index)
    methods_count = pd.Series(0, index=df.index)

    for method_name, method_info in METHODS_RISK.items():
        weight = method_info.get('weight', 1)
        score_func = method_funcs.get(method_name)
        if score_func:
            score = score_func()
        else:
            score = pd.Series(0.0, index=df.index)

        col_score = f"Score_{method_name}"
        col_flag = f"S_{method_name}"
        df[col_score] = score.round(2)
        df[col_flag] = (score >= 5.0).astype(bool)

        methods_total += score * weight
        methods_count += (score >= 5.0).astype(int)
        method_scores[method_name] = score

    # DQ_Risk
    df['DQ_Risk'] = compute_dq_risk(df).round(2)

    # Multiplier по количеству сработавших методов
    multiplier = methods_count.clip(0, 6).map(MULTIPLIERS).fillna(1.0)

    # Priority_Score = Methods_Total × Multiplier + DQ_Risk × 0.8
    df['Methods_Total'] = methods_total.round(2)
    df['Methods_Count'] = methods_count
    df['Priority_Score'] = (methods_total * multiplier + df['DQ_Risk'] * 0.8).round(2)

    # Категории
    df['Risk_Category'] = 'Зелёный'
    df.loc[df['Priority_Score'] >= 1, 'Risk_Category'] = 'Серый'
    df.loc[df['Priority_Score'] >= 4, 'Risk_Category'] = 'Жёлтый'
    df.loc[df['Priority_Score'] >= 7, 'Risk_Category'] = 'Красный'

    # Обратная совместимость — Risk_Sum = Priority_Score (нормализованный 0-10)
    max_ps = df['Priority_Score'].max()
    if max_ps > 0:
        df['Risk_Sum'] = ((df['Priority_Score'] / max_ps) * 10).round(1)
    else:
        df['Risk_Sum'] = 0.0

    return df, extra_info


def _self_test():
    """Самотест математики всех методов с print-выводом."""
    print("\n" + "="*60)
    print("САМОТЕСТ РИСК-СКОРИНГА v2")
    print("="*60)

    # Тест linear_score
    print("\n--- linear_score ---")
    print(f"  linear_score(20, 20) = {linear_score(20, 20)} (ожидается 5.0)")
    print(f"  linear_score(40, 20) = {linear_score(40, 20)} (ожидается 10.0)")
    print(f"  linear_score(10, 20) = {linear_score(10, 20)} (ожидается 2.5)")
    print(f"  linear_score(0, 20)  = {linear_score(0, 20)} (ожидается 0.0)")
    print(f"  linear_score(60, 20) = {linear_score(60, 20)} (ожидается 10.0, cap)")

    # Тестовый DataFrame
    df_test = pd.DataFrame({
        'ID': ['001', '002', '003', '004', '005'],
        'Plan_N': [100000, 80000, 0, 50000, 200000],
        'Fact_N': [130000, 60000, 10000, 120000, 150000],
        'ТМ': ['TM1', 'TM1', 'TM2', 'TM2', 'TM1'],
        'EQUNR_Код': ['EQ001', 'EQ001', 'EQ001', '', 'Н/Д'],
        'ЕО': ['Насос НЦВ-10', 'Насос НЦВ-10', 'Насос НЦВ-10', '', 'Н/Д'],
        'STAT': ['ЗАКР', 'ОТКР', 'В работе', 'ЗАКР', 'ЗАКР'],
        'Факт_Конец': pd.to_datetime(['2024-12-20', '2024-06-15', '2024-12-28', '2024-11-10', '2024-12-31']),
        'Конец': pd.to_datetime(['2024-03-15', '2024-06-15', '2024-09-01', '2024-11-10', '2024-06-30']),
        'План_Длит': [180, 120, 90, 60, 200],
        'Факт_Длит': [30, 120, 15, 60, 40],
        'N_STATUS_RETURNS': [0, 5, 2, 0, 8],
        'Data_Completeness': [90, 70, 50, 30, 80],
    })
    agg_test = {
        'median_by_tm': {'TM1': 100000, 'TM2': 50000},
        'count_by_eo': {'EQ001': 3},
    }

    # C1-M1: Перерасход бюджета (порог 20%)
    print("\n--- C1-M1: Перерасход бюджета (порог 20%) ---")
    s = _score_c1m1(df_test, 20)
    for i, v in enumerate(s):
        plan = df_test['Plan_N'].iloc[i]
        fact = df_test['Fact_N'].iloc[i]
        pct = ((fact / plan) - 1) * 100 if plan > 0 else 0
        print(f"  Заказ {i+1}: план={plan} факт={fact} перерасход={pct:.1f}% → балл={v:.2f}")

    # C1-M6: Аномалия ТМ (порог 140%)
    print("\n--- C1-M6: Аномалия по истории ТМ (порог 140%) ---")
    s = _score_c1m6(df_test, 140, agg_test)
    for i, v in enumerate(s):
        tm = df_test['ТМ'].iloc[i]
        fact = df_test['Fact_N'].iloc[i]
        median = agg_test['median_by_tm'].get(tm, 0)
        print(f"  Заказ {i+1}: ТМ={tm} факт={fact} медиана={median} → балл={v:.2f}")

    # C1-M9: Незавершённые
    print("\n--- C1-M9: Незавершённые работы ---")
    s = _score_c1m9(df_test)
    for i, v in enumerate(s):
        stat = df_test['STAT'].iloc[i]
        print(f"  Заказ {i+1}: STAT={stat} → балл={v:.2f}")

    # C2-M2: Проблемное ЕО (порог 5)
    print("\n--- C2-M2: Проблемное оборудование (порог 5) ---")
    s, without_eo = _score_c2m2(df_test, 5, agg_test)
    for i, v in enumerate(s):
        eo = df_test['EQUNR_Код'].iloc[i]
        print(f"  Заказ {i+1}: ЕО='{eo}' → балл={v:.2f}")
    print(f"  Заказов без ЕО: {without_eo}")

    # NEW-9: Формальное закрытие в декабре (порог 50%)
    print("\n--- NEW-9: Формальное закрытие в декабре (порог 50%) ---")
    s = _score_new9(df_test, 50)
    for i, v in enumerate(s):
        end_month = df_test['Факт_Конец'].iloc[i].month
        plan_end_month = df_test['Конец'].iloc[i].month
        p_dur = df_test['План_Длит'].iloc[i]
        f_dur = df_test['Факт_Длит'].iloc[i]
        print(f"  Заказ {i+1}: факт_конец={end_month} план_конец={plan_end_month} план_длит={p_dur} факт_длит={f_dur} → балл={v:.2f}")

    # NEW-10: Возвраты статусов (порог 3)
    print("\n--- NEW-10: Возвраты статусов (порог 3) ---")
    s = _score_new10(df_test, 3)
    for i, v in enumerate(s):
        returns = df_test['N_STATUS_RETURNS'].iloc[i]
        print(f"  Заказ {i+1}: возвратов={returns} → балл={v:.2f}")

    # DQ_Risk
    print("\n--- DQ_Risk ---")
    dq = compute_dq_risk(df_test)
    for i, v in enumerate(dq):
        compl = df_test['Data_Completeness'].iloc[i]
        print(f"  Заказ {i+1}: полнота={compl}% → DQ_Risk={v:.2f}")

    print("\n" + "="*60)
    print("САМОТЕСТ ЗАВЕРШЁН")
    print("="*60 + "\n")


# _self_test()  # Раскомментировать для отладки
