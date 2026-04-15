# -*- coding: utf-8 -*-
"""
core/cache.py — Parquet-кэш обработанных DataFrame.

Ключ: SHA-256 от содержимого исходного xlsx/csv.
Значение: processed_df.parquet (результат process_data) + aggregates.pkl.

Профит: повторная загрузка того же файла 4-5 мин → 2-3 сек.

ТИТАН-5.
"""

import hashlib
import os
import pickle
from pathlib import Path
from typing import Optional

import pandas as pd

CACHE_DIR = Path(os.path.dirname(__file__)).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

# Версия схемы кэша — инкрементируется при breaking changes в process_data
CACHE_SCHEMA_VERSION = 'v5.0.0'


def compute_file_hash(file_bytes: bytes) -> str:
    """SHA-256 от содержимого файла."""
    return hashlib.sha256(file_bytes).hexdigest()[:32]


def _df_path(file_hash: str) -> Path:
    return CACHE_DIR / f'{CACHE_SCHEMA_VERSION}_{file_hash}_df.parquet'


def _agg_path(file_hash: str) -> Path:
    return CACHE_DIR / f'{CACHE_SCHEMA_VERSION}_{file_hash}_agg.pkl'


def _meta_path(file_hash: str) -> Path:
    return CACHE_DIR / f'{CACHE_SCHEMA_VERSION}_{file_hash}_meta.pkl'


def has_cache(file_hash: str) -> bool:
    """Проверяет наличие обоих файлов кэша."""
    return _df_path(file_hash).exists() and _agg_path(file_hash).exists()


def load_cache(file_hash: str) -> tuple[pd.DataFrame, dict, dict]:
    """Загружает кэш: (df, aggregates, meta)."""
    df = pd.read_parquet(_df_path(file_hash), engine='pyarrow')
    # Восстанавливаем category-типы (parquet их сохраняет, но при чтении
    # некоторые строковые могут стать object; forced восстановление)
    _restore_categorical(df)

    with open(_agg_path(file_hash), 'rb') as f:
        agg = pickle.load(f)

    meta = {}
    if _meta_path(file_hash).exists():
        with open(_meta_path(file_hash), 'rb') as f:
            meta = pickle.load(f)
        # Восстановим df.attrs из meta
        df_attrs = meta.pop('_df_attrs', None)
        if df_attrs:
            df.attrs.update(df_attrs)

    return df, agg, meta


def save_cache(file_hash: str, df: pd.DataFrame, aggregates: dict, meta: Optional[dict] = None) -> None:
    """Сохраняет DataFrame и агрегаты в Parquet + pickle."""
    # df.attrs может содержать не-JSON-сериализуемые объекты (set/Timestamp).
    # Parquet требует JSON-совместимые attrs. Сохраним их отдельно в meta.
    attrs_backup = dict(df.attrs) if df.attrs else {}
    # Очистим attrs на время записи
    original_attrs = df.attrs
    df.attrs = {}
    try:
        df.to_parquet(_df_path(file_hash), engine='pyarrow', compression='zstd', index=False)
    finally:
        df.attrs = original_attrs

    with open(_agg_path(file_hash), 'wb') as f:
        pickle.dump(aggregates, f, protocol=pickle.HIGHEST_PROTOCOL)

    # attrs сохраняем в pickle (там set/Timestamp работают)
    full_meta = dict(meta) if meta else {}
    full_meta['_df_attrs'] = attrs_backup
    with open(_meta_path(file_hash), 'wb') as f:
        pickle.dump(full_meta, f, protocol=pickle.HIGHEST_PROTOCOL)


def invalidate_cache(file_hash: Optional[str] = None) -> int:
    """Удаляет кэш. Если file_hash=None — очищает всё."""
    removed = 0
    pattern = f'{CACHE_SCHEMA_VERSION}_{file_hash}*' if file_hash else f'{CACHE_SCHEMA_VERSION}_*'
    for p in CACHE_DIR.glob(pattern):
        try:
            p.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def _restore_categorical(df: pd.DataFrame) -> None:
    """При чтении Parquet некоторые строковые колонки возвращаются как object.
    Восстанавливаем category для повторяющихся значений."""
    CATEGORICAL_COLS = [
        'БЕ', 'ЗАВОД', 'ПРОИЗВОДСТВО', 'ЦЕХ', 'УСТАНОВКА',
        'STAT', 'ABC', 'Вид', 'ВИД_РАБОТ', 'INGRP', 'КЛАСС',
        'USER', 'LAST_USER', 'MVZ', 'РМ',
    ]
    for col in CATEGORICAL_COLS:
        if col in df.columns and not isinstance(df[col].dtype, pd.CategoricalDtype):
            df[col] = df[col].astype('category')


def cache_stats() -> dict:
    """Статистика кэша: число файлов, общий размер."""
    files = list(CACHE_DIR.glob(f'{CACHE_SCHEMA_VERSION}_*'))
    total_bytes = sum(p.stat().st_size for p in files)
    return {
        'count': len(files),
        'total_mb': round(total_bytes / 1024 / 1024, 1),
        'dir': str(CACHE_DIR),
    }
