# -*- coding: utf-8 -*-
"""
generate_demo_bdrv.py — Генератор демо-данных БДРВ (Базы Данных Режимов
Ведения) для системы ТИТАН-5 на основе DEMO_LUKOIL_2024-2026.xlsx.

Что делает:
  1. Открывает существующий demo-файл заказов ТОРО.
  2. Выделяет ~500 критических ЕО:
       - все 9 «турбин-бомб» из generate_demo_lukoil.py
       - все 16 «горячих точек»
       - + топ по числу заказов с ABC='Критично'
  3. Для каждого ЕО генерирует временные ряды по 5–8 параметрам,
     замер раз в 4 часа за 2 года (~4380 точек/параметр).
  4. Привязывает поведение к датам ремонтов:
       - за 30–90 дней ДО — плавный тренд ухудшения (вибрация, температура)
       - в день ремонта — резкое восстановление к норме (для нормальных)
         или частичное (для проблемных — даёт сигнал «качество ремонта плохое»)
       - между ремонтами — стабильный режим ±3% от номинала
  5. Сохраняет файлы в формате «Панель тренда»:
       /root/titan-v200/DEMO_BDRV/{PLANT}/{EQUNR}.csv
     + сводный архив /root/titan-v200/DEMO_BDRV_2024-2026.zip

Запуск:
    cd /root/titan-v200/tools && python3 generate_demo_bdrv.py

ТИТАН-5.
"""

import csv
import io
import random
import shutil
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Чтобы импортировать конфиг из соседнего скрипта
sys.path.insert(0, str(Path(__file__).parent))
from generate_demo_lukoil import (
    PLANTS, TURBINE_BOMBS, HOT_SPOTS, PERIOD_START, PERIOD_END,
)

random.seed(42)
np.random.seed(42)

DEMO_XLSX = Path('/root/titan-v200/DEMO_LUKOIL_2024-2026.xlsx')
OUT_DIR = Path('/root/titan-v200/DEMO_BDRV')
OUT_ZIP = Path('/root/titan-v200/DEMO_BDRV_2024-2026.zip')

# Размерности генерации
TARGET_EO_COUNT = 500       # сколько ЕО включить в БДРВ-выгрузку
SAMPLE_INTERVAL_HOURS = 4   # шаг между замерами SCADA
PERIOD_DAYS = (PERIOD_END - PERIOD_START).days

# ───────────────────────────────────────────────────────────────────────
# Профили параметров по типам оборудования
# Каждый параметр: (тег_позиция, тип_данных, базовое_значение, ед_измерения,
#                   sigma_нормальная, направление_деградации, амплитуда_деградации%)
# ───────────────────────────────────────────────────────────────────────

PARAM_PROFILES = {
    'pump': [
        ('PI{n}_IN',   'PIDA.PV', 5.0,    'кгс/см²', 0.10, +1, 8),    # давление вход
        ('PI{n}_OUT',  'PIDA.PV', 12.0,   'кгс/см²', 0.18, -1, 12),   # давление выход
        ('TI{n}_BRG',  'TIAS.PV', 65.0,   '°C',      1.5,  +1, 25),   # температура подшипника
        ('TI{n}_MOT',  'TIAS.PV', 55.0,   '°C',      1.0,  +1, 18),   # температура двигателя
        ('VIB{n}',     'DACA.PV', 2.5,    'мм/с',    0.20, +1, 80),   # вибрация
        ('II{n}_MOT',  'IIAS.PV', 45.0,   'А',       1.5,  +1, 15),   # ток двигателя
        ('FI{n}',      'FIDA.PV', 120.0,  'м³/ч',    3.5,  -1, 18),   # расход
    ],
    'compressor': [
        ('PI{n}_SUC',  'PIDA.PV', 4.0,    'кгс/см²', 0.08, -1, 10),   # вход
        ('PI{n}_DIS',  'PIDA.PV', 28.0,   'кгс/см²', 0.40, -1, 18),   # выход
        ('TI{n}_OIL',  'TIAS.PV', 55.0,   '°C',      1.2,  +1, 22),   # масло
        ('TI{n}_BRG',  'TIAS.PV', 70.0,   '°C',      1.8,  +1, 30),   # подшипник
        ('SI{n}_RPM',  'SIDA.PV', 8500,   'об/мин',  35,   -1, 8),    # обороты
        ('VIB{n}',     'DACA.PV', 3.5,    'мм/с',    0.30, +1, 100),  # вибрация
        ('II{n}_MOT',  'IIAS.PV', 320.0,  'А',       6.0,  +1, 20),   # ток
        ('NI{n}_PWR',  'NIDA.PV', 2400.0, 'кВт',     45,   +1, 15),   # мощность
    ],
    'turbine': [
        ('TI{n}_STM',  'TIAS.PV', 540.0,  '°C',      4.0,  -1, 8),    # пар на входе
        ('TI{n}_EXH',  'TIAS.PV', 320.0,  '°C',      6.0,  +1, 20),   # выхлоп
        ('SI{n}_RPM',  'SIDA.PV', 12500,  'об/мин',  60,   -1, 6),    # обороты
        ('VIB{n}_HP',  'DACA.PV', 4.5,    'мм/с',    0.45, +1, 90),   # вибрация ВД
        ('VIB{n}_LP',  'DACA.PV', 5.0,    'мм/с',    0.50, +1, 95),   # вибрация НД
        ('TI{n}_BRG',  'TIAS.PV', 85.0,   '°C',      2.5,  +1, 28),   # подшипник
        ('NI{n}_PWR',  'NIDA.PV', 18000.0,'кВт',     350,  -1, 18),   # мощность
        ('PI{n}_OIL',  'PIDA.PV', 2.5,    'кгс/см²', 0.05, -1, 25),   # давление масла
    ],
    'furnace': [
        ('TI{n}_O1',   'TIAS.PV', 480.0,  '°C',      3.5,  +1, 12),   # выход 1
        ('TI{n}_O2',   'TIAS.PV', 485.0,  '°C',      3.5,  +1, 12),   # выход 2
        ('TI{n}_O3',   'TIAS.PV', 478.0,  '°C',      3.5,  +1, 12),   # выход 3
        ('TI{n}_SKN',  'TIAS.PV', 580.0,  '°C',      6.0,  +1, 20),   # стенка змеевика
        ('FI{n}_FUEL', 'FIDA.PV', 350.0,  'м³/ч',    8.0,  +1, 25),   # расход топлива
        ('PI{n}_DRF',  'PIDA.PV', -2.5,   'мм.вд.ст',0.18, -1, 35),   # тяга
        ('AI{n}_O2',   'AIDA.PV', 3.5,    '%',       0.25, +1, 50),   # О2 в дымгазах
    ],
    'column': [
        ('PI{n}_TOP',  'PIDA.PV', 1.8,    'кгс/см²', 0.04, +1, 12),   # верх
        ('PI{n}_BOT',  'PIDA.PV', 2.2,    'кгс/см²', 0.05, +1, 15),   # низ
        ('TI{n}_TOP',  'TIAS.PV', 165.0,  '°C',      2.5,  +1, 8),
        ('TI{n}_BOT',  'TIAS.PV', 320.0,  '°C',      4.0,  +1, 10),
        ('TI{n}_FED',  'TIAS.PV', 240.0,  '°C',      3.0,  +1, 8),
        ('LI{n}',      'LIDA.PV', 65.0,   '%',       2.0,  +1, 25),   # уровень
    ],
    'heatx': [
        ('PDI{n}',     'PIDA.PV', 1.4,    'кгс/см²', 0.06, +1, 70),   # перепад (рост = закоксов.)
        ('TI{n}_IH',   'TIAS.PV', 285.0,  '°C',      3.0,  -1, 8),    # горячий вход
        ('TI{n}_OH',   'TIAS.PV', 195.0,  '°C',      2.5,  +1, 12),   # горячий выход
        ('TI{n}_IC',   'TIAS.PV', 95.0,   '°C',      1.8,  +1, 6),    # холодный вход
        ('TI{n}_OC',   'TIAS.PV', 165.0,  '°C',      2.2,  -1, 10),   # холодный выход
    ],
    'reactor': [
        ('TI{n}_IN',   'TIAS.PV', 380.0,  '°C',      3.0,  +1, 10),
        ('TI{n}_OUT',  'TIAS.PV', 410.0,  '°C',      3.5,  +1, 12),
        ('PI{n}',      'PIDA.PV', 35.0,   'кгс/см²', 0.40, +1, 15),
        ('AI{n}_CONV', 'AIDA.PV', 78.0,   '%',       1.5,  -1, 18),   # конверсия
    ],
    'valve': [
        ('PI{n}_DEL',  'PIDA.PV', 1.2,    'кгс/см²', 0.05, +1, 50),   # перепад
        ('II{n}_OP',   'IIAS.PV', 65.0,   '%',       2.5,  +1, 30),   # положение
        ('TI{n}_BDY',  'TIAS.PV', 165.0,  '°C',      3.0,  +1, 18),   # тело
    ],
    'fan': [
        ('SI{n}_RPM',  'SIDA.PV', 1480,   'об/мин',  10,   -1, 8),
        ('VIB{n}',     'DACA.PV', 2.8,    'мм/с',    0.25, +1, 90),
        ('II{n}_MOT',  'IIAS.PV', 28.0,   'А',       1.0,  +1, 18),
        ('TI{n}_BRG',  'TIAS.PV', 60.0,   '°C',      1.2,  +1, 25),
    ],
}

# Маппинг типа оборудования по ключевым словам в названии ЕО
def detect_eq_type(eo_name: str) -> str:
    s = (eo_name or '').lower()
    if any(k in s for k in ['турбин', 'тгу', 'тдб', 'тд', 'тг']):
        return 'turbine'
    if any(k in s for k in ['компрес', 'компр', 'воздуходув', 'вд-', 'цк-', 'к-']):
        return 'compressor'
    if any(k in s for k in ['насос', 'н-']):
        return 'pump'
    if any(k in s for k in ['вентил', 'в-', 'вао']):
        return 'fan'
    if any(k in s for k in ['печь', 'печи', 'п-', 'змеевик', 'горелк']):
        return 'furnace'
    if any(k in s for k in ['колонн', 'колон', 'к-1', 'к-2', 'к-3', 'к-4', 'к-5']):
        return 'column'
    if any(k in s for k in ['теплообм', 'т-', 'кожухотр']):
        return 'heatx'
    if any(k in s for k in ['реактор', 'реакц', 'р-']):
        return 'reactor'
    if any(k in s for k in ['клапан', 'задвижка', 'sv-', 'fv-']):
        return 'valve'
    return 'pump'  # дефолт


# ───────────────────────────────────────────────────────────────────────
# Шаг 1. Загрузка demo-xlsx и выбор критических ЕО
# ───────────────────────────────────────────────────────────────────────

def load_orders() -> pd.DataFrame:
    """Загружает список заказов через cache (быстро)."""
    sys.path.insert(0, '/root/titan-v200/backend')
    from core.cache import compute_file_hash, has_cache, load_cache
    with open(DEMO_XLSX, 'rb') as f:
        data = f.read()
    fh = compute_file_hash(data)
    if has_cache(fh):
        df, _, _ = load_cache(fh)
        print(f'  [cache] загружено {len(df)} заказов из Parquet')
        return df
    # Fallback: полный процессинг (медленно)
    from core.data_processor import process_data
    print(f'  [full] парсинг xlsx (~3 мин)…')
    df_raw = pd.read_excel(DEMO_XLSX, engine='calamine')
    df = process_data(df_raw)
    return df


def select_critical_eo(df: pd.DataFrame, target_count: int = TARGET_EO_COUNT) -> pd.DataFrame:
    """Возвращает DataFrame с критическими ЕО:
       (EQUNR_Код, ЕО, ЗАВОД, plant_prefix, n_orders, repair_dates)."""
    print(f'\n[2] Выбираем {target_count} критических ЕО…')

    # Группировка: для каждого ЕО — число заказов, имя, завод, даты ремонтов
    eo_col = 'EQUNR_Код' if 'EQUNR_Код' in df.columns else 'ЕО'

    # Фильтр: только заказы с осмысленной датой
    df = df[df[eo_col].notna() & (df[eo_col] != 'Н/Д')].copy()

    # Группируем
    grouped = df.groupby(eo_col).agg(
        eo_name=('ЕО', 'first'),
        plant=('ЗАВОД', 'first'),
        n_orders=('ID', 'count'),
        n_critical=('ABC', lambda s: (s == 'Критично').sum()),
        max_fact=('Fact_N', 'max'),
        sum_fact=('Fact_N', 'sum'),
    ).reset_index()
    grouped.columns = ['equnr', 'eo_name', 'plant', 'n_orders', 'n_critical', 'max_fact', 'sum_fact']

    # Score для отбора: турбины-бомбы, горячие точки, критические по сумме
    turbine_keywords = [tb[3] for tb in TURBINE_BOMBS]   # имена турбин
    hotspot_keywords = [hs[3] for hs in HOT_SPOTS]        # имена горячих точек

    def is_turbine(name):
        return any(k in (name or '') for k in turbine_keywords)

    def is_hotspot(name):
        return any(k in (name or '') for k in hotspot_keywords)

    grouped['is_turbine'] = grouped['eo_name'].apply(is_turbine)
    grouped['is_hotspot'] = grouped['eo_name'].apply(is_hotspot)

    # Категория приоритета
    grouped['priority'] = (
        grouped['is_turbine'].astype(int) * 1000 +     # турбины — топ
        grouped['is_hotspot'].astype(int) * 500 +      # горячие точки — следующие
        (grouped['n_critical'] >= 3).astype(int) * 100 +
        grouped['n_orders'] +                           # затем по числу заказов
        grouped['sum_fact'] / 1e6                       # затем по сумме затрат
    )

    selected = grouped.nlargest(target_count, 'priority').copy()
    print(f'  Турбин-бомб: {selected["is_turbine"].sum()}')
    print(f'  Горячих точек: {selected["is_hotspot"].sum()}')
    print(f'  Прочих критических: {(~selected["is_turbine"] & ~selected["is_hotspot"]).sum()}')

    # Соберём даты ремонтов для каждого выбранного ЕО (нужно для ухудшений)
    print('  Собираю даты ремонтов…')
    repair_dates = (df[df[eo_col].isin(selected['equnr'])]
                    .groupby(eo_col)
                    .apply(lambda g: sorted(g['Дата_Начало'].dropna().tolist()))
                    .to_dict())
    selected['repair_dates'] = selected['equnr'].map(repair_dates)

    # Префикс завода (для путей файлов)
    plant_prefix_map = {p['iwerk_txt']: code for code, p in PLANTS.items()}
    selected['plant_prefix'] = selected['plant'].map(plant_prefix_map).fillna('XX')

    return selected


# ───────────────────────────────────────────────────────────────────────
# Шаг 2. Генерация временного ряда по одному параметру с привязкой к ремонтам
# ───────────────────────────────────────────────────────────────────────

def generate_param_series(
    timestamps: np.ndarray,         # массив datetime замеров
    base_value: float,              # номинал
    sigma: float,                   # шум нормального режима
    direction: int,                 # +1 — растёт перед поломкой, -1 — падает
    deg_amplitude_pct: float,       # на сколько % от нормы уйдёт перед ремонтом
    repair_dates: list,             # даты ремонтов из xlsx
    is_problematic: bool,           # для проблемных ЕО — частичное восстановление
    deterioration_window_days: int = 60,  # сколько дней ДО ремонта плавно ухудшается
    rng: random.Random = None,
) -> np.ndarray:
    """Генерирует массив значений параметра по временной сетке."""
    if rng is None:
        rng = random
    n = len(timestamps)
    # Базовый шум вокруг номинала
    values = base_value + np.random.normal(0, sigma, n)

    # Привязка к каждому ремонту: за `window` дней до — плавное смещение
    deg_amp = base_value * deg_amplitude_pct / 100.0
    for repair_dt in repair_dates:
        if not isinstance(repair_dt, (datetime, pd.Timestamp)):
            continue
        if isinstance(repair_dt, pd.Timestamp):
            repair_dt = repair_dt.to_pydatetime()
        # Окно ухудшения: [repair - window, repair]
        window_start = repair_dt - timedelta(days=deterioration_window_days)
        # Маска точек в окне
        ts_dt = pd.to_datetime(timestamps)
        mask_window = (ts_dt >= window_start) & (ts_dt < repair_dt)
        if mask_window.any():
            # Линейный рост от 0 до deg_amp
            days_to_repair = np.array([
                (repair_dt - ts.to_pydatetime()).total_seconds() / 86400
                for ts in ts_dt[mask_window]
            ])
            progress = 1.0 - (days_to_repair / deterioration_window_days)
            progress = np.clip(progress, 0, 1)
            # Гладкая функция (квадрат — резкое ухудшение к концу)
            offset = direction * deg_amp * (progress ** 2)
            values[mask_window] += offset
        # После ремонта: возвращаемся к номиналу
        # Для нормальных — полное восстановление (значение уже = base + шум)
        # Для проблемных — частичный остаточный сдвиг
        if is_problematic:
            mask_after = ts_dt > repair_dt
            if mask_after.any():
                # Постепенно затухающий «остаточный сдвиг» 30% от deg_amp
                residual = direction * deg_amp * 0.30
                # Быстро затухает за 7 дней потом стабилизируется
                values[mask_after] += residual * 0.5

    return np.round(values, 4)


# ───────────────────────────────────────────────────────────────────────
# Шаг 3. Запись CSV в формате «Панель тренда»
# ───────────────────────────────────────────────────────────────────────

def write_eo_csv(out_path: Path, plant_prefix: str, eo_name: str, equnr: str,
                 eq_type: str, repair_dates: list, is_problematic: bool):
    """Создаёт один CSV-файл для одного ЕО."""
    profile = PARAM_PROFILES[eq_type]

    # Временная сетка: каждые 4 часа, с лёгким дрейфом времени (как в реальной SCADA)
    n_samples = int(PERIOD_DAYS * 24 / SAMPLE_INTERVAL_HOURS)
    base_times = pd.date_range(PERIOD_START, periods=n_samples, freq=f'{SAMPLE_INTERVAL_HOURS}h')
    # Дрейф: каждый замер сдвинут на ±15 минут случайно
    jitter_minutes = np.random.randint(-15, 16, size=n_samples)
    timestamps = base_times + pd.to_timedelta(jitter_minutes, unit='m')

    # Идентификатор позиции — последняя цифра в имени ЕО или индекс
    pos_id = '101'
    for ch in eo_name or '':
        if ch.isdigit():
            pos_id = ch * 3  # упрощённо
            break

    # Сборка тегов и значений
    tags = []
    columns_data = []
    for tag_pos_tmpl, type_value, base_v, units, sigma, direction, amp_pct in profile:
        tag_pos = tag_pos_tmpl.replace('{n}', pos_id)
        # Полное имя тега: PLANT_PREFIX.POS.TYPE.VALUE
        full_tag = f'{plant_prefix}{eq_type[:2].upper()}1.{tag_pos}.{type_value}'
        tags.append(full_tag)
        rng_local = random.Random(hash((equnr, tag_pos)) & 0xFFFFFFFF)
        values = generate_param_series(
            timestamps.values, base_v, sigma, direction, amp_pct,
            repair_dates or [], is_problematic, rng=rng_local,
        )
        columns_data.append(values)

    # Запись CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Timestamp'] + tags)
        for i in range(n_samples):
            ts_str = pd.Timestamp(timestamps[i]).strftime('%Y-%m-%d %H:%M:%S')
            row = [ts_str]
            for col_vals in columns_data:
                # Десятичный разделитель — запятая (как в Панель тренда)
                row.append(str(col_vals[i]).replace('.', ','))
            writer.writerow(row)


# ───────────────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────────────

def main():
    print('=' * 60)
    print('Генератор demo-БДРВ для ТИТАН-5')
    print('=' * 60)
    print(f'Период: {PERIOD_START.date()} … {PERIOD_END.date()}')
    print(f'Шаг: {SAMPLE_INTERVAL_HOURS} часа')
    print(f'Целевое количество ЕО: {TARGET_EO_COUNT}')
    print(f'Выход: {OUT_DIR} + {OUT_ZIP}')
    print()

    # Очистка предыдущей выгрузки
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    # 1. Загрузка заказов
    print('[1] Читаем существующий demo-файл заказов…')
    df = load_orders()
    print(f'    {len(df)} заказов')

    # 2. Выбор критических ЕО
    selected = select_critical_eo(df, TARGET_EO_COUNT)
    print(f'    Выбрано {len(selected)} ЕО')

    # 3. Генерация CSV для каждого ЕО
    print()
    print(f'[3] Генерация временных рядов ({SAMPLE_INTERVAL_HOURS}h × ~{int(PERIOD_DAYS*24/SAMPLE_INTERVAL_HOURS)} точек/параметр)…')
    n_done = 0
    n_total = len(selected)
    plants_count: dict[str, int] = {}

    for _, row in selected.iterrows():
        eq_type = detect_eq_type(row['eo_name'])
        is_problematic = row['is_turbine'] or row['is_hotspot'] or (row['n_critical'] >= 3)

        plant_dir = OUT_DIR / row['plant_prefix']
        # Безопасное имя файла из EQUNR
        safe_equnr = ''.join(c if c.isalnum() else '_' for c in str(row['equnr']))[:40]
        out_path = plant_dir / f'{safe_equnr}.csv'

        try:
            write_eo_csv(
                out_path,
                plant_prefix=row['plant_prefix'],
                eo_name=row['eo_name'],
                equnr=str(row['equnr']),
                eq_type=eq_type,
                repair_dates=row['repair_dates'] or [],
                is_problematic=is_problematic,
            )
            plants_count[row['plant_prefix']] = plants_count.get(row['plant_prefix'], 0) + 1
            n_done += 1
            if n_done % 50 == 0 or n_done == n_total:
                print(f'    [{n_done:>3}/{n_total}] {row["plant_prefix"]} {row["eo_name"][:50]}')
        except Exception as e:
            print(f'    !!! ошибка для {row["equnr"]}: {e}')

    print(f'\n  Готово: {n_done} файлов')
    for p, c in sorted(plants_count.items()):
        print(f'    {p}: {c} ЕО')

    # 4. Упаковка в zip
    print(f'\n[4] Упаковка в {OUT_ZIP}…')
    if OUT_ZIP.exists():
        OUT_ZIP.unlink()
    with zipfile.ZipFile(OUT_ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for csv_file in sorted(OUT_DIR.rglob('*.csv')):
            arcname = csv_file.relative_to(OUT_DIR.parent)
            zf.write(csv_file, arcname=arcname)

    zip_mb = OUT_ZIP.stat().st_size / 1024 / 1024
    dir_mb = sum(p.stat().st_size for p in OUT_DIR.rglob('*')) / 1024 / 1024
    print(f'  CSV-папка: {dir_mb:.1f} MB')
    print(f'  ZIP-архив: {zip_mb:.1f} MB')

    print()
    print('Готово.')


if __name__ == '__main__':
    main()
