# -*- coding: utf-8 -*-
"""
core/bdrv_loader.py — Парсер CSV «Панель тренда» из систем SCADA-историзации
(OSIsoft PI / Honeywell PHD / аналоги).

Формат входа:
  Timestamp;ETL1.PDI2045.DACA.PV;ETL1.TIAS2085.DACA.PV;...
  2024-01-01 21:48:59;0,32591;15,0327;1,8391;...
  ...

Особенности:
  - Разделитель `;`
  - Десятичный `,`
  - Теги SCADA: UNIT.POSITION.DATA_TYPE.VALUE_TYPE
  - Один файл = один ЕО (или одна установка)

Парсер возвращает long-format DataFrame:
  equnr | tag | tag_pos | tag_type | timestamp | value

ТИТАН-5.
"""

import io
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

# Регекс для SCADA-тега: PLANT.POS.DATA_TYPE.VALUE_TYPE
TAG_PATTERN = re.compile(r'^([A-Z0-9]+)\.([A-Z0-9_]+)\.([A-Z0-9_]+)\.([A-Z0-9_]+)$')


def parse_tag(tag: str) -> dict:
    """Разбирает SCADA-тег вида ETL1.PDI2045.DACA.PV → {plant, pos, data_type, value_type}."""
    m = TAG_PATTERN.match(tag.strip())
    if m:
        return {
            'plant_unit': m.group(1),
            'pos': m.group(2),
            'data_type': m.group(3),
            'value_type': m.group(4),
        }
    return {'plant_unit': '', 'pos': tag.strip(), 'data_type': '', 'value_type': ''}


def detect_separator_and_decimal(sample: str) -> tuple[str, str]:
    """Автоопределение разделителя CSV и десятичного знака."""
    # Считаем число `;` и `,` в первых строках. Если `;` много и `,` есть — формат «Панель тренда».
    n_semi = sample.count(';')
    n_comma = sample.count(',')
    n_tab = sample.count('\t')
    if n_semi > 0 and n_semi >= n_comma // 2:
        return ';', ','
    if n_tab > 0:
        return '\t', '.'
    return ',', '.'


def load_bdrv_csv(file_bytes: bytes, equnr: str = '', filename: str = '') -> pd.DataFrame:
    """Парсит один CSV-файл «Панели тренда» в long-format DataFrame.

    Аргументы:
      file_bytes: содержимое CSV
      equnr: код единицы оборудования (если пустой — пробуем взять из имени файла)
      filename: имя файла (для извлечения equnr и для логов)

    Возвращает: DataFrame с колонками
      equnr, tag, plant_unit, pos, data_type, value_type, timestamp, value
    """
    if not equnr and filename:
        # имя без расширения = equnr
        equnr = Path(filename).stem

    # Декодируем
    try:
        text = file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        text = file_bytes.decode('cp1251', errors='replace')

    # Пропускаем BOM
    text = text.lstrip('\ufeff')

    # Определяем разделители по первым 1024 байтам
    sample = text[:2048]
    sep, dec = detect_separator_and_decimal(sample)

    # Читаем CSV
    df = pd.read_csv(
        io.StringIO(text),
        sep=sep,
        decimal=dec,
        engine='python',  # python-engine надёжнее с разными кавычками/escape
    )

    if df.empty or 'Timestamp' not in df.columns:
        return pd.DataFrame(columns=['equnr', 'tag', 'plant_unit', 'pos', 'data_type', 'value_type', 'timestamp', 'value'])

    # Парсим Timestamp
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df.dropna(subset=['Timestamp'])

    # Long-format: melt по тегам
    tag_cols = [c for c in df.columns if c != 'Timestamp']
    long = df.melt(
        id_vars=['Timestamp'],
        value_vars=tag_cols,
        var_name='tag',
        value_name='value',
    )

    # Числовое значение (float32 — экономия памяти 2× без потери точности для замеров)
    long['value'] = pd.to_numeric(long['value'], errors='coerce').astype('float32')
    long = long.dropna(subset=['value'])

    # Парсим теги (один раз для каждого уникального тега)
    unique_tags = long['tag'].unique()
    tag_meta = {t: parse_tag(t) for t in unique_tags}
    long['plant_unit'] = long['tag'].map(lambda t: tag_meta[t]['plant_unit']).astype('category')
    long['pos'] = long['tag'].map(lambda t: tag_meta[t]['pos']).astype('category')
    long['data_type'] = long['tag'].map(lambda t: tag_meta[t]['data_type']).astype('category')
    long['value_type'] = long['tag'].map(lambda t: tag_meta[t]['value_type']).astype('category')
    # Tag и equnr тоже category (множество повторений)
    long['tag'] = long['tag'].astype('category')

    long['equnr'] = pd.Categorical([equnr] * len(long))
    long = long.rename(columns={'Timestamp': 'timestamp'})

    return long[['equnr', 'tag', 'plant_unit', 'pos', 'data_type', 'value_type', 'timestamp', 'value']]


def load_bdrv_zip(zip_bytes: bytes) -> pd.DataFrame:
    """Парсит ZIP-архив со множеством CSV-файлов БДРВ.

    Имя файла внутри архива = equnr (без расширения).
    Поддерживается вложенная структура: PLANT/equnr.csv (PLANT прибавляется к equnr).
    """
    import zipfile
    out_chunks = []
    bio = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(bio, 'r') as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        for name in names:
            try:
                # equnr из имени файла (отбрасываем папки)
                eq = Path(name).stem
                with zf.open(name) as f:
                    chunk = load_bdrv_csv(f.read(), equnr=eq, filename=name)
                if not chunk.empty:
                    out_chunks.append(chunk)
            except Exception:
                # Пропускаем битые файлы — продолжаем загрузку
                continue
    if not out_chunks:
        return pd.DataFrame(columns=['equnr', 'tag', 'plant_unit', 'pos', 'data_type', 'value_type', 'timestamp', 'value'])
    result = pd.concat(out_chunks, ignore_index=True)
    # После concat category-типы объединяются в object — принудительно восстановим
    for col in ['equnr', 'tag', 'plant_unit', 'pos', 'data_type', 'value_type']:
        if col in result.columns and not isinstance(result[col].dtype, pd.CategoricalDtype):
            result[col] = result[col].astype('category')
    return result


def load_bdrv_files(file_paths: Iterable[Path]) -> pd.DataFrame:
    """Загружает несколько CSV-файлов с диска (для генератора demo и тестов)."""
    chunks = []
    for path in file_paths:
        path = Path(path)
        with open(path, 'rb') as f:
            data = f.read()
        chunk = load_bdrv_csv(data, equnr=path.stem, filename=path.name)
        if not chunk.empty:
            chunks.append(chunk)
    if not chunks:
        return pd.DataFrame(columns=['equnr', 'tag', 'plant_unit', 'pos', 'data_type', 'value_type', 'timestamp', 'value'])
    return pd.concat(chunks, ignore_index=True)


def save_bdrv_parquet(df: pd.DataFrame, parquet_path: Path) -> None:
    """Сохраняет parsed БДРВ в Parquet (zstd-сжатие) для оффлоада из RAM
    и быстрого чтения через DuckDB."""
    parquet_path = Path(parquet_path)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(parquet_path, engine='pyarrow', compression='zstd', index=False)


def load_bdrv_parquet(parquet_path: Path) -> pd.DataFrame:
    """Чтение parsed БДРВ из Parquet."""
    df = pd.read_parquet(parquet_path, engine='pyarrow')
    # Восстанавливаем category для повторяющихся колонок
    for col in ['equnr', 'tag', 'plant_unit', 'pos', 'data_type', 'value_type']:
        if col in df.columns and not isinstance(df[col].dtype, pd.CategoricalDtype):
            df[col] = df[col].astype('category')
    return df


def bdrv_summary(df: pd.DataFrame) -> dict:
    """Сводная статистика загруженной выгрузки."""
    if df.empty:
        return {'eo_count': 0, 'tag_count': 0, 'rows': 0, 'date_min': None, 'date_max': None}
    return {
        'eo_count': int(df['equnr'].nunique()),
        'tag_count': int(df['tag'].nunique()),
        'rows': int(len(df)),
        'date_min': df['timestamp'].min().isoformat() if not df['timestamp'].isna().all() else None,
        'date_max': df['timestamp'].max().isoformat() if not df['timestamp'].isna().all() else None,
    }
