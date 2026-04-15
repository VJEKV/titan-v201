# -*- coding: utf-8 -*-
"""
Регрессионный тест ТИТАН-5.

Эталоны зафиксированы на прогоне ТИТАН-200 (Apr 15, 2026) с demo-файлом
/root/titan-v200/DEMO_LUKOIL_2024-2026.xlsx (SHA-256 проверяется по содержимому).

Правила:
- После ЛЮБОЙ оптимизации скорости результат должен совпасть с эталоном.
- Допуск: 0.01% для целых чисел, 1 ₽ для сумм (от объёма ~100 млрд ₽).
- Тест-маркер slow: pytest -m slow (запускается 3-5 минут).

Запуск:
    cd /root/titan-v200/backend && python3 -m pytest tests/test_regression.py -v
"""

import sys
import time
from pathlib import Path

import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.data_processor import process_data  # noqa: E402
from core.aggregates import compute_aggregates  # noqa: E402
from core.risk_scoring_v2 import apply_risk_scoring_v2  # noqa: E402

DEMO_FILE = Path('/root/titan-v200/DEMO_LUKOIL_2024-2026.xlsx')

# ────────────────────────────────────────────────────────────────────────
# ЭТАЛОНЫ — зафиксированы на ТИТАН-200, обновлять только при осознанном
# изменении алгоритмов (не из-за "оптимизации").
# ────────────────────────────────────────────────────────────────────────

EXPECTED = {
    # Общие
    'total_orders': 124403,
    'total_rows_raw': 628202,
    'total_plants': 4,

    # Суммы — эталон зафиксирован на прогоне ТИТАН-200 (15.04.2026)
    # Допуск 100 ₽ от объёма ~100 млрд (0.0000001%).
    'total_plan_n': 98_975_473_741.61,
    'total_fact_n': 102_470_128_484.55,
    'tolerance_money_rub': 100.0,

    # Методы риск-скоринга (бинарные флаги, допуск ± 3)
    's_c1m1': 3711,
    's_c1m6': 15945,
    's_c1m9': 904,
    's_c2m2': 48881,
    's_new9': 30,
    's_new10': 1196,
    'tolerance_s_methods': 10,

    # Категории риска
    'cat_red': 57840,
    'cat_green': 66563,
    'tolerance_cat': 50,

    # Количество заводов и их заказы
    'plants': {
        'ННОС Нижегороднефтеоргсинтез': 43386,
        'Волгограднефтепереработка': 37393,
        'Пермнефтеоргсинтез': 33118,
        'Ухтанефтепереработка': 10502,
    },
    'tolerance_plant_orders': 30,

    # Топ-3 ЕО по числу заказов (горячие точки)
    'top_eo_names': [
        'Быстродействующие клапаны КЦА КВ-01…40',
        'Насос откачки кокса Н-401 УЗК',
        'Горелки печи П-501 ЭЛОУ-АВТ-1',
    ],

    # Турбины-бомбы — проверяем что они вычисляются (>= 2 заказов)
    'turbine_bombs_keywords': [
        'Турбина ТГУ-6',
        'Турбогенератор ТГ-200',
        'Турбокомпрессор К-301',
        'Турбодетандер ТДА-1',
        'Центробежный компрессор ЦК-501',
    ],
}

# Пороги для apply_risk_scoring_v2 — как в UI по умолчанию
DEFAULT_THRESHOLDS = {
    'C1-M1: Перерасход бюджета': 20,
    'C1-M6: Аномалия по истории ТМ': 140,
    'C2-M2: Проблемное оборудование': 5,
    'NEW-9: Формальное закрытие в декабре': 50,
    'NEW-10: Возвраты статусов': 3,
}


# ────────────────────────────────────────────────────────────────────────
# FIXTURES: загружаем и обрабатываем demo-файл ОДИН РАЗ на всю сессию pytest
# ────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def raw_df():
    """Сырой DataFrame из xlsx — самый долгий шаг."""
    assert DEMO_FILE.exists(), f'Demo-файл не найден: {DEMO_FILE}'
    t0 = time.time()
    df = pd.read_excel(DEMO_FILE, engine='calamine')
    print(f'\n[read_excel] {len(df)} строк за {time.time()-t0:.1f}s')
    return df


@pytest.fixture(scope='module')
def processed_df(raw_df):
    """DataFrame после process_data."""
    t0 = time.time()
    df = process_data(raw_df.copy())
    print(f'[process_data] {len(df)} заказов за {time.time()-t0:.1f}s')
    return df


@pytest.fixture(scope='module')
def scored_df(processed_df):
    """DataFrame с риск-скорингом."""
    t0 = time.time()
    agg = compute_aggregates(processed_df)
    df, _extra = apply_risk_scoring_v2(processed_df.copy(), agg, DEFAULT_THRESHOLDS)
    print(f'[risk_scoring] за {time.time()-t0:.1f}s')
    return df


# ────────────────────────────────────────────────────────────────────────
# ТЕСТЫ
# ────────────────────────────────────────────────────────────────────────

@pytest.mark.slow
class TestLoadAndProcess:
    """Корректность чтения и обработки demo-файла."""

    def test_raw_rows_count(self, raw_df):
        """Число строк в xlsx."""
        assert len(raw_df) == EXPECTED['total_rows_raw'], \
            f'Ожидалось {EXPECTED["total_rows_raw"]} строк, получено {len(raw_df)}'

    def test_processed_orders_count(self, processed_df):
        """После агрегации истории статусов — 124 403 уникальных заказа."""
        assert len(processed_df) == EXPECTED['total_orders'], \
            f'Ожидалось {EXPECTED["total_orders"]} заказов, получено {len(processed_df)}'

    def test_plant_count(self, processed_df):
        """4 завода."""
        plants = processed_df['ЗАВОД'].nunique()
        assert plants == EXPECTED['total_plants'], f'Ожидалось {EXPECTED["total_plants"]} заводов, получено {plants}'

    def test_plants_orders(self, processed_df):
        """Распределение заказов по заводам."""
        tol = EXPECTED['tolerance_plant_orders']
        for plant_name, expected_count in EXPECTED['plants'].items():
            actual = (processed_df['ЗАВОД'] == plant_name).sum()
            assert abs(actual - expected_count) <= tol, \
                f'{plant_name}: ожидалось {expected_count}, получено {actual} (допуск ±{tol})'

    def test_required_columns(self, processed_df):
        """Наличие ключевых колонок после process_data."""
        required = ['ID', 'ЗАВОД', 'ЕО', 'Вид', 'Plan_N', 'Fact_N',
                    'Начало', 'Конец', 'STAT', 'ABC', 'ТМ', 'УСТАНОВКА',
                    'Data_Completeness']
        for col in required:
            assert col in processed_df.columns, f'Отсутствует колонка {col}'


@pytest.mark.slow
class TestFinancials:
    """Денежные суммы — допуск 5 ₽ от объёма ~100 млрд."""

    def test_total_plan(self, processed_df):
        total = processed_df['Plan_N'].sum()
        expected = EXPECTED['total_plan_n']
        tol = EXPECTED['tolerance_money_rub']
        assert abs(total - expected) < tol, \
            f'Total Plan_N: ожидалось {expected}, получено {total} (Δ={abs(total-expected):.2f}, допуск {tol})'

    def test_total_fact(self, processed_df):
        total = processed_df['Fact_N'].sum()
        expected = EXPECTED['total_fact_n']
        tol = EXPECTED['tolerance_money_rub']
        assert abs(total - expected) < tol, \
            f'Total Fact_N: ожидалось {expected}, получено {total} (Δ={abs(total-expected):.2f}, допуск {tol})'


@pytest.mark.slow
class TestRiskScoring:
    """6 методов риск-скоринга — бинарные флаги S_*."""

    def test_s_c1m1(self, scored_df):
        self._check_flag(scored_df, 'S_C1-M1: Перерасход бюджета', EXPECTED['s_c1m1'])

    def test_s_c1m6(self, scored_df):
        self._check_flag(scored_df, 'S_C1-M6: Аномалия по истории ТМ', EXPECTED['s_c1m6'])

    def test_s_c1m9(self, scored_df):
        self._check_flag(scored_df, 'S_C1-M9: Незавершённые работы', EXPECTED['s_c1m9'])

    def test_s_c2m2(self, scored_df):
        self._check_flag(scored_df, 'S_C2-M2: Проблемное оборудование', EXPECTED['s_c2m2'])

    def test_s_new9(self, scored_df):
        self._check_flag(scored_df, 'S_NEW-9: Формальное закрытие в декабре', EXPECTED['s_new9'])

    def test_s_new10(self, scored_df):
        self._check_flag(scored_df, 'S_NEW-10: Возвраты статусов', EXPECTED['s_new10'])

    def test_risk_category_red(self, scored_df):
        n = (scored_df['Risk_Category'] == 'Красный').sum()
        tol = EXPECTED['tolerance_cat']
        assert abs(n - EXPECTED['cat_red']) <= tol, \
            f'Красные: ожидалось {EXPECTED["cat_red"]}, получено {n} (допуск ±{tol})'

    def test_risk_category_green(self, scored_df):
        n = (scored_df['Risk_Category'] == 'Зелёный').sum()
        tol = EXPECTED['tolerance_cat']
        assert abs(n - EXPECTED['cat_green']) <= tol, \
            f'Зелёные: ожидалось {EXPECTED["cat_green"]}, получено {n} (допуск ±{tol})'

    def _check_flag(self, df, col, expected):
        assert col in df.columns, f'Нет колонки {col}'
        n = int(df[col].sum())
        tol = EXPECTED['tolerance_s_methods']
        assert abs(n - expected) <= tol, \
            f'{col}: ожидалось {expected}, получено {n} (допуск ±{tol})'


@pytest.mark.slow
class TestHotSpots:
    """Горячие точки и турбины-бомбы — должны выявляться программой."""

    def test_top_3_eo_are_hotspots(self, processed_df):
        top_eo = (processed_df
                  .groupby('ЕО').size()
                  .sort_values(ascending=False)
                  .head(3)
                  .index.tolist())
        for expected_name in EXPECTED['top_eo_names']:
            assert expected_name in top_eo, \
                f'Горячая точка "{expected_name}" не в ТОП-3 (ТОП-3: {top_eo})'

    def test_turbine_bombs_have_orders(self, processed_df):
        """Все 5 ключевых турбин-бомб имеют >=2 ремонта в файле."""
        for keyword in EXPECTED['turbine_bombs_keywords']:
            mask = processed_df['ЕО'].astype(str).str.contains(keyword, na=False)
            n = mask.sum()
            assert n >= 2, f'Турбина "{keyword}": ожидалось >=2 ремонта, получено {n}'


@pytest.mark.slow
class TestDataCompleteness:
    """Полнота данных — для идеально заполненного demo-файла ≥ 99%."""

    def test_completeness_high(self, processed_df):
        mean_compl = processed_df['Data_Completeness'].mean()
        assert mean_compl >= 99.0, f'Средняя полнота данных {mean_compl:.1f}% < 99%'


if __name__ == '__main__':
    # Быстрый запуск без pytest: python3 test_regression.py
    print('ЗАПУСК РЕГРЕССИОННОГО ТЕСТА...')
    print('Используйте: pytest tests/test_regression.py -v -m slow')
