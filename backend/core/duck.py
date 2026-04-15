# -*- coding: utf-8 -*-
"""
core/duck.py — DuckDB-обёртка для быстрой аналитики.

DuckDB работает in-process (без сервера) и в 10-50× быстрее pandas
на OLAP-запросах (GROUP BY, MEDIAN, сортировки по большим наборам).

Использование:
    con = get_or_create_con(session_id)
    con.register('orders', df)       # zero-copy регистрация pandas DataFrame
    res = con.sql("SELECT ЗАВОД, MEDIAN(Plan_N) FROM orders GROUP BY ЗАВОД").df()

ТИТАН-5.
"""

import threading
from typing import Optional

import duckdb
import pandas as pd

# Кэш connection'ов по session_id
_CONS: dict[str, duckdb.DuckDBPyConnection] = {}
_LOCK = threading.Lock()


def get_or_create_con(session_id: str) -> duckdb.DuckDBPyConnection:
    """Возвращает in-memory connection для сессии. Создаёт при первом обращении."""
    with _LOCK:
        if session_id not in _CONS:
            con = duckdb.connect(database=':memory:')
            # Настройки для скорости
            con.sql("SET memory_limit='4GB'")
            con.sql("SET threads=4")
            _CONS[session_id] = con
        return _CONS[session_id]


def register_orders(session_id: str, df: pd.DataFrame) -> None:
    """Регистрирует DataFrame как view `orders` в DuckDB (zero-copy)."""
    con = get_or_create_con(session_id)
    # Удалим если уже есть
    try:
        con.sql("DROP VIEW IF EXISTS orders")
    except Exception:
        pass
    con.register('orders', df)


def register_bdrv(session_id: str, df: pd.DataFrame) -> None:
    """Регистрирует DataFrame с временными рядами как view `bdrv`."""
    con = get_or_create_con(session_id)
    try:
        con.sql("DROP VIEW IF EXISTS bdrv")
    except Exception:
        pass
    con.register('bdrv', df)


def close_session(session_id: str) -> None:
    """Закрывает DuckDB-connection сессии."""
    with _LOCK:
        con = _CONS.pop(session_id, None)
    if con is not None:
        try:
            con.close()
        except Exception:
            pass


def sql(session_id: str, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """Выполняет SQL и возвращает pandas DataFrame."""
    con = get_or_create_con(session_id)
    if params is None:
        return con.sql(query).df()
    return con.execute(query, params).df()


def sql_scalar(session_id: str, query: str, params: Optional[tuple] = None):
    """Выполняет SQL и возвращает первое значение (для COUNT/SUM/единичных значений)."""
    con = get_or_create_con(session_id)
    if params is None:
        return con.sql(query).fetchone()[0]
    return con.execute(query, params).fetchone()[0]


def build_filter_where(filters: dict) -> tuple[str, list]:
    """Превращает dict-фильтр из API в WHERE-условие и список параметров.

    Поддерживает те же поля, что utils/filters.apply_hierarchy_filters:
      hierarchy: {БЕ, ЗАВОД, ПРОИЗВОДСТВО, ЦЕХ, УСТАНОВКА, ЕО}
      search: строка — поиск по ID и Текст
      vid: list of AUART кодов/названий
      abc: list of ABCKZ
      stat: list of STAT
      starred_orders: list (по ID)
      starred_eo: list (по ЕО)

    Возвращает: (where_sql, params_list). where_sql всегда начинается с 'WHERE 1=1'.
    """
    conditions = ['1=1']
    params: list = []

    hierarchy = filters.get('hierarchy', {}) if filters else {}
    for col, values in hierarchy.items():
        if values and len(values) > 0:
            placeholders = ', '.join(['?'] * len(values))
            conditions.append(f'"{col}" IN ({placeholders})')
            params.extend(values)

    search = (filters or {}).get('search', '').strip()
    if search:
        conditions.append('(CAST("ID" AS VARCHAR) ILIKE ? OR "Текст" ILIKE ?)')
        params.extend([f'%{search}%', f'%{search}%'])

    def _in_filter(col: str, key: str):
        vals = (filters or {}).get(key)
        if vals and len(vals) > 0:
            placeholders = ', '.join(['?'] * len(vals))
            conditions.append(f'"{col}" IN ({placeholders})')
            params.extend(vals)

    _in_filter('Вид', 'vid')
    _in_filter('ABC', 'abc')
    _in_filter('STAT', 'stat')

    starred_orders = (filters or {}).get('starred_orders') or []
    starred_eo = (filters or {}).get('starred_eo') or []
    if starred_orders or starred_eo:
        sub_conditions = []
        if starred_orders:
            placeholders = ', '.join(['?'] * len(starred_orders))
            sub_conditions.append(f'"ID" IN ({placeholders})')
            params.extend(starred_orders)
        if starred_eo:
            placeholders = ', '.join(['?'] * len(starred_eo))
            sub_conditions.append(f'"ЕО" IN ({placeholders})')
            params.extend(starred_eo)
        conditions.append('(' + ' OR '.join(sub_conditions) + ')')

    return 'WHERE ' + ' AND '.join(conditions), params


def cleanup_all() -> None:
    """Закрывает все connection'ы (для shutdown приложения)."""
    with _LOCK:
        for con in _CONS.values():
            try:
                con.close()
            except Exception:
                pass
        _CONS.clear()
