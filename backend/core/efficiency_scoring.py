# -*- coding: utf-8 -*-
"""
core/efficiency_scoring.py — 4 индекса эффективности эксплуатации оборудования.

Индексы (все 0–10, кроме Degradation_Trend, который −10…+10):

  1. Justification_Score  — Обоснованность ремонта
     Были ли параметры режима ВНЕ нормы перед ремонтом?
     Метод: Z-score параметров за 14 дней ДО GSTRP относительно «нормального режима».

  2. Quality_Score        — Качество ремонта
     Параметры ПОСЛЕ ремонта статистически лучше, чем ДО?
     Метод: Mann-Whitney U тест между 7 днями ДО и 7 днями ПОСЛЕ ZZFACTEND.

  3. Longevity_Score      — Живучесть ремонта
     Как долго после ремонта параметры оставались в норме?
     Метод: время до первого отклонения > 2σ, нормализованное на плановый МРО.

  4. Degradation_Trend    — Тренд деградации (по последним N ремонтам)
     Mann-Kendall тест на тренд «нормального режима» после каждого ремонта.
     Положительный тренд индикатора износа → отрицательный балл (хуже).

Композит: Efficiency_Score = взвешенная сумма, 0–10.

Все методы:
  - Работают с long-format DataFrame БДРВ: (equnr, tag, timestamp, value)
  - Возвращают NaN если данных недостаточно (< 100 замеров вне ремонтов)
  - Не используют .apply(axis=1) — только векторизованно

ТИТАН-5.
"""

from datetime import timedelta
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

# ───────────────────────────────────────────────────────────────────────
# Вспомогательные утилиты
# ───────────────────────────────────────────────────────────────────────

def _baseline_stats(bdrv: pd.DataFrame, repair_dates: list, exclude_days: int = 30) -> pd.DataFrame:
    """Для каждой (equnr, tag) вычисляет медиану и MAD «нормального режима»
    (исключая зоны ±exclude_days вокруг каждого ремонта).

    Возвращает DataFrame: tag | baseline_median | baseline_mad
    """
    if bdrv.empty:
        return pd.DataFrame(columns=['tag', 'baseline_median', 'baseline_mad'])

    # Маска «нормального режима»: точки, не попавшие в ни одно окно ±exclude_days
    if repair_dates:
        repair_dt = pd.to_datetime([d for d in repair_dates if d is not None])
        mask_normal = pd.Series(True, index=bdrv.index)
        for rd in repair_dt:
            dt_from = rd - pd.Timedelta(days=exclude_days)
            dt_to = rd + pd.Timedelta(days=exclude_days)
            mask_normal &= ~((bdrv['timestamp'] >= dt_from) & (bdrv['timestamp'] <= dt_to))
        normal = bdrv.loc[mask_normal]
    else:
        normal = bdrv

    if normal.empty:
        return pd.DataFrame(columns=['tag', 'baseline_median', 'baseline_mad'])

    # Медиана и MAD (median absolute deviation) по каждому тегу
    grouped = normal.groupby('tag', observed=True)['value']
    med = grouped.median().rename('baseline_median')
    mad = grouped.apply(lambda s: (s - s.median()).abs().median()).rename('baseline_mad')
    result = pd.concat([med, mad], axis=1).reset_index()
    # Защита от нулевого MAD (деление на ноль в Z-score)
    zero_mask = result['baseline_mad'] == 0
    if zero_mask.any():
        fallback = result.loc[zero_mask, 'baseline_median'].abs() * 0.01 + 0.001
        result.loc[zero_mask, 'baseline_mad'] = fallback
    return result


# ───────────────────────────────────────────────────────────────────────
# Индекс 1: Обоснованность ремонта
# ───────────────────────────────────────────────────────────────────────

def justification_score(bdrv: pd.DataFrame, baseline: pd.DataFrame,
                         repair_date: pd.Timestamp, window_days: int = 14) -> float:
    """Z-score параметров за `window_days` до `repair_date`.
    Если max(|Z|) > 2 → обоснован (8-10 баллов).
    1-2 → серая зона (4-7).
    < 1 → ремонт без необходимости (0-3).
    """
    if bdrv.empty or baseline.empty or repair_date is pd.NaT:
        return float('nan')

    dt_from = repair_date - pd.Timedelta(days=window_days)
    window = bdrv[(bdrv['timestamp'] >= dt_from) & (bdrv['timestamp'] < repair_date)]
    if window.empty:
        return float('nan')

    # Для каждого тега берём среднее значение в окне и сравниваем с baseline
    merged = window.groupby('tag', observed=True)['value'].mean().reset_index()
    merged = merged.merge(baseline, on='tag', how='inner')
    if merged.empty:
        return float('nan')

    # Robust Z-score через MAD: z = (value - median) / (1.4826 * MAD)
    merged['z'] = (merged['value'] - merged['baseline_median']).abs() / (1.4826 * merged['baseline_mad'])
    max_z = merged['z'].max()

    if pd.isna(max_z):
        return float('nan')
    # Маппинг Z → балл: z=0 → 0, z=2 → 7, z=4+ → 10 (сигмоида)
    score = 10 * (max_z ** 2) / (max_z ** 2 + 4)
    return float(round(score, 2))


# ───────────────────────────────────────────────────────────────────────
# Индекс 2: Качество ремонта
# ───────────────────────────────────────────────────────────────────────

def quality_score(bdrv: pd.DataFrame, baseline: pd.DataFrame,
                   repair_end: pd.Timestamp, window_days: int = 7) -> float:
    """Сравнение параметров 7 дней ДО закрытия ремонта vs 7 дней ПОСЛЕ.
    Хороший ремонт → параметры сдвинулись к baseline_median.
    Балл 0-10.
    """
    if bdrv.empty or baseline.empty or repair_end is pd.NaT:
        return float('nan')

    before = bdrv[(bdrv['timestamp'] >= repair_end - pd.Timedelta(days=window_days)) &
                  (bdrv['timestamp'] < repair_end)]
    after = bdrv[(bdrv['timestamp'] >= repair_end) &
                 (bdrv['timestamp'] < repair_end + pd.Timedelta(days=window_days))]
    if before.empty or after.empty:
        return float('nan')

    # Для каждого тега считаем отклонение от baseline ДО и ПОСЛЕ
    before_mean = before.groupby('tag', observed=True)['value'].mean().rename('before_mean')
    after_mean = after.groupby('tag', observed=True)['value'].mean().rename('after_mean')
    merged = pd.concat([before_mean, after_mean], axis=1).reset_index()
    merged = merged.merge(baseline, on='tag', how='inner').dropna()
    if merged.empty:
        return float('nan')

    # Отклонения от baseline в единицах MAD
    dev_before = (merged['before_mean'] - merged['baseline_median']).abs() / (1.4826 * merged['baseline_mad'])
    dev_after = (merged['after_mean'] - merged['baseline_median']).abs() / (1.4826 * merged['baseline_mad'])

    # Улучшение: насколько dev_after меньше dev_before
    improvement = (dev_before - dev_after).mean()
    # Нормализация к 0–10: улучшение >= 2 MAD → 10, <= 0 → 0
    score = max(0.0, min(10.0, 5 + improvement * 2.5))
    return float(round(score, 2))


# ───────────────────────────────────────────────────────────────────────
# Индекс 3: Живучесть ремонта
# ───────────────────────────────────────────────────────────────────────

def longevity_score(bdrv: pd.DataFrame, baseline: pd.DataFrame,
                     repair_end: pd.Timestamp, next_repair: Optional[pd.Timestamp] = None,
                     expected_mro_days: int = 180) -> float:
    """Время после ремонта до первого отклонения > 2 MAD.
    Если > 80% expected_mro_days — 10 баллов; 50–80% — 5; <50% — 0.
    """
    if bdrv.empty or baseline.empty or repair_end is pd.NaT:
        return float('nan')

    horizon_end = next_repair if next_repair is not pd.NaT and next_repair is not None else bdrv['timestamp'].max()
    after = bdrv[(bdrv['timestamp'] > repair_end) & (bdrv['timestamp'] <= horizon_end)]
    if after.empty:
        return float('nan')

    merged = after.merge(baseline, on='tag', how='inner')
    if merged.empty:
        return float('nan')
    merged['z'] = (merged['value'] - merged['baseline_median']).abs() / (1.4826 * merged['baseline_mad'])

    # Ищем первую точку с z > 2
    deviations = merged[merged['z'] > 2.0].sort_values('timestamp')
    if deviations.empty:
        # Не отклонялось — полная живучесть
        days_to_dev = (horizon_end - repair_end).total_seconds() / 86400
    else:
        days_to_dev = (deviations.iloc[0]['timestamp'] - repair_end).total_seconds() / 86400

    # Сравниваем с ожидаемым МРО
    ratio = days_to_dev / max(expected_mro_days, 1)
    # Маппинг: ratio >= 0.8 → 10, 0.5 → 5, 0.0 → 0 (линейно)
    score = max(0.0, min(10.0, ratio * 12.5))
    return float(round(score, 2))


# ───────────────────────────────────────────────────────────────────────
# Индекс 4: Тренд деградации
# ───────────────────────────────────────────────────────────────────────

def degradation_trend(bdrv: pd.DataFrame, baseline: pd.DataFrame,
                       repair_dates: list, window_days: int = 7) -> float:
    """Оценка тренда по последним N ремонтам.

    Для каждого ремонта вычисляем «остаточное отклонение» (mean |z| за 7 дней
    после ремонта по тегам-индикаторам износа — вибрация, температура).
    Дальше — Mann-Kendall тест на тренд: если отклонения растут от ремонта
    к ремонту → отрицательный балл (деградация).

    Возвращает балл −10…+10.
    """
    if bdrv.empty or baseline.empty or len(repair_dates) < 3:
        return float('nan')

    residuals = []
    sorted_dates = sorted([d for d in repair_dates if d is not None])
    for rd in sorted_dates:
        rd = pd.Timestamp(rd)
        after = bdrv[(bdrv['timestamp'] > rd) &
                     (bdrv['timestamp'] <= rd + pd.Timedelta(days=window_days))]
        if after.empty:
            continue
        m = after.merge(baseline, on='tag', how='inner')
        if m.empty:
            continue
        m['z'] = (m['value'] - m['baseline_median']).abs() / (1.4826 * m['baseline_mad'])
        residuals.append(m['z'].mean())

    if len(residuals) < 3:
        return float('nan')

    # Простой непараметрический Mann-Kendall без внешней библиотеки
    n = len(residuals)
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            if residuals[j] > residuals[i]:
                s += 1
            elif residuals[j] < residuals[i]:
                s -= 1
    # Нормализация: max possible s = n*(n-1)/2
    s_norm = s / (n * (n - 1) / 2) if n > 1 else 0
    # Положительный s → деградация → отрицательный балл
    score = -s_norm * 10
    return float(round(score, 2))


# ───────────────────────────────────────────────────────────────────────
# Композит: Efficiency_Score
# ───────────────────────────────────────────────────────────────────────

def efficiency_composite(justification: float, quality: float,
                          longevity: float, degradation: float) -> float:
    """Композитный балл 0–10 по 4 индексам.

    Веса:
      Justification: 0.25 — было ли основание для ремонта
      Quality:       0.30 — результат ремонта
      Longevity:     0.25 — сколько продержалось
      Degradation:   0.20 — устойчивый тренд

    Пропущенные индексы исключаются, веса переносятся на остальные.
    """
    items = [
        (justification, 0.25),
        (quality, 0.30),
        (longevity, 0.25),
        # Degradation: трансформируем (-10..+10) в (0..10): 0 = 5, +10 = 10, -10 = 0
        ((degradation + 10) / 2 if not pd.isna(degradation) else float('nan'), 0.20),
    ]
    valid = [(v, w) for v, w in items if not pd.isna(v)]
    if not valid:
        return float('nan')
    total_weight = sum(w for _, w in valid)
    score = sum(v * w for v, w in valid) / total_weight
    return float(round(score, 2))


# ───────────────────────────────────────────────────────────────────────
# Сводный расчёт по всем заказам с БДРВ
# ───────────────────────────────────────────────────────────────────────

def compute_efficiency_for_eo(bdrv_eo: pd.DataFrame, orders_eo: pd.DataFrame,
                                expected_mro_days: int = 180) -> pd.DataFrame:
    """Считает 4 индекса + композит для всех заказов одного ЕО.

    Аргументы:
      bdrv_eo    — все замеры для конкретного equnr (long-format).
      orders_eo  — все заказы ТОРО для этого equnr (DataFrame из processed_df).
                   Должен содержать: ID, Дата_Начало, Дата_Конец, Факт_Конец.

    Возвращает: DataFrame с одной строкой на заказ, колонки:
      ID, Justification_Score, Quality_Score, Longevity_Score,
      Degradation_Trend, Efficiency_Score
    """
    if bdrv_eo.empty or orders_eo.empty:
        return pd.DataFrame(columns=[
            'ID', 'Justification_Score', 'Quality_Score',
            'Longevity_Score', 'Degradation_Trend', 'Efficiency_Score',
        ])

    # Сортируем заказы по дате начала
    orders_sorted = orders_eo.sort_values('Дата_Начало').reset_index(drop=True)
    repair_starts = orders_sorted['Дата_Начало'].dropna().tolist()
    repair_ends = orders_sorted['Дата_Конец'].fillna(orders_sorted['Дата_Начало']).dropna().tolist()

    baseline = _baseline_stats(bdrv_eo, repair_starts, exclude_days=30)
    if baseline.empty:
        return pd.DataFrame(columns=[
            'ID', 'Justification_Score', 'Quality_Score',
            'Longevity_Score', 'Degradation_Trend', 'Efficiency_Score',
        ])

    # Общий тренд деградации — по всем ремонтам этого ЕО
    deg_trend = degradation_trend(bdrv_eo, baseline, repair_starts)

    rows = []
    for i, order in orders_sorted.iterrows():
        repair_start = order['Дата_Начало']
        repair_end = order.get('Дата_Конец') or repair_start
        next_start = orders_sorted.iloc[i + 1]['Дата_Начало'] if i + 1 < len(orders_sorted) else pd.NaT

        j = justification_score(bdrv_eo, baseline, repair_start)
        q = quality_score(bdrv_eo, baseline, repair_end)
        l = longevity_score(bdrv_eo, baseline, repair_end, next_start, expected_mro_days)
        eff = efficiency_composite(j, q, l, deg_trend)

        rows.append({
            'ID': order['ID'],
            'Justification_Score': j,
            'Quality_Score': q,
            'Longevity_Score': l,
            'Degradation_Trend': deg_trend,
            'Efficiency_Score': eff,
        })

    return pd.DataFrame(rows)


def compute_efficiency_batch(bdrv: pd.DataFrame, orders: pd.DataFrame,
                              expected_mro_days: int = 180,
                              max_eo: Optional[int] = None) -> pd.DataFrame:
    """Считает эффективность для всех ЕО, у которых есть и БДРВ, и заказы.

    max_eo — если задано, считаем только для первых N ЕО (для быстрой вкладки).
    """
    if bdrv.empty or orders.empty:
        return pd.DataFrame()

    # Какие ЕО (по equnr) есть в обоих датасетах
    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in orders.columns else 'ЕО'
    eo_with_bdrv = set(bdrv['equnr'].astype(str).unique())
    orders_with_bdrv = orders[orders[eo_col].astype(str).isin(eo_with_bdrv)]
    if orders_with_bdrv.empty:
        return pd.DataFrame()

    eo_list = orders_with_bdrv[eo_col].unique()
    if max_eo:
        # Берём ЕО с наибольшим числом заказов (вероятно наиболее интересные)
        counts = orders_with_bdrv.groupby(eo_col, observed=True).size().sort_values(ascending=False)
        eo_list = counts.head(max_eo).index.tolist()

    all_results = []
    for eo in eo_list:
        bdrv_eo = bdrv[bdrv['equnr'].astype(str) == str(eo)]
        orders_eo = orders[orders[eo_col].astype(str) == str(eo)].copy()
        result = compute_efficiency_for_eo(bdrv_eo, orders_eo, expected_mro_days)
        if not result.empty:
            result['equnr'] = str(eo)
            # Добавим имя ЕО и завод для отображения
            first_order = orders_eo.iloc[0]
            result['eo_name'] = first_order.get('ЕО', str(eo))
            result['plant'] = first_order.get('ЗАВОД', '')
            result['unit'] = first_order.get('УСТАНОВКА', '')
            all_results.append(result)

    if not all_results:
        return pd.DataFrame()
    return pd.concat(all_results, ignore_index=True)
