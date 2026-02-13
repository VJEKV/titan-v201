# -*- coding: utf-8 -*-
"""
core/tm_loader.py — Загрузка справочника структуры ТМ
"""

import json
import os

_TM_HIERARCHY = None
_EO_TO_TM = None
_LOADED = False


def _get_json_path():
    """Ищет tm_structure.json в разных местах."""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'tm_structure.json'),
        os.path.join(os.path.dirname(__file__), 'tm_structure.json'),
        'tm_structure.json',
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def _load_structure():
    """Загружает справочники из JSON (один раз)."""
    global _TM_HIERARCHY, _EO_TO_TM, _LOADED

    if _LOADED:
        return

    path = _get_json_path()
    if path:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _TM_HIERARCHY = data.get('tm_hierarchy', {})
            _EO_TO_TM = data.get('eo_to_tm', {})
        except Exception as e:
            print(f"Ошибка загрузки tm_structure.json: {e}")
            _TM_HIERARCHY = {}
            _EO_TO_TM = {}
    else:
        _TM_HIERARCHY = {}
        _EO_TO_TM = {}

    _LOADED = True


def load_tm_structure():
    """Загрузка справочников."""
    _load_structure()
    return _TM_HIERARCHY, _EO_TO_TM


def format_with_name(code, name):
    """Форматирует: 'КОД - Название' или 'Н/Д'."""
    if not code or code in ['', 'Н/Д', 'nan', 'None']:
        return 'Н/Д'
    if name:
        return f"{code} - {name}"
    return code
