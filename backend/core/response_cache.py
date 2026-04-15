# -*- coding: utf-8 -*-
"""
core/response_cache.py — LRU-кэш ответов API.

Кэширует результаты чистых функций-эндпоинтов по (session_id, hash(filters),
hash(thresholds), path_params). Существенно ускоряет работу с одним и тем
же набором фильтров (открыли/закрыли вкладку, переключились назад).

TTL и размер настраиваются. Сброс по session_id происходит при POST /api/upload.

ТИТАН-5.
"""

import hashlib
import json
import time
from functools import wraps
from threading import Lock
from typing import Any, Callable

# Внутреннее хранилище: { key: (value, expires_at) }
_CACHE: dict[str, tuple[Any, float]] = {}
# Индекс по session_id для быстрого invalidate
_SESSION_KEYS: dict[str, set[str]] = {}
_LOCK = Lock()

DEFAULT_TTL = 300          # 5 минут
MAX_ENTRIES = 512          # LRU-ограничение (простая FIFO-очистка при превышении)


def _serialize_for_key(obj: Any) -> str:
    """Детерминированная сериализация любых JSON-подобных объектов."""
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return repr(obj)


def _make_key(endpoint: str, args: tuple, kwargs: dict) -> str:
    """Строит ключ кэша из endpoint и параметров (session_id включён в kwargs)."""
    parts = [endpoint]
    for a in args:
        parts.append(_serialize_for_key(a))
    for k in sorted(kwargs.keys()):
        parts.append(f'{k}={_serialize_for_key(kwargs[k])}')
    raw = '|'.join(parts)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]


def cached_endpoint(ttl: int = DEFAULT_TTL):
    """Декоратор кэширования async-эндпоинтов.

    Требование: первый позиционный аргумент или именованный `session_id`
    должен однозначно идентифицировать сессию, иначе инвалидация по upload
    не сработает и ответы между сессиями будут перемешаны.
    """
    def decorator(func: Callable):
        endpoint = f'{func.__module__}.{func.__name__}'

        @wraps(func)
        async def wrapper(*args, **kwargs):
            session_id = kwargs.get('session_id')
            if not isinstance(session_id, str) or not session_id:
                # Не можем определить session_id — вызываем без кэша
                return await func(*args, **kwargs)

            key = _make_key(endpoint, args, kwargs)
            now = time.time()

            with _LOCK:
                entry = _CACHE.get(key)
                if entry is not None:
                    value, expires_at = entry
                    if expires_at > now:
                        return value
                    # Просрочено
                    _CACHE.pop(key, None)
                    _SESSION_KEYS.get(session_id, set()).discard(key)

            # Вызов функции
            result = await func(*args, **kwargs)

            with _LOCK:
                _CACHE[key] = (result, now + ttl)
                _SESSION_KEYS.setdefault(session_id, set()).add(key)
                # Простое ограничение размера — FIFO: удаляем самые старые
                if len(_CACHE) > MAX_ENTRIES:
                    oldest_key = next(iter(_CACHE))
                    _CACHE.pop(oldest_key, None)
                    for keys in _SESSION_KEYS.values():
                        keys.discard(oldest_key)
            return result

        return wrapper
    return decorator


def invalidate_session(session_id: str) -> int:
    """Удаляет все кэшированные ответы по сессии. Вызывается при upload."""
    with _LOCK:
        keys = _SESSION_KEYS.pop(session_id, set())
        for k in keys:
            _CACHE.pop(k, None)
    return len(keys)


def cache_stats() -> dict:
    with _LOCK:
        return {
            'entries': len(_CACHE),
            'sessions': len(_SESSION_KEYS),
            'max_entries': MAX_ENTRIES,
        }


def clear_all() -> int:
    """Полная очистка кэша."""
    with _LOCK:
        n = len(_CACHE)
        _CACHE.clear()
        _SESSION_KEYS.clear()
    return n
