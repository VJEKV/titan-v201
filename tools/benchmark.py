# -*- coding: utf-8 -*-
"""
Бенчмарк ТИТАН-5 — измерение скорости ключевых операций на реальных demo-данных.

Запуск:
    cd /root/titan-v200/backend && python3 ../tools/benchmark.py

Или на Windows:
    cd backend && ..\python\python.exe ..\tools\benchmark.py
"""

import sys
import time
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

from core.cache import compute_file_hash, has_cache, load_cache, save_cache, invalidate_cache
from core.data_processor import process_data
from core.aggregates import compute_aggregates
from core.risk_scoring_v2 import apply_risk_scoring_v2

DEMO = Path('/root/titan-v200/DEMO_LUKOIL_2024-2026.xlsx')
BDRV_ZIP = Path('/root/titan-v200/DEMO_BDRV_2024-2026.zip')

THRESH = {
    'C1-M1: Перерасход бюджета': 20,
    'C1-M6: Аномалия по истории ТМ': 140,
    'C2-M2: Проблемное оборудование': 5,
    'NEW-9: Формальное закрытие в декабре': 50,
    'NEW-10: Возвраты статусов': 3,
}


def fmt_time(t):
    if t < 1:
        return f'{t*1000:.0f} мс'
    if t < 60:
        return f'{t:.1f} сек'
    return f'{int(t/60)} мин {int(t%60)} сек'


def bench():
    print('=' * 68)
    print('БЕНЧМАРК ТИТАН-5')
    print('=' * 68)
    print(f'Demo-файл: {DEMO.name}, размер: {DEMO.stat().st_size/1024/1024:.0f} МБ')
    if BDRV_ZIP.exists():
        print(f'БДРВ-архив: {BDRV_ZIP.name}, размер: {BDRV_ZIP.stat().st_size/1024/1024:.0f} МБ')
    print()

    results = {}

    # ─── 1. Первичный процессинг (сценарий: новый файл, кэша нет) ───
    print('[1/6] ПЕРВИЧНЫЙ ПРОЦЕССИНГ (удаляем кэш, считаем с нуля)')
    with open(DEMO, 'rb') as f:
        xlsx_bytes = f.read()
    file_hash = compute_file_hash(xlsx_bytes)
    invalidate_cache(file_hash)

    t0 = time.time()
    df_raw = pd.read_excel(DEMO, engine='calamine')
    t_read = time.time() - t0
    print(f'      read_excel: {fmt_time(t_read)} ({len(df_raw):,} строк)')

    t0 = time.time()
    df = process_data(df_raw)
    t_proc = time.time() - t0
    print(f'      process_data: {fmt_time(t_proc)} ({len(df):,} заказов)')

    t0 = time.time()
    agg = compute_aggregates(df)
    t_agg = time.time() - t0
    print(f'      compute_aggregates: {fmt_time(t_agg)}')

    t0 = time.time()
    df_scored, _ = apply_risk_scoring_v2(df.copy(), agg, THRESH)
    t_score = time.time() - t0
    print(f'      risk_scoring_v2: {fmt_time(t_score)}')

    t_total_fresh = t_read + t_proc + t_agg + t_score
    results['fresh_upload'] = t_total_fresh
    print(f'      ИТОГО: {fmt_time(t_total_fresh)}')

    # ─── 2. Сохранение в Parquet-кэш ───
    print()
    print('[2/6] СОХРАНЕНИЕ В PARQUET-КЭШ')
    t0 = time.time()
    save_cache(file_hash, df, agg)
    t_save = time.time() - t0
    results['save_cache'] = t_save
    cache_file = BACKEND_DIR / 'cache' / f'v5.0.0_{file_hash}_df.parquet'
    if cache_file.exists():
        print(f'      {fmt_time(t_save)}, файл {cache_file.stat().st_size/1024/1024:.1f} МБ')
    else:
        print(f'      {fmt_time(t_save)} (файл не найден по ожидаемому пути)')

    # ─── 3. Повторная загрузка (из кэша) ───
    print()
    print('[3/6] ПОВТОРНАЯ ЗАГРУЗКА ТОГО ЖЕ ФАЙЛА (из Parquet)')
    t0 = time.time()
    df2, agg2, meta = load_cache(file_hash)
    t_reload = time.time() - t0
    results['cached_upload'] = t_reload
    print(f'      load_cache: {fmt_time(t_reload)} ({len(df2):,} заказов)')
    speedup = t_total_fresh / t_reload if t_reload else 0
    print(f'      Ускорение vs первичной загрузки: ×{speedup:.0f}')

    # ─── 4. Типичный запрос вкладки (filter + aggregate + scoring) ───
    print()
    print('[4/6] ТИПИЧНЫЙ ЗАПРОС ВКЛАДКИ (фильтр + агрегаты + скоринг)')
    # Имитируем фильтр «Завод = ННОС»
    t0 = time.time()
    mask = df_scored['ЗАВОД'].astype(str) == 'ННОС Нижегороднефтеоргсинтез'
    subset = df_scored[mask]
    t_filter = time.time() - t0
    print(f'      Фильтр по заводу: {fmt_time(t_filter)} ({len(subset):,} заказов)')

    t0 = time.time()
    by_unit = subset.groupby('УСТАНОВКА', observed=True).agg(
        n=('ID', 'count'),
        plan=('Plan_N', 'sum'),
        fact=('Fact_N', 'sum'),
        risk=('Risk_Sum', 'mean'),
    ).sort_values('fact', ascending=False).head(20)
    t_grp = time.time() - t0
    print(f'      Groupby+sort+head(20): {fmt_time(t_grp)}')

    t0 = time.time()
    top_eo = subset.groupby('ЕО', observed=True).size().sort_values(ascending=False).head(50)
    t_top = time.time() - t0
    print(f'      TOP-50 ЕО: {fmt_time(t_top)}')

    results['filter_aggregate'] = t_filter + t_grp + t_top

    # ─── 5. Загрузка БДРВ (если есть) ───
    if BDRV_ZIP.exists():
        print()
        print('[5/6] ЗАГРУЗКА БДРВ (ZIP с 500 ЕО × 7 параметров × 5004 точек)')
        from core.bdrv_loader import load_bdrv_zip, save_bdrv_parquet, load_bdrv_parquet
        parquet_path = BACKEND_DIR / 'cache' / 'bdrv' / f'bdrv_demo_bench.parquet'
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        if parquet_path.exists():
            parquet_path.unlink()

        t0 = time.time()
        with open(BDRV_ZIP, 'rb') as f:
            zip_bytes = f.read()
        bdrv = load_bdrv_zip(zip_bytes)
        t_bdrv_parse = time.time() - t0
        results['bdrv_parse'] = t_bdrv_parse
        print(f'      Парсинг ZIP: {fmt_time(t_bdrv_parse)} ({len(bdrv):,} строк, {bdrv["equnr"].nunique()} ЕО)')

        t0 = time.time()
        save_bdrv_parquet(bdrv, parquet_path)
        t_bdrv_save = time.time() - t0
        print(f'      Save Parquet: {fmt_time(t_bdrv_save)} ({parquet_path.stat().st_size/1024/1024:.0f} МБ)')

        t0 = time.time()
        bdrv2 = load_bdrv_parquet(parquet_path)
        t_bdrv_load = time.time() - t0
        results['bdrv_reload'] = t_bdrv_load
        print(f'      Повторная загрузка из Parquet: {fmt_time(t_bdrv_load)}')
        bdrv_speedup = t_bdrv_parse / t_bdrv_load if t_bdrv_load else 0
        print(f'      Ускорение: ×{bdrv_speedup:.0f}')

    # ─── Сводка ───
    print()
    print('=' * 68)
    print('СВОДКА')
    print('=' * 68)
    print(f'{"Операция":<50s} {"Время":>15s}')
    print('-' * 68)
    labels = {
        'fresh_upload': 'Первичная загрузка (xlsx → DataFrame)',
        'save_cache': 'Сохранение в Parquet-кэш',
        'cached_upload': 'Повторная загрузка (Parquet)',
        'filter_aggregate': 'Запрос вкладки (фильтр + агрегаты)',
        'bdrv_parse': 'БДРВ: парсинг ZIP (первый раз)',
        'bdrv_reload': 'БДРВ: повторная загрузка (Parquet)',
    }
    for key, label in labels.items():
        if key in results:
            print(f'{label:<50s} {fmt_time(results[key]):>15s}')

    print()
    print('ВЫВОД: эти цифры — потолок для вашего ПК при условии')
    print('что процессор сопоставим (этот сервер: {cpu}).'.format(
        cpu=(lambda: __import__('platform').processor() or 'неизвестен')()
    ))


if __name__ == '__main__':
    bench()
